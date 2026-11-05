from decimal import Decimal

from app.services.self_order_payment import (
    MercadoPagoPointProvider,
)


TERMINAL_ID = (
    "NEWLAND_N950__N950NCD500197607"
)


def test_point_provider_creates_automatic_order():
    calls = []

    def request_json(**kwargs):
        calls.append(kwargs)

        return {
            "id": "ORD01TEST123",
            "status": "created",
            "status_detail": "created",
        }

    provider = MercadoPagoPointProvider(
        access_token="TEST_TOKEN",
        terminal_id=TERMINAL_ID,
        request_json=request_json,
    )

    result = provider.charge(
        payment_attempt_uuid=(
            "11111111-1111-4111-8111-111111111111"
        ),
        amount=Decimal("114.00"),
    )

    assert result.status == "PROCESSING"

    assert (
        result.external_reference
        == "ORD01TEST123"
    )

    assert len(calls) == 1

    call = calls[0]

    assert call["method"] == "POST"

    assert (
        call["url"]
        == "https://api.mercadopago.com/v1/orders"
    )

    assert (
        call["headers"]["X-Idempotency-Key"]
        == "11111111-1111-4111-8111-111111111111"
    )

    payload = call["payload"]

    assert payload["type"] == "point"

    assert (
        payload["transactions"]
        ["payments"][0]["amount"]
        == "114.00"
    )

    assert (
        payload["config"]["point"]
        ["terminal_id"]
        == TERMINAL_ID
    )

    assert "processing_mode" not in payload


def test_point_provider_maps_processed_to_approved():
    def request_json(**kwargs):
        return {
            "id": "ORD01PAID123",
            "status": "processed",
            "status_detail": "accredited",
        }

    provider = MercadoPagoPointProvider(
        access_token="TEST_TOKEN",
        terminal_id=TERMINAL_ID,
        request_json=request_json,
    )

    result = provider.charge(
        payment_attempt_uuid=(
            "22222222-2222-4222-8222-222222222222"
        ),
        amount=Decimal("25.00"),
    )

    assert result.status == "APPROVED"

    assert (
        result.external_reference
        == "ORD01PAID123"
    )


def test_point_provider_maps_terminal_failure_to_declined():
    for status in (
        "failed",
        "expired",
        "canceled",
    ):
        def request_json(
            *,
            _status=status,
            **kwargs,
        ):
            return {
                "id": "ORD01FAILED123",
                "status": _status,
                "status_detail": _status,
            }

        provider = MercadoPagoPointProvider(
            access_token="TEST_TOKEN",
            terminal_id=TERMINAL_ID,
            request_json=request_json,
        )

        result = provider.charge(
            payment_attempt_uuid=(
                "33333333-3333-4333-8333-333333333333"
            ),
            amount=Decimal("25.00"),
        )

        assert result.status == "DECLINED"


def test_point_provider_blocks_amount_below_five_without_http():
    calls = []

    def request_json(**kwargs):
        calls.append(kwargs)

        raise AssertionError(
            "HTTP should not be called"
        )

    provider = MercadoPagoPointProvider(
        access_token="TEST_TOKEN",
        terminal_id=TERMINAL_ID,
        request_json=request_json,
    )

    result = provider.charge(
        payment_attempt_uuid=(
            "44444444-4444-4444-8444-444444444444"
        ),
        amount=Decimal("4.99"),
    )

    assert result.status == "DECLINED"
    assert result.external_reference is None
    assert calls == []
