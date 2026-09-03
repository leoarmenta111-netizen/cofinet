from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.pos_catalog import PosProduct
from app.schemas.admin_pos_catalog import (
    AdminPosProductCreate,
    AdminPosProductResponse,
    AdminPosProductUpdate,
)
from app.schemas.pos_catalog import PosCatalogProductResponse


def model_fields(model):
    return getattr(
        model,
        "model_fields",
        getattr(model, "__fields__", {}),
    )


def test_pos_product_has_preparation_station_column():
    assert hasattr(
        PosProduct,
        "preparation_station",
    )

    column = (
        PosProduct
        .__table__
        .c
        .preparation_station
    )

    assert column.nullable is False


def test_admin_product_schemas_expose_preparation_station():
    assert (
        "preparation_station"
        in model_fields(
            AdminPosProductCreate
        )
    )

    assert (
        "preparation_station"
        in model_fields(
            AdminPosProductUpdate
        )
    )

    assert (
        "preparation_station"
        in model_fields(
            AdminPosProductResponse
        )
    )


def test_public_catalog_product_exposes_preparation_station():
    assert (
        "preparation_station"
        in model_fields(
            PosCatalogProductResponse
        )
    )


@pytest.mark.parametrize(
    "station",
    [
        "NONE",
        "KITCHEN",
        "BAR",
    ],
)
def test_admin_product_accepts_valid_preparation_station(
    station,
):
    product = AdminPosProductCreate(
        category_id=1,
        name="Test product",
        base_price=Decimal("50.00"),
        preparation_station=station,
    )

    assert (
        product.preparation_station
        == station
    )


def test_new_product_defaults_to_none_station():
    product = AdminPosProductCreate(
        category_id=1,
        name="Test product",
        base_price=Decimal("50.00"),
    )

    assert (
        product.preparation_station
        == "NONE"
    )


def test_admin_product_rejects_invalid_preparation_station():
    with pytest.raises(
        ValidationError
    ):
        AdminPosProductCreate(
            category_id=1,
            name="Test product",
            base_price=Decimal("50.00"),
            preparation_station="EXPO",
        )



def test_admin_create_product_persists_preparation_station(
    db_session,
):
    from app.models.branch import Branch
    from app.models.pos_catalog import PosCategory
    from app.services.admin_pos_catalog_service import (
        AdminPosCatalogService,
    )

    branch = Branch(
        name="Preparation Station Branch",
        code="prep-station-branch",
        is_active=True,
    )

    category = PosCategory(
        name="Bebidas",
        slug="prep-station-bebidas",
        is_active=True,
    )

    db_session.add_all([branch, category])
    db_session.commit()

    payload = AdminPosProductCreate(
        category_id=category.id,
        name="Latte",
        base_price=Decimal("65.00"),
        preparation_station="BAR",
    )

    result = AdminPosCatalogService.create_product(
        db_session,
        payload,
    )

    stored = (
        db_session.query(PosProduct)
        .filter(PosProduct.name == "Latte")
        .one()
    )

    assert stored.preparation_station == "BAR"

    returned = next(
        item
        for item in result["products"]
        if item["id"] == stored.id
    )

    assert returned["preparation_station"] == "BAR"


def test_admin_update_product_returns_preparation_station(
    db_session,
):
    from app.models.branch import Branch
    from app.models.pos_catalog import PosCategory
    from app.services.admin_pos_catalog_service import (
        AdminPosCatalogService,
    )

    branch = Branch(
        name="Update Station Branch",
        code="update-station-branch",
        is_active=True,
    )

    category = PosCategory(
        name="Comida",
        slug="update-station-comida",
        is_active=True,
    )

    db_session.add_all([branch, category])
    db_session.commit()

    created = AdminPosCatalogService.create_product(
        db_session,
        AdminPosProductCreate(
            category_id=category.id,
            name="Sandwich",
            base_price=Decimal("95.00"),
        ),
    )

    product_id = created["products"][0]["id"]

    result = AdminPosCatalogService.update_product(
        db_session,
        product_id,
        AdminPosProductUpdate(
            preparation_station="KITCHEN",
        ),
    )

    stored = db_session.get(
        PosProduct,
        product_id,
    )

    assert stored.preparation_station == "KITCHEN"

    returned = next(
        item
        for item in result["products"]
        if item["id"] == product_id
    )

    assert returned["preparation_station"] == "KITCHEN"
