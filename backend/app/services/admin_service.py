from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import logging
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.auth.security import hash_password, verify_password
from app.models.admin import Admin, AdminRole
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.purchase import Purchase, PurchaseCreationSource, PurchaseStatus
from app.schemas.admin import (
    AdminCreate,
    AdminDashboardResponse,
    AdminPaymentResponse,
    AdminPinCreate,
    AdminPinResponse,
)
from app.services.mikrotik_service import MikroTikService, MikroTikUserExistsError
from app.services.branch_service import BranchService
from app.services.purchase_service import PurchaseService


logger = logging.getLogger(__name__)


class AdminService:
    _PIN_GENERATION_ATTEMPTS = 10

    @staticmethod
    def login(db: Session, email: str, password: str) -> Admin:
        admin = db.execute(
            select(Admin).where(func.lower(Admin.email) == email.strip().lower())
        ).scalar_one_or_none()
        if admin is None or not verify_password(password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not admin.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive admin")

        admin.last_login_at = datetime.now(UTC)
        try:
            db.commit()
            db.refresh(admin)
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not update administrator login audit",
            ) from exc
        return admin

    @staticmethod
    def create_admin(db: Session, admin_data: AdminCreate, creator: Admin) -> Admin:
        admin = Admin(
            email=str(admin_data.email).strip().lower(),
            password_hash=hash_password(admin_data.password),
            full_name=admin_data.full_name.strip(),
            role=admin_data.role,
            is_active=True,
            created_by_admin_id=creator.id,
        )
        try:
            db.add(admin)
            db.commit()
            db.refresh(admin)
            return admin
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Admin email already registered",
            ) from exc
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create admin",
            ) from exc

    @staticmethod
    def list_admins(db: Session) -> Sequence[Admin]:
        return db.execute(
            select(Admin).options(joinedload(Admin.created_by)).order_by(Admin.created_at, Admin.id)
        ).scalars().all()

    @staticmethod
    def set_admin_status(db: Session, admin_id: int, is_active: bool) -> Admin:
        admins = AdminService._lock_admins(db)
        target = AdminService._find_locked_admin(admins, admin_id)
        if target.is_active and not is_active:
            AdminService._ensure_not_final_super_admin(admins, target)
        target.is_active = is_active
        return AdminService._commit_admin_change(db, target)

    @staticmethod
    def set_admin_role(db: Session, admin_id: int, role: AdminRole) -> Admin:
        admins = AdminService._lock_admins(db)
        target = AdminService._find_locked_admin(admins, admin_id)
        if target.role == AdminRole.SUPER_ADMIN and role != AdminRole.SUPER_ADMIN:
            AdminService._ensure_not_final_super_admin(admins, target)
        target.role = role
        return AdminService._commit_admin_change(db, target)

    @staticmethod
    def reset_admin_password(db: Session, admin_id: int, new_password: str) -> None:
        target = db.execute(
            select(Admin).where(Admin.id == admin_id).with_for_update()
        ).scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
        target.password_hash = hash_password(new_password)
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not reset administrator password",
            ) from exc

    @staticmethod
    def dashboard(
        db: Session,
        branch_code: str | None = None,
    ) -> AdminDashboardResponse:
        now = datetime.now(UTC)
        today_start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        week_start = today_start - timedelta(
            days=today_start.weekday()
        )
        month_start = today_start.replace(day=1)

        branch = (
            BranchService.get_by_code(db, branch_code)
            if branch_code
            else None
        )

        branch_filters = (
            [Purchase.branch_id == branch.id]
            if branch is not None
            else []
        )

        active_purchases = db.execute(
            select(func.count(Purchase.id)).where(
                Purchase.status == PurchaseStatus.PAID,
                Purchase.expires_at > now,
                *branch_filters,
            )
        ).scalar_one()

        expired_purchases = db.execute(
            select(func.count(Purchase.id)).where(
                or_(
                    Purchase.status == PurchaseStatus.EXPIRED,
                    Purchase.expires_at <= now,
                ),
                *branch_filters,
            )
        ).scalar_one()

        active_pins = db.execute(
            select(func.count(Purchase.id)).where(
                Purchase.pin_code.is_not(None),
                Purchase.status == PurchaseStatus.PAID,
                Purchase.expires_at > now,
                *branch_filters,
            )
        ).scalar_one()

        pending_payment_query = (
            select(func.count(Payment.id))
            .join(Payment.purchase)
            .where(
                Payment.provider == "mercadopago",
                Payment.status == "pending",
            )
        )

        if branch is not None:
            pending_payment_query = pending_payment_query.where(
                Purchase.branch_id == branch.id
            )

        pending_payments = db.execute(
            pending_payment_query
        ).scalar_one()

        branch_id = branch.id if branch is not None else None

        return AdminDashboardResponse(
            total_sales_today=AdminService._revenue_since(
                db,
                today_start,
                branch_id=branch_id,
            ),
            total_sales_week=AdminService._revenue_since(
                db,
                week_start,
                branch_id=branch_id,
            ),
            total_sales_month=AdminService._revenue_since(
                db,
                month_start,
                branch_id=branch_id,
            ),
            active_purchases=active_purchases,
            expired_purchases=expired_purchases,
            active_pins=active_pins,
            pending_mercadopago_payments=pending_payments,
        )

    @staticmethod
    def create_cash_pin(
        db: Session,
        pin_request: AdminPinCreate,
        current_admin: Admin,
    ) -> AdminPinResponse:
        plan = db.execute(
            select(Plan).where(Plan.id == pin_request.plan_id, Plan.is_active.is_(True))
        ).scalar_one_or_none()
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        branch = BranchService.resolve(db, pin_request.branch_code)
        issued_at = datetime.now(UTC)

        for _ in range(AdminService._PIN_GENERATION_ATTEMPTS):
            pin_code = AdminService._generate_pin()
            if db.execute(select(Purchase.id).where(Purchase.pin_code == pin_code)).scalar_one_or_none():
                continue

            mikrotik = None
            mikrotik_user_created = False
            purchase = Purchase(
                branch_id=branch.id,
                plan_id=plan.id,
                amount=plan.price,
                status=PurchaseStatus.PAID,
                pin_code=pin_code,
                issued_at=issued_at,
                expires_at=issued_at + timedelta(minutes=plan.duration_minutes),
                creation_source=PurchaseCreationSource.ADMIN_CASH,
                created_by_admin_id=current_admin.id,
            )

            try:
                mikrotik = MikroTikService.for_branch(branch.code)
                mikrotik.create_hotspot_user_strict(
                    username=pin_code,
                    password=pin_code,
                    duration_minutes=plan.duration_minutes,
                    profile="default",
                    comment="CofiNet cash purchase",
                )
                mikrotik_user_created = True
                db.add(purchase)
                db.commit()
                db.refresh(purchase)
                purchase.plan = plan
                purchase.branch = branch
                purchase.created_by_admin = current_admin
                return AdminService._pin_response(purchase, plan)
            except (IntegrityError, MikroTikUserExistsError):
                db.rollback()
                if mikrotik_user_created and mikrotik is not None:
                    try:
                        mikrotik.remove_hotspot_user(pin_code)
                    except Exception:
                        logger.exception("Could not compensate duplicate cash PIN %s", pin_code)
                continue
            except SQLAlchemyError as exc:
                db.rollback()
                if mikrotik_user_created and mikrotik is not None:
                    try:
                        mikrotik.remove_hotspot_user(pin_code)
                    except Exception:
                        logger.exception("Could not compensate cash PIN %s", pin_code)
                logger.exception("Database rejected cash PIN %s", pin_code)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not create cash PIN",
                ) from exc
            except Exception as exc:
                db.rollback()
                if mikrotik_user_created and mikrotik is not None:
                    try:
                        mikrotik.remove_hotspot_user(pin_code)
                    except Exception:
                        logger.exception("Could not compensate cash PIN %s", pin_code)
                logger.exception("MikroTik rejected cash PIN %s", pin_code)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Could not create PIN in MikroTik",
                ) from exc
            finally:
                if mikrotik is not None:
                    mikrotik.disconnect()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate a unique PIN",
        )

    @staticmethod
    def list_cash_pins(db: Session, current_admin: Admin) -> list[AdminPinResponse]:
        query = (
            select(Purchase)
            .options(
                joinedload(Purchase.plan),
                joinedload(Purchase.branch),
                joinedload(Purchase.created_by_admin),
            )
            .where(
                Purchase.creation_source == PurchaseCreationSource.ADMIN_CASH,
                Purchase.status == PurchaseStatus.PAID,
                Purchase.pin_code.is_not(None),
            )
            .order_by(Purchase.issued_at.desc(), Purchase.id.desc())
        )
        if current_admin.role == AdminRole.PIN_OPERATOR:
            query = query.where(Purchase.created_by_admin_id == current_admin.id)
        purchases = db.execute(query).scalars().all()
        return [AdminService._pin_response(purchase, purchase.plan) for purchase in purchases]

    @staticmethod
    def list_payments(
        db: Session,
        branch_code: str | None = None,
    ) -> list[AdminPaymentResponse]:
        branch = (
            BranchService.get_by_code(db, branch_code)
            if branch_code
            else None
        )

        query = (
            select(Payment)
            .options(
                joinedload(Payment.purchase).joinedload(Purchase.plan),
                joinedload(Payment.purchase).joinedload(Purchase.branch),
            )
            .order_by(
                Payment.created_at.desc(),
                Payment.id.desc(),
            )
        )

        if branch is not None:
            query = (
                query
                .join(Payment.purchase)
                .where(Purchase.branch_id == branch.id)
            )

        payments = db.execute(query).scalars().all()

        return [
            AdminService._payment_response(payment)
            for payment in payments
        ]

    @staticmethod
    def get_payment(
        db: Session,
        payment_id: int,
    ) -> AdminPaymentResponse:
        payment = db.execute(
            select(Payment)
            .options(
                joinedload(Payment.purchase).joinedload(Purchase.plan),
                joinedload(Payment.purchase).joinedload(Purchase.branch),
            )
            .where(Payment.id == payment_id)
        ).scalar_one_or_none()

        if payment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        return AdminService._payment_response(payment)

    @staticmethod
    def _revenue_since(
        db: Session,
        start: datetime,
        branch_id: int | None = None,
    ) -> Decimal:
        conditions = [
            Purchase.status == PurchaseStatus.PAID,
            Purchase.issued_at >= start,
        ]

        if branch_id is not None:
            conditions.append(
                Purchase.branch_id == branch_id
            )

        return db.execute(
            select(
                func.coalesce(
                    func.sum(Purchase.amount),
                    Decimal("0"),
                )
            ).where(*conditions)
        ).scalar_one()

    @staticmethod
    def _pin_response(purchase: Purchase, plan: Plan) -> AdminPinResponse:
        creator = purchase.created_by_admin
        branch = purchase.branch

        return AdminPinResponse(
            purchase_id=purchase.id,
            branch_id=purchase.branch_id,
            branch_code=branch.code,
            branch_name=branch.name,
            plan_id=plan.id,
            plan_name=plan.name,
            duration_minutes=PurchaseService.issued_duration_minutes(purchase),
            pin=purchase.pin_code,
            issued_at=purchase.issued_at,
            expires_at=purchase.expires_at,
            amount=purchase.amount,
            creation_source=purchase.creation_source,
            created_by_admin_id=purchase.created_by_admin_id,
            created_by_admin_name=creator.full_name if creator is not None else None,
        )

    @staticmethod
    def _payment_response(payment: Payment) -> AdminPaymentResponse:
        purchase = payment.purchase
        branch = purchase.branch

        return AdminPaymentResponse(
            payment_id=payment.id,
            purchase_id=payment.purchase_id,
            branch_id=purchase.branch_id,
            branch_code=branch.code,
            branch_name=branch.name,
            provider=payment.provider,
            provider_payment_id=payment.provider_payment_id,
            provider_preference_id=payment.provider_preference_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            plan_name=purchase.plan.name,
            purchase_status=purchase.status.value,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )

    @staticmethod
    def _lock_admins(db: Session) -> list[Admin]:
        return list(
            db.execute(select(Admin).order_by(Admin.id).with_for_update()).scalars().all()
        )

    @staticmethod
    def _find_locked_admin(admins: list[Admin], admin_id: int) -> Admin:
        target = next((admin for admin in admins if admin.id == admin_id), None)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
        return target

    @staticmethod
    def _ensure_not_final_super_admin(admins: list[Admin], target: Admin) -> None:
        active_supers = [
            admin
            for admin in admins
            if admin.is_active and admin.role == AdminRole.SUPER_ADMIN
        ]
        if target in active_supers and len(active_supers) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The final active super administrator cannot be disabled or demoted",
            )

    @staticmethod
    def _commit_admin_change(db: Session, admin: Admin) -> Admin:
        try:
            db.commit()
            db.refresh(admin)
            return admin
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not update administrator",
            ) from exc

    @staticmethod
    def _generate_pin() -> str:
        return f"{secrets.randbelow(900000) + 100000:06d}"
