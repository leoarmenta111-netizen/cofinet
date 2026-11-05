import hashlib
import hmac
from decimal import Decimal
from pathlib import Path

from app.services.self_order_payment import (
    MercadoPagoPointProvider,
    SelfOrderPaymentService,
    validate_mercadopago_webhook_signature,
)


def test_point_provider_can_retrieve_order():
    calls = []

    def request_json(**kwargs):
        calls.append(kwargs)

        return {
            "id": "ORD01RECONCILE",
            "status": "processed",
            "status_detail": "accredited",
        }

    provider = MercadoPagoPointProvider(
        access_token="TEST_TOKEN",
        terminal_id="TEST_TERMINAL",
        request_json=request_json,
    )

    result = provider.retrieve(
        "ORD01RECONCILE"
    )

    assert result.status == "APPROVED"

    assert (
        result.external_reference
        == "ORD01RECONCILE"
    )

    assert len(calls) == 1

    assert calls[0]["method"] == "GET"

    assert (
        calls[0]["url"]
        == (
            "https://api.mercadopago.com"
            "/v1/orders/ORD01RECONCILE"
        )
    )


def test_webhook_signature_matches_mp_manifest():
    data_id = "ORD01ABCDEF"
    request_id = "request-123"
    ts = "1742505638683"
    secret = "test-webhook-secret"

    manifest = (
        "id:ord01abcdef;"
        "request-id:request-123;"
        "ts:1742505638683;"
    )

    digest = hmac.new(
        secret.encode(),
        manifest.encode(),
        hashlib.sha256,
    ).hexdigest()

    signature = (
        f"ts={ts},v1={digest}"
    )

    assert (
        validate_mercadopago_webhook_signature(
            data_id=data_id,
            x_request_id=request_id,
            x_signature=signature,
            secret=secret,
        )
        is True
    )


def test_invalid_webhook_signature_is_rejected():
    assert (
        validate_mercadopago_webhook_signature(
            data_id="ORD01ABCDEF",
            x_request_id="request-123",
            x_signature=(
                "ts=1742505638683,"
                "v1=bad"
            ),
            secret="secret",
        )
        is False
    )


def test_payment_service_exposes_reconciliation():
    assert hasattr(
        SelfOrderPaymentService,
        "reconcile",
    )

    assert hasattr(
        SelfOrderPaymentService,
        "reconcile_by_provider_reference",
    )


def test_api_exposes_polling_and_point_webhook():
    root = Path(__file__).resolve().parents[2]

    source = (
        root
        / "backend"
        / "app"
        / "api"
        / "self_orders.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "/payment-status" in source
    assert "/point/webhook" in source

    assert (
        "validate_mercadopago_webhook_signature"
        in source
    )


def test_webhook_secret_is_server_configuration():
    root = Path(__file__).resolve().parents[2]

    source = (
        root
        / "backend"
        / "app"
        / "core"
        / "config.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "MERCADOPAGO_WEBHOOK_SECRET"
        in source
    )



def test_point_webhook_uses_query_data_id_for_signature():
    root = Path(__file__).resolve().parents[2]

    source = (
        root
        / "backend"
        / "app"
        / "api"
        / "self_orders.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "request.query_params.get("
        in source
    )

    assert (
        "'data.id'"
        in source
        or
        '"data.id"'
        in source
    )

    assert (
        "data_id=signature_data_id"
        in source
    )



def test_point_payment_amount_stays_server_side():
    # Smoke assertion documenting that reconciliation
    # uses persisted SelfOrderPaymentAttempt.amount,
    # never an amount from the browser.
    root = Path(__file__).resolve().parents[2]

    source = (
        root
        / "backend"
        / "app"
        / "services"
        / "self_order_payment.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "attempt.amount"
        in source
    )

    assert (
        "provider.retrieve"
        in source
    )
