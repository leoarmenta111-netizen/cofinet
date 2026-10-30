from pathlib import Path

from app.models.pos_catalog import (
    PosModifierOption,
)
from app.schemas.admin_pos_catalog import (
    AdminPosModifierOptionResponse,
)
from app.schemas.pos_catalog import (
    PosModifierOptionResponse,
)
from app.services.pos_modifier_option_image_service import (
    PosModifierOptionImageService,
)


def test_modifier_option_model_has_image_url():
    assert hasattr(
        PosModifierOption,
        "image_url",
    )


def test_public_modifier_schema_exposes_image_url():
    model = PosModifierOptionResponse(
        id=1,
        name="Almendras",
        price_delta="25.00",
        image_url=(
            "/media/pos-products/"
            "modifier-test.webp"
        ),
        sort_order=0,
    )

    assert model.image_url.endswith(
        "modifier-test.webp"
    )


def test_admin_modifier_schema_exposes_image_url():
    model = AdminPosModifierOptionResponse(
        id=1,
        name="Almendras",
        price_delta="25.00",
        image_url=(
            "/media/pos-products/"
            "modifier-test.webp"
        ),
        sort_order=0,
        is_active=True,
    )

    assert model.image_url is not None


def test_modifier_managed_image_path():
    result = (
        PosModifierOptionImageService
        ._managed_path(
            "/media/pos-products/"
            "modifier-test.webp"
        )
    )

    assert isinstance(
        result,
        Path,
    )

    assert result.name == (
        "modifier-test.webp"
    )


def test_modifier_rejects_unmanaged_path():
    assert (
        PosModifierOptionImageService
        ._managed_path(
            "https://example.com/test.webp"
        )
        is None
    )
