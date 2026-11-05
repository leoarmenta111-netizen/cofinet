from pathlib import Path

from app.core.config import settings
from app.schemas.self_orders import (
    SelfOrderPaymentAttemptCreate,
)
import app.services.self_order_payment as payment_module


def test_simulation_is_optional_not_required():
    field = (
        SelfOrderPaymentAttemptCreate
        .model_fields["simulated_outcome"]
    )

    assert field.is_required() is False
    assert field.default is None


def test_point_provider_exists():
    provider = getattr(
        payment_module,
        "MercadoPagoPointProvider",
        None,
    )

    assert provider is not None
    assert (
        provider.provider_name
        == "MERCADOPAGO_POINT"
    )


def test_payment_contract_supports_processing_state():
    assert (
        "PROCESSING"
        in payment_module.PAYMENT_OUTCOMES
    )


def test_settings_expose_point_terminal_configuration():
    assert hasattr(
        settings,
        "MERCADOPAGO_POINT_TERMINAL_ID",
    )


def test_point_terminal_and_token_never_live_in_frontend():
    root = Path(__file__).resolve().parents[2]

    frontend_sources = "\n".join(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        for path in (
            root / "customer-order" / "js"
        ).glob("*.js")
    )

    assert (
        "NEWLAND_N950__N950NCD500197607"
        not in frontend_sources
    )

    assert (
        "MERCADOPAGO_ACCESS_TOKEN"
        not in frontend_sources
    )


def test_self_order_api_knows_real_point_provider():
    root = Path(__file__).resolve().parents[2]

    source = (
        root
        / "backend"
        / "app"
        / "api"
        / "self_orders.py"
    ).read_text(
        encoding="utf-8",
    )

    assert "MercadoPagoPointProvider" in source


def test_point_provider_contract_contains_orders_api():
    root = Path(__file__).resolve().parents[2]

    source = (
        root
        / "backend"
        / "app"
        / "services"
        / "self_order_payment.py"
    ).read_text(
        encoding="utf-8",
    )

    assert "/v1/orders" in source
    assert "X-Idempotency-Key" in source
    assert "terminal_id" in source
    assert "processing_mode" not in source


def test_pending_point_order_stays_processing():
    root = Path(__file__).resolve().parents[2]

    source = (
        root
        / "backend"
        / "app"
        / "services"
        / "self_order_payment.py"
    ).read_text(
        encoding="utf-8",
    )

    assert (
        "result_status == 'PROCESSING'"
        in source
    )

    assert (
        "'PAYMENT_PROCESSING'"
        in source
    )
