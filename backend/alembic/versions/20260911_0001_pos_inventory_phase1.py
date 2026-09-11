"""Add POS inventory phase 1.

Revision ID: 20260911_0001
Revises: 20260908_0002
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_0001"
down_revision = "20260908_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_inventory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "unit_code",
            sa.String(length=16),
            server_default=sa.text("'EA'"),
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
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "unit_code IN ('EA')",
            name="ck_pos_inventory_items_unit_code",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["pos_products.id"],
            name="fk_pos_inventory_items_product_id_pos_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            name="uq_pos_inventory_items_product_id",
        ),
    )

    op.create_index(
        "ix_pos_inventory_items_id",
        "pos_inventory_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_items_product_id",
        "pos_inventory_items",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_items_is_active",
        "pos_inventory_items",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "pos_inventory_balances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column(
            "inventory_item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "quantity_on_hand",
            sa.Numeric(precision=14, scale=3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "low_stock_threshold",
            sa.Numeric(precision=14, scale=3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_tracked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_pos_inventory_balances_threshold_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_inventory_balances_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pos_inventory_items.id"],
            name="fk_pos_inventory_balances_item_id_items",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "branch_id",
            "inventory_item_id",
            name="uq_pos_inventory_balances_branch_item",
        ),
    )

    op.create_index(
        "ix_pos_inventory_balances_id",
        "pos_inventory_balances",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_balances_branch_id",
        "pos_inventory_balances",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_balances_inventory_item_id",
        "pos_inventory_balances",
        ["inventory_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_balances_is_tracked",
        "pos_inventory_balances",
        ["is_tracked"],
        unique=False,
    )

    op.create_table(
        "pos_inventory_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column(
            "inventory_item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "movement_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "quantity_delta",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "balance_after",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("order_item_id", sa.Integer(), nullable=True),
        sa.Column(
            "idempotency_key",
            sa.String(length=180),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_by_admin_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "movement_type IN "
            "('INITIAL','RECEIPT','SALE','SALE_REVERSAL','WASTE','ADJUSTMENT')",
            name="ck_pos_inventory_movements_type",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_inventory_movements_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pos_inventory_items.id"],
            name="fk_pos_inventory_movements_item_id_items",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["pos_orders.id"],
            name="fk_pos_inventory_movements_order_id_pos_orders",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["pos_order_items.id"],
            name="fk_pos_inventory_movements_order_item_id_pos_order_items",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["admins.id"],
            name="fk_pos_inventory_movements_admin_id_admins",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_pos_inventory_movements_idempotency_key",
        ),
    )

    op.create_index(
        "ix_pos_inventory_movements_id",
        "pos_inventory_movements",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_movements_branch_id",
        "pos_inventory_movements",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_movements_inventory_item_id",
        "pos_inventory_movements",
        ["inventory_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_movements_movement_type",
        "pos_inventory_movements",
        ["movement_type"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_movements_order_id",
        "pos_inventory_movements",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_movements_order_item_id",
        "pos_inventory_movements",
        ["order_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_pos_inventory_movements_created_by_admin_id",
        "pos_inventory_movements",
        ["created_by_admin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_inventory_movements_created_by_admin_id",
        table_name="pos_inventory_movements",
    )
    op.drop_index(
        "ix_pos_inventory_movements_order_item_id",
        table_name="pos_inventory_movements",
    )
    op.drop_index(
        "ix_pos_inventory_movements_order_id",
        table_name="pos_inventory_movements",
    )
    op.drop_index(
        "ix_pos_inventory_movements_movement_type",
        table_name="pos_inventory_movements",
    )
    op.drop_index(
        "ix_pos_inventory_movements_inventory_item_id",
        table_name="pos_inventory_movements",
    )
    op.drop_index(
        "ix_pos_inventory_movements_branch_id",
        table_name="pos_inventory_movements",
    )
    op.drop_index(
        "ix_pos_inventory_movements_id",
        table_name="pos_inventory_movements",
    )
    op.drop_table("pos_inventory_movements")

    op.drop_index(
        "ix_pos_inventory_balances_is_tracked",
        table_name="pos_inventory_balances",
    )
    op.drop_index(
        "ix_pos_inventory_balances_inventory_item_id",
        table_name="pos_inventory_balances",
    )
    op.drop_index(
        "ix_pos_inventory_balances_branch_id",
        table_name="pos_inventory_balances",
    )
    op.drop_index(
        "ix_pos_inventory_balances_id",
        table_name="pos_inventory_balances",
    )
    op.drop_table("pos_inventory_balances")

    op.drop_index(
        "ix_pos_inventory_items_is_active",
        table_name="pos_inventory_items",
    )
    op.drop_index(
        "ix_pos_inventory_items_product_id",
        table_name="pos_inventory_items",
    )
    op.drop_index(
        "ix_pos_inventory_items_id",
        table_name="pos_inventory_items",
    )
    op.drop_table("pos_inventory_items")
