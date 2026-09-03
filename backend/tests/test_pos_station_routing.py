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
