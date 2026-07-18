from dataclasses import dataclass
from decimal import Decimal
import logging
from typing import Any
from urllib.parse import urlparse

import mercadopago
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.payment import Payment
from app.models.purchase import Purchase, PurchaseStatus
from app.services.purchase_service import PurchaseService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckoutSession:
    checkout_url: str
    payment_status: str


class PaymentService:
    _PROVIDER = "mercadopago"
    _CURRENCY = "MXN"

    @staticmethod
    def create_mercadopago_checkout(db: Session, purchase: Purchase) -> CheckoutSession:
        """Create a Checkout Pro preference and persist its pending payment record."""
        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Mercado Pago is not configured",
            )

        preference = PaymentService._create_preference(purchase)
        preference_id = preference.get("id")
        checkout_url = preference.get("init_point")
        if not isinstance(preference_id, str) or not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Mercado Pago returned an invalid preference",
            )

        payment = Payment(
            purchase_id=purchase.id,
            provider=PaymentService._PROVIDER,
            provider_preference_id=preference_id,
            amount=purchase.amount,
            currency=PaymentService._CURRENCY,
            status="pending",
        )
        try:
            db.add(payment)
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create payment record",
            ) from exc

        return CheckoutSession(checkout_url=checkout_url, payment_status=payment.status)

    @staticmethod
    def _create_preference(purchase: Purchase) -> dict[str, Any]:
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

        preference_data: dict[str, Any] = {
            "items": [
                {
                    "id": str(purchase.plan_id),
                    "title": purchase.plan.name,
                    "description": purchase.plan.description or purchase.plan.name,
                    "quantity": 1,
                    "currency_id": PaymentService._CURRENCY,
                    "unit_price": float(Decimal(purchase.amount)),
                }
            ],
            "external_reference": str(purchase.id),
            "notification_url": f"{settings.FRONTEND_URL.rstrip('/')}/api/payments/webhook",
        }
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        frontend_host = urlparse(frontend_url).hostname
        if frontend_host not in {"localhost", "127.0.0.1", "::1"}:
            preference_data["back_urls"] = {
                "success": f"{frontend_url}/?purchase_id={purchase.id}",
                "pending": f"{frontend_url}/?purchase_id={purchase.id}",
                "failure": f"{frontend_url}/?purchase_id={purchase.id}",
            }
            preference_data["auto_return"] = "approved"
        logger.info("Mercado Pago preference payload: %r", preference_data)
        try:
            result = sdk.preference().create(preference_data)
        except Exception as exc:
            logger.exception("Mercado Pago preference creation failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not create Mercado Pago preference",
            ) from exc

        logger.info("Mercado Pago preference SDK response: %r", result)
        print("Mercado Pago preference SDK response:", result)
        response = (
            result.get("response", result.get("body"))
            if isinstance(result, dict)
            else None
        )
        if not isinstance(response, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Mercado Pago returned an invalid preference",
            )
        
        return response

    @staticmethod
    def _checkout_url(preference: dict[str, Any]) -> str | None:
        checkout_url = preference.get("init_point")
        return checkout_url if isinstance(checkout_url, str) and checkout_url else None

    @staticmethod
    def process_mercadopago_webhook(db: Session, notification: dict[str, Any]) -> None:
        logger.info("========== WEBHOOK RECIBIDO ==========")
        logger.info("Payload: %s", notification)

        notification_payment_id = PaymentService._notification_payment_id(notification)

        logger.info("Notification payment id: %s", notification_payment_id)

        if notification_payment_id is None:
            logger.warning("Webhook recibido sin payment_id.")
            return

        verified_payment = PaymentService._get_mercadopago_payment(notification_payment_id)

        logger.info("Mercado Pago payment:")
        logger.info("%s", verified_payment)

        payment_status = verified_payment.get("status")
        provider_payment_id = str(verified_payment.get("id", notification_payment_id))
        external_reference = verified_payment.get("external_reference")

        logger.info("Status.............: %s", payment_status)
        logger.info("Provider payment...: %s", provider_payment_id)
        logger.info("External Reference.: %s", external_reference)

        if payment_status != "approved":
            logger.warning("Pago todavía NO aprobado.")
            return

        if not external_reference or not external_reference.isdigit():
            logger.error("El pago no tiene un external_reference válido (purchase_id).")
            return

        purchase_id = int(external_reference)

        try:
            payment = db.execute(
                select(Payment)
                .where(
                    Payment.provider == PaymentService._PROVIDER,
                    Payment.purchase_id == purchase_id,
                )
                .with_for_update()
            ).scalar_one_or_none()

            logger.info("Payment encontrado: %s", payment)

            if payment is None:
                logger.error("NO SE ENCONTRÓ EL PAYMENT LOCAL")
                db.rollback()
                return

            purchase = db.execute(
                select(Purchase)
                .where(Purchase.id == payment.purchase_id)
                .with_for_update()
            ).scalar_one()

            logger.info("Purchase encontrada: %s", purchase.id)
            logger.info("Estado actual: %s", purchase.status)

            if purchase.status == PurchaseStatus.PAID:
                logger.info("La compra ya estaba pagada.")
                db.rollback()
                return

            payment.provider_payment_id = provider_payment_id
            payment.status = "approved"

            logger.info("Generando PIN...")

            PurchaseService.mark_guest_purchase_paid(db, purchase)
            
            db.commit()
            logger.info("PIN generado correctamente y transacción completada.")

        except Exception as e:
            db.rollback()
            logger.exception("Error procesando el webhook: %s", e)
            raise

    @staticmethod
    def _notification_payment_id(notification: dict[str, Any]) -> str | None:
        data = notification.get("data")
        if isinstance(data, dict) and data.get("id") is not None:
            return str(data["id"])
        if notification.get("id") is not None:
            return str(notification["id"])
        return None

    @staticmethod
    def _get_mercadopago_payment(payment_id: str) -> dict[str, Any]:
        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Mercado Pago is not configured",
            )
        try:
            result = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN).payment().get(payment_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not verify Mercado Pago payment",
            ) from exc
        response = result.get("response") if isinstance(result, dict) else None
        if not isinstance(response, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Mercado Pago returned an invalid payment",
            )
        return response
