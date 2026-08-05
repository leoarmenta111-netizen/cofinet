from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.admin import Admin, AdminRole
from app.models.admin_access import InternalHotspotCredential, PinBatch
from app.models.purchase import Purchase
from app.schemas.admin_access import (
    InternalAccessResponse,
    PinBatchDetailResponse,
    PinBatchFailureResponse,
    PinBatchPrintResponse,
    PinBatchPrintableTicket,
    PinBatchSummaryResponse,
    PinBatchTicket,
)


class AdminAccessQueryService:
    """PostgreSQL-only reads for batches and internal credentials.

    This module intentionally has no MikroTik imports. Router availability must
    never affect history, detail, print-data, or internal credential listings.
    """

    @staticmethod
    def list_pin_batches(db: Session, current_admin: Admin) -> list[PinBatchSummaryResponse]:
        query = (
            select(PinBatch)
            .options(joinedload(PinBatch.plan), joinedload(PinBatch.created_by_admin))
            .order_by(PinBatch.created_at.desc(), PinBatch.id.desc())
        )
        if current_admin.role == AdminRole.PIN_OPERATOR:
            query = query.where(PinBatch.created_by_admin_id == current_admin.id)
        batches = db.execute(query).scalars().all()
        return [AdminAccessQueryService.batch_summary(item) for item in batches]

    @staticmethod
    def get_pin_batch(
        db: Session, batch_id: int, current_admin: Admin
    ) -> PinBatchDetailResponse:
        batch = db.execute(
            select(PinBatch)
            .options(
                joinedload(PinBatch.plan),
                joinedload(PinBatch.created_by_admin),
                selectinload(PinBatch.purchases).joinedload(Purchase.plan),
                selectinload(PinBatch.failures),
            )
            .where(PinBatch.id == batch_id)
        ).unique().scalar_one_or_none()
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PIN batch not found")
        AdminAccessQueryService.authorize_batch(batch, current_admin)
        return AdminAccessQueryService.batch_detail(batch)

    @staticmethod
    def get_pin_batch_print_data(
        db: Session, batch_id: int, current_admin: Admin
    ) -> PinBatchPrintResponse:
        detail = AdminAccessQueryService.get_pin_batch(db, batch_id, current_admin)
        return PinBatchPrintResponse(
            batch_uuid=detail.batch_uuid,
            plan_name=detail.plan_name,
            generated_at=detail.created_at,
            tickets=[
                PinBatchPrintableTicket(**ticket.model_dump(exclude={"purchase_id"}))
                for ticket in detail.pins
            ],
        )

    @staticmethod
    def list_internal_access(db: Session) -> list[InternalAccessResponse]:
        credentials = db.execute(
            select(InternalHotspotCredential)
            .options(joinedload(InternalHotspotCredential.created_by_admin))
            .order_by(
                InternalHotspotCredential.created_at.desc(),
                InternalHotspotCredential.id.desc(),
            )
        ).scalars().all()
        return [AdminAccessQueryService.internal_response(item) for item in credentials]

    @staticmethod
    def authorize_batch(batch: PinBatch, current_admin: Admin) -> None:
        if (
            current_admin.role == AdminRole.PIN_OPERATOR
            and batch.created_by_admin_id != current_admin.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    @staticmethod
    def batch_summary(batch: PinBatch) -> PinBatchSummaryResponse:
        creator = batch.created_by_admin
        return PinBatchSummaryResponse(
            id=batch.id,
            batch_uuid=UUID(batch.batch_uuid),
            request_id=UUID(batch.request_uuid),
            plan_id=batch.plan_id,
            plan_name=batch.plan.name,
            requested=batch.requested_quantity,
            created=batch.created_quantity,
            failed=batch.failed_quantity,
            status=batch.status,
            created_by_admin_id=batch.created_by_admin_id,
            created_by_admin_name=creator.full_name if creator is not None else None,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
        )

    @staticmethod
    def batch_detail(batch: PinBatch) -> PinBatchDetailResponse:
        summary = AdminAccessQueryService.batch_summary(batch)
        purchases = sorted(
            batch.purchases,
            key=lambda item: (item.issued_at or item.created_at, item.id),
        )
        return PinBatchDetailResponse(
            **summary.model_dump(),
            pins=[AdminAccessQueryService.batch_ticket(item) for item in purchases],
            failures=[
                PinBatchFailureResponse(
                    pin=item.pin_code,
                    error_code=item.error_code,
                    message=item.error_message,
                )
                for item in batch.failures
            ],
        )

    @staticmethod
    def batch_ticket(purchase: Purchase) -> PinBatchTicket:
        return PinBatchTicket(
            purchase_id=purchase.id,
            pin=purchase.pin_code,
            plan_name=purchase.plan.name,
            duration_minutes=purchase.plan.duration_minutes,
            amount=purchase.amount,
            issued_at=purchase.issued_at,
            expires_at=purchase.expires_at,
        )

    @staticmethod
    def internal_response(credential: InternalHotspotCredential) -> InternalAccessResponse:
        creator = credential.created_by_admin
        return InternalAccessResponse(
            id=credential.id,
            label=credential.label,
            pin=credential.pin_code,
            is_active=credential.is_active,
            created_by_admin_id=credential.created_by_admin_id,
            created_by_admin_name=creator.full_name if creator is not None else None,
            created_at=credential.created_at,
            revoked_at=credential.revoked_at,
            last_used_at=credential.last_used_at,
        )
