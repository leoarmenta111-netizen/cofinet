"""POS orders

Revision ID: 20260821_0002
Revises: 20260821_0001
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0002"
down_revision = "20260821_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_uuid", sa.String(36), nullable=False),
        sa.Column("folio", sa.String(40), nullable=True),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("terminal_id", sa.String(80), nullable=False),
        sa.Column(
            "status",
            sa.String(24),
            server_default="NEW",
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.String(24),
            server_default="PAID",
            nullable=False,
        ),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "currency",
            sa.String(3),
            server_default="MXN",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at_client",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "subtotal >= 0",
            name="ck_pos_orders_subtotal_nonnegative",
        ),
        sa.CheckConstraint(
            "total >= 0",
            name="ck_pos_orders_total_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('NEW','PREPARING','READY','DELIVERED','CANCELLED')",
            name="ck_pos_orders_status",
        ),
        sa.CheckConstraint(
            "payment_status IN ('PENDING','PAID','REFUNDED')",
            name="ck_pos_orders_payment_status",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_orders_branch_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_uuid"),
        sa.UniqueConstraint("folio"),
    )

    op.create_index("ix_pos_orders_id", "pos_orders", ["id"])
    op.create_index(
        "ix_pos_orders_order_uuid",
        "pos_orders",
        ["order_uuid"],
        unique=True,
    )
    op.create_index(
        "ix_pos_orders_folio",
        "pos_orders",
        ["folio"],
        unique=True,
    )
    op.create_index(
        "ix_pos_orders_branch_id",
        "pos_orders",
        ["branch_id"],
    )
    op.create_index(
        "ix_pos_orders_terminal_id",
        "pos_orders",
        ["terminal_id"],
    )
    op.create_index(
        "ix_pos_orders_status",
        "pos_orders",
        ["status"],
    )
    op.create_index(
        "ix_pos_orders_payment_status",
        "pos_orders",
        ["payment_status"],
    )

    op.create_table(
        "pos_order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "unit_base_price",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "unit_modifier_total",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "line_total",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_pos_order_items_quantity_positive",
        ),
        sa.CheckConstraint(
            "unit_price >= 0",
            name="ck_pos_order_items_unit_price_nonnegative",
        ),
        sa.CheckConstraint(
            "line_total >= 0",
            name="ck_pos_order_items_line_total_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["pos_orders.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["pos_products.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pos_order_items_id",
        "pos_order_items",
        ["id"],
    )
    op.create_index(
        "ix_pos_order_items_order_id",
        "pos_order_items",
        ["order_id"],
    )
    op.create_index(
        "ix_pos_order_items_product_id",
        "pos_order_items",
        ["product_id"],
    )

    op.create_table(
        "pos_order_item_modifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "order_item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "modifier_group_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "modifier_option_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "group_name",
            sa.String(120),
            nullable=False,
        ),
        sa.Column(
            "option_name",
            sa.String(120),
            nullable=False,
        ),
        sa.Column(
            "price_delta",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["pos_order_items.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["modifier_group_id"],
            ["pos_modifier_groups.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["modifier_option_id"],
            ["pos_modifier_options.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pos_order_item_modifiers_id",
        "pos_order_item_modifiers",
        ["id"],
    )
    op.create_index(
        "ix_pos_order_item_modifiers_order_item_id",
        "pos_order_item_modifiers",
        ["order_item_id"],
    )

    op.create_table(
        "pos_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "payment_uuid",
            sa.String(36),
            nullable=False,
        ),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(24), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "amount_tendered",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "change_due",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "external_reference",
            sa.String(120),
            nullable=True,
        ),
        sa.Column(
            "created_at_client",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "method IN ('CASH','CARD_EXTERNAL')",
            name="ck_pos_payments_method",
        ),
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_pos_payments_amount_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["pos_orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payment_uuid",
            name="uq_pos_payments_payment_uuid",
        ),
    )

    op.create_index(
        "ix_pos_payments_id",
        "pos_payments",
        ["id"],
    )
    op.create_index(
        "ix_pos_payments_payment_uuid",
        "pos_payments",
        ["payment_uuid"],
    )
    op.create_index(
        "ix_pos_payments_order_id",
        "pos_payments",
        ["order_id"],
    )
    op.create_index(
        "ix_pos_payments_method",
        "pos_payments",
        ["method"],
    )


def downgrade() -> None:
    op.drop_table("pos_payments")
    op.drop_table("pos_order_item_modifiers")
    op.drop_table("pos_order_items")
    op.drop_table("pos_orders")
