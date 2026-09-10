from sqlalchemy import CheckConstraint, UniqueConstraint

import app.models.pos_orders as order_models


def station_model():
    model = getattr(
        order_models,
        "PosOrderStation",
        None,
    )

    assert model is not None, (
        "PosOrderStation model does not exist"
    )

    return model


def named_constraints(table, constraint_type):
    return {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
    }


def test_order_item_persists_preparation_station_snapshot():
    assert hasattr(
        order_models.PosOrderItem,
        "preparation_station",
    )

    column = (
        order_models.PosOrderItem
        .__table__
        .c
        .preparation_station
    )

    assert column.nullable is False
    assert column.server_default is not None

    checks = named_constraints(
        order_models.PosOrderItem.__table__,
        CheckConstraint,
    )

    assert (
        "ck_pos_order_items_preparation_station"
        in checks
    )

    sql = str(
        checks[
            "ck_pos_order_items_preparation_station"
        ].sqltext
    )

    assert "KITCHEN" in sql
    assert "BAR" in sql
    assert "NONE" in sql


def test_pos_order_station_model_exists():
    model = station_model()

    assert (
        model.__tablename__
        == "pos_order_stations"
    )


def test_pos_order_station_has_required_columns():
    model = station_model()

    columns = set(
        model.__table__.columns.keys()
    )

    assert {
        "id",
        "order_id",
        "station",
        "status",
        "started_at",
        "ready_at",
        "created_at",
        "updated_at",
    }.issubset(columns)

    assert (
        model.__table__.c.order_id.nullable
        is False
    )

    assert (
        model.__table__.c.station.nullable
        is False
    )

    assert (
        model.__table__.c.status.nullable
        is False
    )


def test_pos_order_station_has_unique_order_station_pair():
    model = station_model()

    uniques = named_constraints(
        model.__table__,
        UniqueConstraint,
    )

    assert (
        "uq_pos_order_stations_order_station"
        in uniques
    )

    columns = {
        column.name
        for column in uniques[
            "uq_pos_order_stations_order_station"
        ].columns
    }

    assert columns == {
        "order_id",
        "station",
    }


def test_pos_order_station_constrains_station_and_status():
    model = station_model()

    checks = named_constraints(
        model.__table__,
        CheckConstraint,
    )

    assert (
        "ck_pos_order_stations_station"
        in checks
    )

    station_sql = str(
        checks[
            "ck_pos_order_stations_station"
        ].sqltext
    )

    assert "KITCHEN" in station_sql
    assert "BAR" in station_sql

    assert (
        "ck_pos_order_stations_status"
        in checks
    )

    status_sql = str(
        checks[
            "ck_pos_order_stations_status"
        ].sqltext
    )

    assert "NEW" in status_sql
    assert "PREPARING" in status_sql
    assert "READY" in status_sql


def test_order_and_station_models_have_relationships():
    model = station_model()

    assert hasattr(
        order_models.PosOrder,
        "station_states",
    )

    assert hasattr(
        model,
        "order",
    )


# ============================================================
# TASK 3 — Order creation routing + general preparation state
# ============================================================

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.models.pos_orders import (
    PosOrder,
    PosOrderItem,
    PosOrderStation,
)
from app.schemas.pos_orders import (
    PosOrderCreate,
    PosOrderItemResponse,
    PosOrderResponse,
)
from app.services.pos_order_service import PosOrderService


def seed_station_catalog(
    db_session,
    stations,
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Station Branch {suffix}",
        code=f"station-{suffix}",
        is_active=True,
    )

    category = PosCategory(
        name=f"Station Products {suffix}",
        slug=f"station-products-{suffix}",
        is_active=True,
    )

    db_session.add_all([
        branch,
        category,
    ])
    db_session.flush()

    products = []

    for index, station in enumerate(stations):
        product = PosProduct(
            category_id=category.id,
            name=f"Station Product {index} {suffix}",
            base_price=Decimal("50.00"),
            preparation_station=station,
            is_active=True,
        )

        db_session.add(product)
        db_session.flush()

        db_session.add(
            PosBranchProduct(
                branch_id=branch.id,
                product_id=product.id,
                price=None,
                is_available=True,
            )
        )

        products.append(product)

    db_session.flush()

    return branch, products


