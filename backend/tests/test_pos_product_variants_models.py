import sqlalchemy as sa

import app.models.pos_catalog as catalog_models
from app.models.pos_orders import PosOrderItem


def constraint_names(table, constraint_type):
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
        and constraint.name
    }


def foreign_key_targets(table):
    return {
        (
            fk.parent.name,
            fk.column.table.name,
            fk.column.name,
            fk.ondelete,
        )
        for fk in table.foreign_keys
    }


def test_variant_models_exist():
    assert hasattr(
        catalog_models,
        "PosVariantGroup",
    ), "PosVariantGroup model is missing"

    assert hasattr(
        catalog_models,
        "PosVariant",
    ), "PosVariant model is missing"

    assert hasattr(
        catalog_models,
        "PosProductVariant",
    ), "PosProductVariant model is missing"

    assert hasattr(
        catalog_models,
        "PosBranchProductVariant",
    ), "PosBranchProductVariant model is missing"


def test_variant_group_model_contract():
    model = catalog_models.PosVariantGroup
    table = model.__table__

    assert table.name == "pos_variant_groups"

    assert {
        "id",
        "name",
        "sort_order",
        "is_active",
        "created_at",
        "updated_at",
    } <= set(table.c.keys())

    assert table.c.name.nullable is False
    assert table.c.sort_order.nullable is False
    assert table.c.is_active.nullable is False


def test_variant_model_contract():
    model = catalog_models.PosVariant
    table = model.__table__

    assert table.name == "pos_variants"

    assert {
        "id",
        "variant_group_id",
        "name",
        "sort_order",
        "is_active",
        "created_at",
        "updated_at",
    } <= set(table.c.keys())

    assert (
        "variant_group_id",
        "pos_variant_groups",
        "id",
        "CASCADE",
    ) in foreign_key_targets(table)

    assert (
        "uq_pos_variants_group_name"
        in constraint_names(
            table,
            sa.UniqueConstraint,
        )
    )


def test_product_variant_model_contract():
    model = catalog_models.PosProductVariant
    table = model.__table__

    assert table.name == "pos_product_variants"

    assert {
        "id",
        "product_id",
        "variant_id",
        "price",
        "is_active",
        "sort_order",
        "created_at",
        "updated_at",
    } <= set(table.c.keys())

    assert (
        "product_id",
        "pos_products",
        "id",
        "CASCADE",
    ) in foreign_key_targets(table)

    assert (
        "variant_id",
        "pos_variants",
        "id",
        "RESTRICT",
    ) in foreign_key_targets(table)

    assert (
        "uq_pos_product_variants_product_variant"
        in constraint_names(
            table,
            sa.UniqueConstraint,
        )
    )

    assert (
        "ck_pos_product_variants_price_nonnegative"
        in constraint_names(
            table,
            sa.CheckConstraint,
        )
    )


def test_branch_product_variant_model_contract():
    model = catalog_models.PosBranchProductVariant
    table = model.__table__

    assert table.name == "pos_branch_product_variants"

    assert {
        "id",
        "branch_id",
        "product_variant_id",
        "price_override",
        "is_available",
        "created_at",
        "updated_at",
    } <= set(table.c.keys())

    assert table.c.price_override.nullable is True

    assert (
        "branch_id",
        "branches",
        "id",
        "CASCADE",
    ) in foreign_key_targets(table)

    assert (
        "product_variant_id",
        "pos_product_variants",
        "id",
        "CASCADE",
    ) in foreign_key_targets(table)

    assert (
        "uq_pos_branch_product_variants_branch_product_variant"
        in constraint_names(
            table,
            sa.UniqueConstraint,
        )
    )

    assert (
        "ck_pos_branch_product_variants_price_override_nonnegative"
        in constraint_names(
            table,
            sa.CheckConstraint,
        )
    )


def test_product_has_nullable_variant_group_assignment():
    table = catalog_models.PosProduct.__table__

    assert "variant_group_id" in table.c
    assert table.c.variant_group_id.nullable is True

    assert (
        "variant_group_id",
        "pos_variant_groups",
        "id",
        "SET NULL",
    ) in foreign_key_targets(table)


def test_order_item_has_variant_history_snapshot():
    table = PosOrderItem.__table__

    assert "product_variant_id" in table.c
    assert "variant_name" in table.c

    assert table.c.product_variant_id.nullable is True
    assert table.c.variant_name.nullable is True

    assert (
        "product_variant_id",
        "pos_product_variants",
        "id",
        "SET NULL",
    ) in foreign_key_targets(table)
