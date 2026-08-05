from datetime import UTC, datetime, timedelta
import logging
import os
import secrets
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.admin import Admin
from app.models.admin_access import (
    InternalHotspotCredential,
    PinBatch,
    PinBatchFailure,
    PinBatchStatus,
)
from app.models.plan import Plan
from app.models.purchase import Purchase, PurchaseCreationSource, PurchaseStatus
from app.schemas.admin_access import (
    InternalAccessCreate,
    InternalAccessResponse,
    PinBatchCreate,
    PinBatchDetailResponse,
)
from app.services.admin_access_query_service import AdminAccessQueryService
from app.services.mikrotik_service import MikroTikService, MikroTikUserExistsError


logger = logging.getLogger(__name__)


class AdminAccessService:
    _PIN_GENERATION_ATTEMPTS = 25
    _INTERNAL_PROFILE = os.getenv("MIKROTIK_INTERNAL_PROFILE", "internal-devices")

    @staticmethod
    def create_pin_batch(
        db: Session, request: PinBatchCreate, current_admin: Admin
    ) -> PinBatchDetailResponse:
        request_uuid = str(request.request_id)
        existing = AdminAccessService._batch_by_request(db, request_uuid)
        if existing is not None:
            AdminAccessService._validate_batch_replay(existing, request, current_admin)
            if existing.status == PinBatchStatus.PROCESSING:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This batch request is already processing",
                )
            return AdminAccessQueryService.batch_detail(existing)

        plan = db.execute(
            select(Plan).where(Plan.id == request.plan_id, Plan.is_active.is_(True))
        ).scalar_one_or_none()
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        batch = PinBatch(
            batch_uuid=str(uuid4()),
            request_uuid=request_uuid,
            plan_id=plan.id,
            requested_quantity=request.quantity,
            created_quantity=0,
            failed_quantity=0,
            status=PinBatchStatus.PROCESSING,
            created_by_admin_id=current_admin.id,
        )
        try:
            db.add(batch)
            db.commit()
            db.refresh(batch)
        except IntegrityError as exc:
            db.rollback()
            existing = AdminAccessService._batch_by_request(db, request_uuid)
            if existing is not None:
                AdminAccessService._validate_batch_replay(existing, request, current_admin)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This batch request is already processing",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Batch request conflicts with existing data",
            ) from exc
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not initialize PIN batch",
            ) from exc

        mikrotik = None
        try:
            mikrotik = MikroTikService()
        except Exception:
            for _ in range(request.quantity):
                AdminAccessService._record_batch_failure(
                    db,
                    batch.id,
                    None,
                    "mikrotik_unavailable",
                    "MikroTik connection could not be established",
                )
            AdminAccessService._finalize_batch(db, batch.id)
            return AdminAccessQueryService.get_pin_batch(db, batch.id, current_admin)

        try:
            for _ in range(request.quantity):
                AdminAccessService._create_batch_pin(
                    db=db,
                    batch_id=batch.id,
                    plan=plan,
                    current_admin=current_admin,
                    mikrotik=mikrotik,
                )
        finally:
            AdminAccessService._disconnect_quietly(mikrotik)

        AdminAccessService._finalize_batch(db, batch.id)
        return AdminAccessQueryService.get_pin_batch(db, batch.id, current_admin)

    @staticmethod
    def create_internal_access(
        db: Session, request: InternalAccessCreate, current_admin: Admin
    ) -> InternalAccessResponse:
        request_uuid = str(request.request_id)
        existing = db.execute(
            select(InternalHotspotCredential)
            .options(joinedload(InternalHotspotCredential.created_by_admin))
            .where(InternalHotspotCredential.request_uuid == request_uuid)
        ).scalar_one_or_none()
        if existing is not None:
            if existing.label != request.label or existing.created_by_admin_id != current_admin.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Internal access request identifier conflicts with existing data",
                )
            return AdminAccessQueryService.internal_response(existing)

        label_exists = db.execute(
            select(InternalHotspotCredential.id).where(
                InternalHotspotCredential.label == request.label
            )
        ).scalar_one_or_none()
        if label_exists is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An internal credential already uses this device label",
            )

        mikrotik = None
        try:
            mikrotik = MikroTikService()
            for _ in range(AdminAccessService._PIN_GENERATION_ATTEMPTS):
                pin_code = AdminAccessService._generate_pin()
                if AdminAccessService._pin_exists(db, pin_code):
                    continue
                try:
                    mikrotik.create_permanent_hotspot_user_strict(
                        username=pin_code,
                        password=pin_code,
                        profile=AdminAccessService._INTERNAL_PROFILE,
                        comment=f"CofiNet internal device: {request.label}",
                    )
                except MikroTikUserExistsError:
                    continue
                except Exception as exc:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Could not create permanent credential in MikroTik",
                    ) from exc

                credential = InternalHotspotCredential(
                    request_uuid=request_uuid,
                    label=request.label,
                    pin_code=pin_code,
                    creation_source="internal_device",
                    is_active=True,
                    created_by_admin_id=current_admin.id,
                )
                try:
                    db.add(credential)
                    db.commit()
                    db.refresh(credential)
                    credential.created_by_admin = current_admin
                    return AdminAccessQueryService.internal_response(credential)
                except IntegrityError as exc:
                    db.rollback()
                    AdminAccessService._remove_user_quietly(mikrotik, pin_code)
                    if db.execute(
                        select(InternalHotspotCredential.id).where(
                            InternalHotspotCredential.label == request.label
                        )
                    ).scalar_one_or_none():
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="An internal credential already uses this device label",
                        ) from exc
                    continue
                except SQLAlchemyError as exc:
                    db.rollback()
                    AdminAccessService._remove_user_quietly(mikrotik, pin_code)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Could not store permanent credential",
                    ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not connect to MikroTik",
            ) from exc
        finally:
            if mikrotik is not None:
                AdminAccessService._disconnect_quietly(mikrotik)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not generate a unique permanent credential",
        )

    @staticmethod
    def set_internal_access_status(
        db: Session, credential_id: int, is_active: bool
    ) -> InternalAccessResponse:
        credential = db.execute(
            select(InternalHotspotCredential)
            .options(joinedload(InternalHotspotCredential.created_by_admin))
            .where(InternalHotspotCredential.id == credential_id)
            .with_for_update()
        ).scalar_one_or_none()
        if credential is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internal credential not found",
            )
        if credential.is_active == is_active:
            return AdminAccessQueryService.internal_response(credential)

        mikrotik = None
        try:
            mikrotik = MikroTikService()
            if is_active:
                try:
                    mikrotik.create_permanent_hotspot_user_strict(
                        username=credential.pin_code,
                        password=credential.pin_code,
                        profile=AdminAccessService._INTERNAL_PROFILE,
                        comment=f"CofiNet internal device: {credential.label}",
                    )
                except MikroTikUserExistsError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="The MikroTik username already exists; activation is unsafe",
                    ) from exc
            else:
                mikrotik.remove_hotspot_user(credential.pin_code)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not update permanent credential in MikroTik",
            ) from exc

        credential.is_active = is_active
        credential.revoked_at = None if is_active else datetime.now(UTC)
        try:
            db.commit()
            db.refresh(credential)
            return AdminAccessQueryService.internal_response(credential)
        except SQLAlchemyError as exc:
            db.rollback()
            try:
                if is_active:
                    mikrotik.remove_hotspot_user(credential.pin_code)
                else:
                    mikrotik.create_permanent_hotspot_user_strict(
                        username=credential.pin_code,
                        password=credential.pin_code,
                        profile=AdminAccessService._INTERNAL_PROFILE,
                        comment=f"CofiNet internal device: {credential.label}",
                    )
            except Exception:
                logger.exception("Failed to compensate MikroTik after database status failure")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not store permanent credential status",
            ) from exc
        finally:
            if mikrotik is not None:
                AdminAccessService._disconnect_quietly(mikrotik)

    @staticmethod
    def _create_batch_pin(
        db: Session,
        batch_id: int,
        plan: Plan,
        current_admin: Admin,
        mikrotik: MikroTikService,
    ) -> None:
        last_pin = None
        for _ in range(AdminAccessService._PIN_GENERATION_ATTEMPTS):
            pin_code = AdminAccessService._generate_pin()
            last_pin = pin_code
            if AdminAccessService._pin_exists(db, pin_code):
                continue
            if db.execute(
                select(PinBatchFailure.id).where(
                    PinBatchFailure.pin_batch_id == batch_id,
                    PinBatchFailure.pin_code == pin_code,
                )
            ).scalar_one_or_none() is not None:
                continue
            try:
                mikrotik.create_hotspot_user_strict(
                    username=pin_code,
                    password=pin_code,
                    duration_minutes=plan.duration_minutes,
                    profile="default",
                    comment=f"CofiNet admin batch {batch_id}",
                )
            except MikroTikUserExistsError:
                continue
            except Exception:
                AdminAccessService._record_batch_failure(
                    db,
                    batch_id,
                    pin_code,
                    "mikrotik_create_failed",
                    "MikroTik did not confirm the Hotspot user",
                )
                return

            batch = db.get(PinBatch, batch_id)
            issued_at = datetime.now(UTC)
            purchase = Purchase(
                plan_id=plan.id,
                amount=plan.price,
                status=PurchaseStatus.PAID,
                pin_code=pin_code,
                issued_at=issued_at,
                expires_at=issued_at + timedelta(minutes=plan.duration_minutes),
                creation_source=PurchaseCreationSource.ADMIN_BATCH,
                created_by_admin_id=current_admin.id,
                pin_batch_id=batch_id,
            )
            try:
                batch.created_quantity += 1
                db.add(purchase)
                db.commit()
                return
            except IntegrityError:
                db.rollback()
                AdminAccessService._remove_user_quietly(mikrotik, pin_code)
                continue
            except SQLAlchemyError:
                db.rollback()
                AdminAccessService._remove_user_quietly(mikrotik, pin_code)
                AdminAccessService._record_batch_failure(
                    db,
                    batch_id,
                    pin_code,
                    "database_write_failed",
                    "Database did not confirm the generated PIN",
                )
                return

        AdminAccessService._record_batch_failure(
            db,
            batch_id,
            last_pin,
            "unique_pin_exhausted",
            "Could not find a PIN unique in PostgreSQL and MikroTik",
        )

    @staticmethod
    def _record_batch_failure(
        db: Session,
        batch_id: int,
        pin_code: str | None,
        error_code: str,
        message: str,
    ) -> None:
        batch = db.get(PinBatch, batch_id)
        batch.failed_quantity += 1
        db.add(
            PinBatchFailure(
                pin_batch_id=batch_id,
                pin_code=pin_code,
                error_code=error_code,
                error_message=message,
            )
        )
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not record PIN batch failure",
            ) from exc

    @staticmethod
    def _finalize_batch(db: Session, batch_id: int) -> None:
        batch = db.get(PinBatch, batch_id)
        if batch.created_quantity == batch.requested_quantity:
            batch.status = PinBatchStatus.COMPLETED
        elif batch.created_quantity == 0:
            batch.status = PinBatchStatus.FAILED
        else:
            batch.status = PinBatchStatus.PARTIAL
        batch.completed_at = datetime.now(UTC)
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not finalize PIN batch",
            ) from exc

    @staticmethod
    def _batch_by_request(db: Session, request_uuid: str) -> PinBatch | None:
        return db.execute(
            select(PinBatch)
            .options(
                joinedload(PinBatch.plan),
                joinedload(PinBatch.created_by_admin),
                selectinload(PinBatch.purchases).joinedload(Purchase.plan),
                selectinload(PinBatch.failures),
            )
            .where(PinBatch.request_uuid == request_uuid)
        ).unique().scalar_one_or_none()

    @staticmethod
    def _validate_batch_replay(
        batch: PinBatch, request: PinBatchCreate, current_admin: Admin
    ) -> None:
        if (
            batch.plan_id != request.plan_id
            or batch.requested_quantity != request.quantity
            or batch.created_by_admin_id != current_admin.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Batch request identifier conflicts with existing data",
            )

    @staticmethod
    def _pin_exists(db: Session, pin_code: str) -> bool:
        purchase = db.execute(
            select(Purchase.id).where(Purchase.pin_code == pin_code)
        ).scalar_one_or_none()
        if purchase is not None:
            return True
        internal = db.execute(
            select(InternalHotspotCredential.id).where(
                InternalHotspotCredential.pin_code == pin_code
            )
        ).scalar_one_or_none()
        return internal is not None

    @staticmethod
    def _remove_user_quietly(mikrotik: MikroTikService, pin_code: str) -> None:
        try:
            mikrotik.remove_hotspot_user(pin_code)
        except Exception:
            logger.exception("Could not compensate MikroTik Hotspot user creation")

    @staticmethod
    def _disconnect_quietly(mikrotik: MikroTikService) -> None:
        try:
            mikrotik.disconnect()
        except Exception:
            logger.exception("Could not close MikroTik connection")

    @staticmethod
    def _generate_pin() -> str:
        return f"{secrets.randbelow(900000) + 100000:06d}"
