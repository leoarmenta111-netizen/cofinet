from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import logging
from typing import Any

import mercadopago
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.core.config import settings
from app.models.membership import Membership, MembershipStatus
from app.models.user import User
from app.schemas.membership import MembershipCheckoutRequest


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MembershipPlanDefinition:
    name: str
    amount: Decimal


class MembershipService:
    PLANS = {
        "individual": MembershipPlanDefinition("Individual", Decimal("599.00")),
        "freelancer": MembershipPlanDefinition("Freelancer", Decimal("999.00")),
        "empresarial": MembershipPlanDefinition("Empresarial", Decimal("2490.00")),
    }

    @classmethod
    def create_checkout(cls, db: Session, request: MembershipCheckoutRequest) -> tuple[Membership, str]:
        plan = cls.PLANS.get(request.plan.lower())
        if plan is None:
            raise HTTPException(status_code=404, detail="Membership plan not found")
        if db.execute(select(User.id).where(User.email == request.email)).scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = User(name=request.full_name, email=request.email, password_hash=hash_password(request.password), membership_type=request.plan.lower(), is_active=False)
        membership = Membership(user=user, plan_code=request.plan.lower(), plan_name=plan.name, monthly_amount=plan.amount, status=MembershipStatus.PENDING)
        try:
            db.add_all([user, membership])
            db.commit()
            db.refresh(membership)
        except IntegrityError as exc:
            db.rollback()
            logger.exception("Membership checkout failed: email already registered during persistence")
            raise HTTPException(status_code=409, detail="Email already registered") from exc
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Membership checkout database persistence failed")
            raise HTTPException(status_code=500, detail="Could not create membership") from exc

        try:
            checkout_url, preapproval_id = cls._create_preapproval(membership, request.email)
            membership.provider_preapproval_id = preapproval_id
            db.commit()
            return membership, checkout_url
        except Exception:
            logger.exception("Membership checkout subscription creation failed")
            db.delete(membership)
            db.delete(user)
            db.commit()
            raise

    @staticmethod
    def _create_preapproval(membership: Membership, email: str) -> tuple[str, str]:
        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            raise HTTPException(status_code=500, detail="Membership payments are not configured")
        payload: dict[str, Any] = {
            "reason": f"CofiNet {membership.plan_name} mensual",
            "external_reference": str(membership.id),
            "payer_email": email,
            "auto_recurring": {"frequency": 1, "frequency_type": "months", "transaction_amount": float(membership.monthly_amount), "currency_id": "MXN"},
            "back_url": f"{settings.FRONTEND_URL.rstrip('/')}/index.html?membership=success",
        }
        payload["notification_url"] = (
    settings.MEMBERSHIP_WEBHOOK_URL
    or f"{settings.FRONTEND_URL.rstrip('/')}/api/memberships/webhook"
)
        token_prefix = (settings.MERCADOPAGO_ACCESS_TOKEN or "")[:10]
       
        logger.info("Mercado Pago membership preapproval payload: %r", payload)
        try:
            result = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN).preapproval().create(payload)
            logger.info("Mercado Pago membership preapproval SDK response: %r", result)
            response = result.get("response", result.get("body")) if isinstance(result, dict) else None
        except Exception as exc:
            logger.exception("Mercado Pago membership preapproval creation failed")
            detail = "Could not create membership subscription"
            if settings.DEBUG:
                detail = f"{detail}: {exc}"
            raise HTTPException(status_code=502, detail=detail) from exc
        if not isinstance(response, dict) or not isinstance(response.get("id"), str) or not isinstance(response.get("init_point"), str):
            raise HTTPException(status_code=502, detail="Mercado Pago returned an invalid subscription")
        return response["init_point"], response["id"]

    @staticmethod
    def process_webhook(db: Session, preapproval_id: str) -> None:
        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            raise HTTPException(status_code=500, detail="Membership payments are not configured")
        try:
            result = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN).preapproval().get(preapproval_id)
            response = result.get("response", result.get("body")) if isinstance(result, dict) else None
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Could not verify membership subscription") from exc
        if not isinstance(response, dict):
            raise HTTPException(status_code=502, detail="Mercado Pago returned an invalid subscription")
        membership = db.execute(select(Membership).where(Membership.provider_preapproval_id == preapproval_id)).scalar_one_or_none()
        if membership is None:
            return
        user = db.get(User, membership.user_id)
        if response.get("status") == "authorized":
            membership.status = MembershipStatus.ACTIVE
            membership.activated_at = datetime.now(UTC)
            user.is_active = True
        elif response.get("status") in {"cancelled", "paused"}:
            membership.status = MembershipStatus.CANCELLED
            user.is_active = False
        db.commit()
