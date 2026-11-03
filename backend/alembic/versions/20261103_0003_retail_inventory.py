"""Add transactional Papeleria retail inventory.

Revision ID: 20261103_0003
Revises: 20261103_0002
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0003"
down_revision = "20261103_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retail_inventory_balances",
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
            "item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "quantity_on_hand",
            sa.Numeric(14, 3),
            server_default="0",
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
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "low_stock_threshold IS NULL "
                "OR low_stock_threshold >= 0"
            ),
            name=(
                "ck_retail_inventory_balances_"
                "low_stock_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "max_stock IS NULL "
                "OR max_stock >= 0"
            ),
            name=(
                "ck_retail_inventory_balances_"
                "max_stock_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["retail_catalog_items.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "branch_id",
            "item_id",
            name=(
                "uq_retail_inventory_balances_"
                "branch_item"
            ),
        ),
    )

    for column in (
        "id",
        "branch_id",
        "item_id",
    ):
        op.create_index(
            f"ix_retail_inventory_balances_{column}",
            "retail_inventory_balances",
            [column],
        )

    op.create_table(
        "retail_inventory_movements",
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
            "item_id",
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
            sa.Numeric(14, 3),
            nullable=False,
        ),
        sa.Column(
            "balance_after",
            sa.Numeric(14, 3),
            nullable=False,
        ),
        sa.Column(
            "sale_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "sale_line_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "actor_staff_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "authorizer_staff_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_by_admin_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=180),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "movement_type IN ("
                "'INITIAL',"
                "'MANUAL_ENTRY',"
                "'MANUAL_REMOVAL',"
                "'ADJUSTMENT',"
                "'SALE',"
                "'RETURN',"
                "'CANCELLATION_REVERSAL'"
                ")"
            ),
            name=(
                "ck_retail_inventory_movements_type"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["retail_catalog_items.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_staff_id"],
            ["pos_staff.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["authorizer_staff_id"],
            ["pos_staff.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["admins.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name=(
                "uq_retail_inventory_movements_"
                "idempotency_key"
            ),
        ),
    )

    for column in (
        "id",
        "branch_id",
        "item_id",
        "movement_type",
        "sale_id",
        "sale_line_id",
        "actor_staff_id",
        "authorizer_staff_id",
        "created_by_admin_id",
        "idempotency_key",
        "created_at",
    ):
        op.create_index(
            f"ix_retail_inventory_movements_{column}",
            "retail_inventory_movements",
            [column],
        )


def downgrade() -> None:
    for column in reversed(
        (
            "id",
            "branch_id",
            "item_id",
            "movement_type",
            "sale_id",
            "sale_line_id",
            "actor_staff_id",
            "authorizer_staff_id",
            "created_by_admin_id",
            "idempotency_key",
            "created_at",
        )
    ):
        op.drop_index(
            f"ix_retail_inventory_movements_{column}",
            table_name="retail_inventory_movements",
        )

    op.drop_table(
        "retail_inventory_movements"
    )

    for column in reversed(
        (
            "id",
            "branch_id",
            "item_id",
        )
    ):
        op.drop_index(
            f"ix_retail_inventory_balances_{column}",
            table_name="retail_inventory_balances",
        )

    op.drop_table(
        "retail_inventory_balances"
    )