def station_order_payload(
    branch,
    products,
):
    now = datetime.now(timezone.utc)

    return PosOrderCreate(
        order_uuid=uuid4(),
        branch_code=branch.code,
        terminal_id="STATION-TEST-01",
        created_at_client=now,
        items=[
            {
                "product_id": product.id,
                "quantity": 1,
            }
            for product in products
        ],
        payment={
            "payment_uuid": uuid4(),
            "method": "CASH",
            "amount_tendered": "1000.00",
            "created_at_client": now,
        },
    )


def test_order_response_schemas_expose_station_routing():
    assert (
        "preparation_station"
        in PosOrderItemResponse.model_fields
    )

    assert (
        "stations"
        in PosOrderResponse.model_fields
    )


def test_create_order_snapshots_bar_station(
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        ["BAR"],
    )

    payload = station_order_payload(
        branch,
        products,
    )

    response = PosOrderService.create(
        db_session,
        payload,
    )

    stored = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(payload.order_uuid)
        )
        .one()
    )

    assert len(stored.items) == 1

    assert (
        stored.items[0].preparation_station
        == "BAR"
    )

    assert len(stored.station_states) == 1

    station = stored.station_states[0]

    assert station.station == "BAR"
    assert station.status == "NEW"

    assert (
        response.items[0].preparation_station
        == "BAR"
    )

    assert len(response.stations) == 1
    assert response.stations[0].station == "BAR"
    assert response.stations[0].status == "NEW"

    assert response.status == "NEW"


def test_create_mixed_order_creates_independent_stations(
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        [
            "KITCHEN",
            "BAR",
        ],
    )

    payload = station_order_payload(
        branch,
        products,
    )

    response = PosOrderService.create(
        db_session,
        payload,
    )

    stored = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(payload.order_uuid)
        )
        .one()
    )

    item_stations = {
        item.preparation_station
        for item in stored.items
    }

    assert item_stations == {
        "KITCHEN",
        "BAR",
    }

    station_states = {
        (
            item.station,
            item.status,
        )
        for item in stored.station_states
    }

    assert station_states == {
        ("KITCHEN", "NEW"),
        ("BAR", "NEW"),
    }

    assert response.status == "NEW"

    response_stations = {
        (
            item.station,
            item.status,
        )
        for item in response.stations
    }

    assert response_stations == station_states


def test_none_only_order_is_ready_without_station_ticket(
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        ["NONE"],
    )

    payload = station_order_payload(
        branch,
        products,
    )

    response = PosOrderService.create(
        db_session,
        payload,
    )

    stored = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(payload.order_uuid)
        )
        .one()
    )

    assert (
        stored.items[0].preparation_station
        == "NONE"
    )

    assert stored.station_states == []
    assert stored.status == "READY"

    assert response.stations == []
    assert response.status == "READY"


def test_order_item_station_is_historical_snapshot(
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        ["BAR"],
    )

    product = products[0]

    payload = station_order_payload(
        branch,
        products,
    )

    PosOrderService.create(
        db_session,
        payload,
    )

    product.preparation_station = "KITCHEN"
    db_session.flush()

    stored_item = (
        db_session.query(PosOrderItem)
        .join(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(payload.order_uuid)
        )
        .one()
    )

    assert (
        stored_item.preparation_station
        == "BAR"
    )

    stored_station = (
        db_session.query(PosOrderStation)
        .join(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(payload.order_uuid)
        )
        .one()
    )

    assert stored_station.station == "BAR"


def test_recalculate_general_preparation_status(
    db_session,
):
    branch, products = seed_station_catalog(
        db_session,
        [
            "KITCHEN",
            "BAR",
        ],
    )

    payload = station_order_payload(
        branch,
        products,
    )

    PosOrderService.create(
        db_session,
        payload,
    )

    order = (
        db_session.query(PosOrder)
        .filter(
            PosOrder.order_uuid
            == str(payload.order_uuid)
        )
        .one()
    )

    stations = {
        item.station: item
        for item in order.station_states
    }

    assert order.status == "NEW"

    stations["BAR"].status = "READY"

    PosOrderService._recalculate_preparation_status(
        order
    )

    assert order.status == "PREPARING"

    stations["KITCHEN"].status = "READY"

    PosOrderService._recalculate_preparation_status(
        order
    )

    assert order.status == "READY"

    order.status = "DELIVERED"
    stations["BAR"].status = "NEW"

    PosOrderService._recalculate_preparation_status(
        order
    )

    assert order.status == "DELIVERED"

    order.status = "CANCELLED"

    PosOrderService._recalculate_preparation_status(
        order
    )

    assert order.status == "CANCELLED"
