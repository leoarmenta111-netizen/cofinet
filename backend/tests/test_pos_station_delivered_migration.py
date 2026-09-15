import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = Path(
    "alembic/versions/"
    "20260915_0001_pos_station_delivered.py"
)


def load_migration():
    assert MIGRATION_PATH.exists(), (
        "Falta migración de estado DELIVERED "
        "para pos_order_stations"
    )

    spec = importlib.util.spec_from_file_location(
        "pos_station_delivered_migration",
        MIGRATION_PATH,
    )

    migration = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(migration)

    return migration


def test_station_delivered_migration_continues_current_revision():
    migration = load_migration()

    assert migration.revision == "20260915_0001"
    assert migration.down_revision == "20260908_0002"


def test_station_delivered_migration_allows_delivered_and_downgrades():
    migration = load_migration()

    engine = sa.create_engine(
        "sqlite://"
    )

    metadata = sa.MetaData()

    station_table = sa.Table(
        "pos_order_stations",
        metadata,
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "status",
            sa.String(length=24),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "status IN "
                "('NEW','PREPARING','READY')"
            ),
            name=(
                "ck_pos_order_stations_status"
            ),
        ),
    )

    with engine.begin() as connection:
        metadata.create_all(connection)

        context = MigrationContext.configure(
            connection,
            opts={
                "render_as_batch": True,
            },
        )

        operations = Operations(context)

        original_op = migration.op
        migration.op = operations

        try:
            migration.upgrade()

            connection.execute(
                station_table.insert().values(
                    id=1,
                    status="DELIVERED",
                )
            )

            connection.execute(
                station_table.delete()
            )

            migration.downgrade()

            with pytest.raises(
                sa.exc.IntegrityError
            ):
                connection.execute(
                    station_table
                    .insert()
                    .values(
                        id=2,
                        status="DELIVERED",
                    )
                )

        finally:
            migration.op = original_op
