from datetime import UTC, datetime, timedelta
from decimal import Decimal
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.auth.security import hash_password, verify_password
from app.models.admin import Admin
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.purchase import Purchase, PurchaseStatus
from app.schemas.admin import AdminDashboardResponse, AdminPinCreate, AdminPinResponse


class AdminService:
    _PIN_GENERATION_ATTEMPTS = 10

    @staticmethod
    def login(db: Session, email: str, password: str) -> Admin:
        admin = db.execute(select(Admin).where(Admin.email == email)).scalar_one_or_none()
        if admin is None or not verify_password(password, admin.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not admin.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive admin")
        return admin

    @staticmethod
    def create_admin(db: Session, email: str, password: str, full_name: str) -> Admin:
        """Internal provisioning helper; intentionally not exposed as a public route."""
        admin = Admin(email=email, password_hash=hash_password(password), full_name=full_name)
        try:
            db.add(admin)
            db.commit()
            db.refresh(admin)
            return admin
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin email already registered") from exc
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create admin") from exc

    @staticmethod
    def dashboard(db: Session) -> AdminDashboardResponse:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        total_sales = db.execute(
            select(func.coalesce(func.sum(Purchase.amount), Decimal("0"))).where(
                Purchase.status == PurchaseStatus.PAID,
                Purchase.issued_at >= today_start,
            )
        ).scalar_one()
        active_purchases = db.execute(
            select(func.count(Purchase.id)).where(
                Purchase.status == PurchaseStatus.PAID,
                Purchase.expires_at > now,
            )
        ).scalar_one()
        expired_purchases = db.execute(
            select(func.count(Purchase.id)).where(
                or_(Purchase.status == PurchaseStatus.EXPIRED, Purchase.expires_at <= now),
            )
        ).scalar_one()
        active_pins = db.execute(
            select(func.count(Purchase.id)).where(
                Purchase.pin_code.is_not(None),
                Purchase.status == PurchaseStatus.PAID,
                Purchase.expires_at > now,
            )
        ).scalar_one()
        pending_payments = db.execute(
            select(func.count(Payment.id)).where(
                Payment.provider == "mercadopago", Payment.status == "pending"
            )
        ).scalar_one()
        return AdminDashboardResponse(
            total_sales_today=total_sales,
            active_purchases=active_purchases,
            expired_purchases=expired_purchases,
            active_pins=active_pins,
            pending_mercadopago_payments=pending_payments,
        )

    @staticmethod
    def create_cash_pin(db: Session, pin_request: AdminPinCreate) -> AdminPinResponse:
        plan = db.execute(
            select(Plan).where(Plan.id == pin_request.plan_id, Plan.is_active.is_(True))
        ).scalar_one_or_none()
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        issued_at = datetime.now(UTC)
        for _ in range(AdminService._PIN_GENERATION_ATTEMPTS):
            pin_code = AdminService._generate_pin()
            if db.execute(select(Purchase.id).where(Purchase.pin_code == pin_code)).scalar_one_or_none():
                continue
            purchase = Purchase(
                plan_id=plan.id,
                amount=plan.price,
                status=PurchaseStatus.PAID,
                pin_code=pin_code,
                issued_at=issued_at,
                expires_at=issued_at + timedelta(minutes=plan.duration_minutes),
            )
            try:
                db.add(purchase)
                db.commit()
                db.refresh(purchase)
                return AdminService._pin_response(purchase, plan)
            except IntegrityError:
                db.rollback()
            except SQLAlchemyError as exc:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create cash PIN") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate a unique PIN")

    @staticmethod
    def list_cash_pins(db: Session) -> list[AdminPinResponse]:
        purchases = db.execute(
            select(Purchase)
            .outerjoin(Payment, Payment.purchase_id == Purchase.id)
            .options(joinedload(Purchase.plan))
            .where(
                Purchase.user_id.is_(None),
                Payment.id.is_(None),
                Purchase.status == PurchaseStatus.PAID,
                Purchase.pin_code.is_not(None),
            )
            .order_by(Purchase.issued_at.desc(), Purchase.id.desc())
        ).scalars().all()
        return [AdminService._pin_response(purchase, purchase.plan) for purchase in purchases]

    @staticmethod
    def _pin_response(purchase: Purchase, plan: Plan) -> AdminPinResponse:
        return AdminPinResponse(
            purchase_id=purchase.id,
            plan_id=plan.id,
            plan_name=plan.name,
            pin=purchase.pin_code,
            issued_at=purchase.issued_at,
            expires_at=purchase.expires_at,
            amount=purchase.amount,
        )

    @staticmethod
    def _generate_pin() -> str:
        return f"{secrets.randbelow(900000) + 100000:06d}"
