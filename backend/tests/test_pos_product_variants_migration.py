import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260917_0001_pos_product_variants.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location(
        "pos_product_variants_migration",
        MIGRATION_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def constraint_names(rows):
    return {
        row["name"]
        for row in rows
        if row.get("name")
    }


def fk_targets(inspector, table_name):
    return {
        (
            tuple(row["constrained_columns"]),
            row["referred_table"],
            tuple(row["referred_columns"]),
        )
        for row in inspector.get_foreign_keys(table_name)
    }


def test_product_variants_migration_continues_current_revision():
    assert MIGRATION_PATH.exists(), (
        "Missing migration: "
        "20260917_0001_pos_product_variants.py"
    )

    migration = load_migration()

    assert migration.revision == "20260917_0001"
    assert migration.down_revision == "20260915_0001"


def test_product_variants_migration_creates_schema_and_downgrades():
    migration = load_migration()

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    metadata = sa.MetaData()

    sa.Table(
        "branches",
        metadata,
        sa.Column(
            "id",
            sa.Integer,
            primary_key=True,
        ),
    )

    sa.Table(
        "pos_products",
        metadata,
        sa.Column(
            "id",
            sa.Integer,
            primary_key=True,
        ),
    )

    sa.Table(
        "pos_order_items",
        metadata,
        sa.Column(
            "id",
            sa.Integer,
            primary_key=True,
        ),
    )

    metadata.create_all(engine)

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        migration.op = Operations(context)

        migration.upgrade()

        inspector = sa.inspect(connection)

        table_names = set(
            inspector.get_table_names()
        )

        assert "pos_variant_groups" in table_names
        assert "pos_variants" in table_names
        assert "pos_product_variants" in table_names
        assert "pos_branch_product_variants" in table_names

        group_columns = {
            column["name"]
            for column in inspector.get_columns(
                "pos_variant_groups"
            )
        }

        assert {
            "id",
            "name",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        } <= group_columns

        variant_columns = {
            column["name"]
            for column in inspector.get_columns(
                "pos_variants"
            )
        }

        assert {
            "id",
            "variant_group_id",
            "name",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        } <= variant_columns

        product_variant_columns = {
            column["name"]
            for column in inspector.get_columns(
                "pos_product_variants"
            )
        }

        assert {
            "id",
            "product_id",
            "variant_id",
            "price",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        } <= product_variant_columns

        branch_variant_columns = {
            column["name"]
            for column in inspector.get_columns(
                "pos_branch_product_variants"
            )
        }

        assert {
            "id",
            "branch_id",
            "product_variant_id",
            "price_override",
            "is_available",
            "created_at",
            "updated_at",
        } <= branch_variant_columns

        product_columns = {
            column["name"]
            for column in inspector.get_columns(
                "pos_products"
            )
        }

        assert "variant_group_id" in product_columns

        order_item_columns = {
            column["name"]
            for column in inspector.get_columns(
                "pos_order_items"
            )
        }

        assert "product_variant_id" in order_item_columns
        assert "variant_name" in order_item_columns

        variant_unique_names = constraint_names(
            inspector.get_unique_constraints(
                "pos_variants"
            )
        )

        assert (
            "uq_pos_variants_group_name"
            in variant_unique_names
        )

        product_variant_unique_names = constraint_names(
            inspector.get_unique_constraints(
                "pos_product_variants"
            )
        )

        assert (
            "uq_pos_product_variants_product_variant"
            in product_variant_unique_names
        )

        branch_variant_unique_names = constraint_names(
            inspector.get_unique_constraints(
                "pos_branch_product_variants"
            )
        )

        assert (
            "uq_pos_branch_product_variants_branch_product_variant"
            in branch_variant_unique_names
        )

        product_variant_checks = constraint_names(
            inspector.get_check_constraints(
                "pos_product_variants"
            )
        )

        assert (
            "ck_pos_product_variants_price_nonnegative"
            in product_variant_checks
        )

        branch_variant_checks = constraint_names(
            inspector.get_check_constraints(
                "pos_branch_product_variants"
            )
        )

        assert (
            "ck_pos_branch_product_variants_price_override_nonnegative"
            in branch_variant_checks
        )

        assert (
            ("variant_group_id",),
            "pos_variant_groups",
            ("id",),
        ) in fk_targets(
            inspector,
            "pos_products",
        )

        assert (
            ("variant_group_id",),
            "pos_variant_groups",
            ("id",),
        ) in fk_targets(
            inspector,
            "pos_variants",
        )

        assert (
            ("product_id",),
            "pos_products",
            ("id",),
        ) in fk_targets(
            inspector,
            "pos_product_variants",
        )

        assert (
            ("variant_id",),
            "pos_variants",
            ("id",),
        ) in fk_targets(
            inspector,
            "pos_product_variants",
        )

        assert (
            ("branch_id",),
            "branches",
            ("id",),
        ) in fk_targets(
            inspector,
            "pos_branch_product_variants",
        )

        assert (
            ("product_variant_id",),
            "pos_product_variants",
            ("id",),
        ) in fk_targets(
            inspector,
            "pos_branch_product_variants",
        )

        assert (
            ("product_variant_id",),
            "pos_product_variants",
            ("id",),
        ) in fk_targets(
            inspector,
            "pos_order_items",
        )

        migration.downgrade()

        inspector = sa.inspect(connection)

        remaining_tables = set(
            inspector.get_table_names()
        )

        assert "pos_variant_groups" not in remaining_tables
        assert "pos_variants" not in remaining_tables
        assert "pos_product_variants" not in remaining_tables
        assert (
            "pos_branch_product_variants"
            not in remaining_tables
        )

        assert "variant_group_id" not in {
            column["name"]
            for column in inspector.get_columns(
                "pos_products"
            )
        }

        assert "product_variant_id" not in {
            column["name"]
            for column in inspector.get_columns(
                "pos_order_items"
            )
        }

        assert "variant_name" not in {
            column["name"]
            for column in inspector.get_columns(
                "pos_order_items"
            )
        }
