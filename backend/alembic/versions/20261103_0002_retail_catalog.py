"""Add Papeleria retail catalog and presentation models.

Revision ID: 20261103_0002
Revises: 20261103_0001
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0002"
down_revision = "20261103_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retail_catalog_items",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "item_type",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "sku",
            sa.String(length=80),
            nullable=True,
        ),
        sa.Column(
            "name",
            sa.String(length=180),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "category",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "base_unit_code",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "cost",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "inventory_tracked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "low_stock_threshold",
            sa.Numeric(14, 3),
            nullable=True,
        ),
        sa.Column(
            "max_stock",
            sa.Numeric(14, 3),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "item_type IN ('PRODUCT','SERVICE')",
            name="ck_retail_catalog_items_type",
        ),
        sa.CheckConstraint(
            "cost >= 0",
            name=(
                "ck_retail_catalog_items_"
                "cost_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "low_stock_threshold IS NULL "
                "OR low_stock_threshold >= 0"
            ),
            name=(
                "ck_retail_catalog_items_"
                "low_stock_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "max_stock IS NULL OR max_stock >= 0",
            name=(
                "ck_retail_catalog_items_"
                "max_stock_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "item_type = 'PRODUCT' "
                "OR inventory_tracked = false"
            ),
            name=(
                "ck_retail_catalog_items_"
                "service_not_inventory_tracked"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "branch_id",
            "sku",
            name=(
                "uq_retail_catalog_items_"
                "branch_sku"
            ),
        ),
    )

    op.create_index(
        "ix_retail_catalog_items_id",
        "retail_catalog_items",
        ["id"],
    )
    op.create_index(
        "ix_retail_catalog_items_branch_id",
        "retail_catalog_items",
        ["branch_id"],
    )
    op.create_index(
        "ix_retail_catalog_items_item_type",
        "retail_catalog_items",
        ["item_type"],
    )
    op.create_index(
        "ix_retail_catalog_items_sku",
        "retail_catalog_items",
        ["sku"],
    )
    op.create_index(
        "ix_retail_catalog_items_name",
        "retail_catalog_items",
        ["name"],
    )
    op.create_index(
        "ix_retail_catalog_items_category",
        "retail_catalog_items",
        ["category"],
    )
    op.create_index(
        "ix_retail_catalog_items_inventory_tracked",
        "retail_catalog_items",
        ["inventory_tracked"],
    )
    op.create_index(
        "ix_retail_catalog_items_is_active",
        "retail_catalog_items",
        ["is_active"],
    )

    op.create_table(
        "retail_presentations",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "barcode",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "conversion_factor",
            sa.Numeric(14, 3),
            nullable=False,
        ),
        sa.Column(
            "sale_price",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "bulk_price",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "bulk_min_quantity",
            sa.Numeric(14, 3),
            nullable=True,
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "conversion_factor > 0",
            name=(
                "ck_retail_presentations_"
                "conversion_positive"
            ),
        ),
        sa.CheckConstraint(
            "sale_price >= 0",
            name=(
                "ck_retail_presentations_"
                "sale_price_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "bulk_price IS NULL "
                "OR bulk_price >= 0"
            ),
            name=(
                "ck_retail_presentations_"
                "bulk_price_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "bulk_min_quantity IS NULL "
                "OR bulk_min_quantity > 0"
            ),
            name=(
                "ck_retail_presentations_"
                "bulk_min_positive"
            ),
        ),
        sa.CheckConstraint(
            (
                "(bulk_price IS NULL "
                "AND bulk_min_quantity IS NULL) "
                "OR "
                "(bulk_price IS NOT NULL "
                "AND bulk_min_quantity IS NOT NULL)"
            ),
            name=(
                "ck_retail_presentations_"
                "bulk_pair"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["retail_catalog_items.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "branch_id",
            "barcode",
            name=(
                "uq_retail_presentations_"
                "branch_barcode"
            ),
        ),
    )

    op.create_index(
        "ix_retail_presentations_id",
        "retail_presentations",
        ["id"],
    )
    op.create_index(
        "ix_retail_presentations_item_id",
        "retail_presentations",
        ["item_id"],
    )
    op.create_index(
        "ix_retail_presentations_branch_id",
        "retail_presentations",
        ["branch_id"],
    )
    op.create_index(
        "ix_retail_presentations_barcode",
        "retail_presentations",
        ["barcode"],
    )
    op.create_index(
        "ix_retail_presentations_is_default",
        "retail_presentations",
        ["is_default"],
    )
    op.create_index(
        "ix_retail_presentations_is_active",
        "retail_presentations",
        ["is_active"],
    )

    op.create_table(
        "retail_service_price_tiers",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "min_quantity",
            sa.Numeric(14, 3),
            nullable=False,
        ),
        sa.Column(
            "max_quantity",
            sa.Numeric(14, 3),
            nullable=True,
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "min_quantity > 0",
            name=(
                "ck_retail_service_tiers_"
                "min_positive"
            ),
        ),
        sa.CheckConstraint(
            (
                "max_quantity IS NULL "
                "OR max_quantity >= min_quantity"
            ),
            name=(
                "ck_retail_service_tiers_"
                "valid_range"
            ),
        ),
        sa.CheckConstraint(
            "unit_price >= 0",
            name=(
                "ck_retail_service_tiers_"
                "price_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["retail_catalog_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_retail_service_price_tiers_id",
        "retail_service_price_tiers",
        ["id"],
    )
    op.create_index(
        "ix_retail_service_price_tiers_item_id",
        "retail_service_price_tiers",
        ["item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retail_service_price_tiers_item_id",
        table_name="retail_service_price_tiers",
    )
    op.drop_index(
        "ix_retail_service_price_tiers_id",
        table_name="retail_service_price_tiers",
    )
    op.drop_table(
        "retail_service_price_tiers"
    )

    op.drop_index(
        "ix_retail_presentations_is_active",
        table_name="retail_presentations",
    )
    op.drop_index(
        "ix_retail_presentations_is_default",
        table_name="retail_presentations",
    )
    op.drop_index(
        "ix_retail_presentations_barcode",
        table_name="retail_presentations",
    )
    op.drop_index(
        "ix_retail_presentations_branch_id",
        table_name="retail_presentations",
    )
    op.drop_index(
        "ix_retail_presentations_item_id",
        table_name="retail_presentations",
    )
    op.drop_index(
        "ix_retail_presentations_id",
        table_name="retail_presentations",
    )
    op.drop_table(
        "retail_presentations"
    )

    op.drop_index(
        "ix_retail_catalog_items_is_active",
        table_name="retail_catalog_items",
    )
    op.drop_index(
        "ix_retail_catalog_items_inventory_tracked",
        table_name="retail_catalog_items",
    )
    op.drop_index(
        "ix_retail_catalog_items_category",
        table_name="retail_catalog_items",
    )
    op.drop_index(
        "ix_retail_catalog_items_name",
        table_name="retail_catalog_items",
    )
    op.drop_index(
        "ix_retail_catalog_items_sku",
        table_name="retail_catalog_items",
    )
    op.drop_index(
        "ix_retail_catalog_items_item_type",
        table_name="retail_catalog_items",
    )
    op.drop_index(
        "ix_retail_catalog_items_branch_id",
        table_name="retail_catalog_items",
    )
    op.drop_index(
        "ix_retail_catalog_items_id",
        table_name="retail_catalog_items",
    )
    op.drop_table(
        "retail_catalog_items"
    )
