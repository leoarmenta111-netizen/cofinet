"""Add Papeleria retail sales domain.

Revision ID: 20261103_0004
Revises: 20261103_0003
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0004"
down_revision = "20261103_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retail_sales",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sale_uuid",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "module_code",
            sa.String(length=16),
            server_default="PAPELERIA",
            nullable=False,
        ),
        sa.Column(
            "terminal_id",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "cashier_staff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="HELD",
            nullable=False,
        ),
        sa.Column(
            "label",
            sa.String(length=160),
            nullable=True,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "discount_total",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="MXN",
            nullable=False,
        ),
        sa.Column(
            "receipt_snapshot",
            sa.JSON(none_as_null=True),
            nullable=True,
        ),
        sa.Column(
            "paid_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            "module_code = 'PAPELERIA'",
            name="ck_retail_sales_module",
        ),
        sa.CheckConstraint(
            (
                "status IN ("
                "'HELD',"
                "'PAID',"
                "'PARTIALLY_RETURNED',"
                "'RETURNED',"
                "'CANCELLED'"
                ")"
            ),
            name="ck_retail_sales_status",
        ),
        sa.CheckConstraint(
            "subtotal >= 0",
            name=(
                "ck_retail_sales_subtotal_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "discount_total >= 0",
            name=(
                "ck_retail_sales_discount_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "total >= 0",
            name=(
                "ck_retail_sales_total_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "discount_total <= subtotal",
            name=(
                "ck_retail_sales_discount_lte_subtotal"
            ),
        ),
        sa.CheckConstraint(
            "currency = 'MXN'",
            name="ck_retail_sales_currency",
        ),
        sa.CheckConstraint(
            (
                "receipt_snapshot IS NULL "
                "OR status <> 'HELD'"
            ),
            name=(
                "ck_retail_sales_held_no_receipt"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cashier_staff_id"],
            ["pos_staff.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sale_uuid",
            name="uq_retail_sales_sale_uuid",
        ),
    )

    for column in (
        "id",
        "sale_uuid",
        "branch_id",
        "module_code",
        "terminal_id",
        "cashier_staff_id",
        "status",
        "paid_at",
        "created_at",
    ):
        op.create_index(
            f"ix_retail_sales_{column}",
            "retail_sales",
            [column],
        )

    op.create_table(
        "retail_sale_lines",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sale_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            nullable=True,
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
            "item_name",
            sa.String(length=180),
            nullable=False,
        ),
        sa.Column(
            "presentation_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "presentation_name",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "barcode",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "conversion_factor",
            sa.Numeric(14, 3),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(14, 3),
            nullable=False,
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "line_subtotal",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "discount_amount",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "line_total",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "unit_cost_snapshot",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "item_type IN ("
                "'PRODUCT',"
                "'SERVICE'"
                ")"
            ),
            name="ck_retail_sale_lines_item_type",
        ),
        sa.CheckConstraint(
            "conversion_factor > 0",
            name=(
                "ck_retail_sale_lines_conversion_positive"
            ),
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name=(
                "ck_retail_sale_lines_quantity_positive"
            ),
        ),
        sa.CheckConstraint(
            "unit_price >= 0",
            name=(
                "ck_retail_sale_lines_unit_price_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "line_subtotal >= 0",
            name=(
                "ck_retail_sale_lines_subtotal_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "discount_amount >= 0",
            name=(
                "ck_retail_sale_lines_discount_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "line_total >= 0",
            name=(
                "ck_retail_sale_lines_total_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "discount_amount <= line_subtotal",
            name=(
                "ck_retail_sale_lines_discount_lte_subtotal"
            ),
        ),
        sa.CheckConstraint(
            "unit_cost_snapshot >= 0",
            name=(
                "ck_retail_sale_lines_cost_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["retail_sales.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["retail_catalog_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["retail_presentations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    for column in (
        "id",
        "sale_id",
        "item_id",
        "item_type",
        "presentation_id",
    ):
        op.create_index(
            f"ix_retail_sale_lines_{column}",
            "retail_sale_lines",
            [column],
        )

    op.create_table(
        "retail_payments",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sale_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "payment_uuid",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "method",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "amount_tendered",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "change_due",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "external_reference",
            sa.String(length=160),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "method IN ('CASH','CARD')",
            name="ck_retail_payments_method",
        ),
        sa.CheckConstraint(
            "amount >= 0",
            name=(
                "ck_retail_payments_amount_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "amount_tendered IS NULL "
                "OR amount_tendered >= 0"
            ),
            name=(
                "ck_retail_payments_tendered_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "change_due >= 0",
            name=(
                "ck_retail_payments_change_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["retail_sales.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payment_uuid",
            name=(
                "uq_retail_payments_payment_uuid"
            ),
        ),
        sa.UniqueConstraint(
            "sale_id",
            name=(
                "uq_retail_payments_sale_id"
            ),
        ),
    )

    for column in (
        "id",
        "sale_id",
        "payment_uuid",
        "method",
    ):
        op.create_index(
            f"ix_retail_payments_{column}",
            "retail_payments",
            [column],
        )

    op.create_table(
        "retail_returns",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "return_uuid",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "sale_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "cashier_staff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "authorizer_staff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "total",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "subtotal >= 0",
            name=(
                "ck_retail_returns_subtotal_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "total >= 0",
            name=(
                "ck_retail_returns_total_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["retail_sales.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cashier_staff_id"],
            ["pos_staff.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["authorizer_staff_id"],
            ["pos_staff.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "return_uuid",
            name=(
                "uq_retail_returns_return_uuid"
            ),
        ),
    )

    for column in (
        "id",
        "return_uuid",
        "sale_id",
        "cashier_staff_id",
        "authorizer_staff_id",
        "created_at",
    ):
        op.create_index(
            f"ix_retail_returns_{column}",
            "retail_returns",
            [column],
        )

    op.create_table(
        "retail_return_lines",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "return_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sale_line_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(14, 3),
            nullable=False,
        ),
        sa.Column(
            "unit_amount",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "line_total",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name=(
                "ck_retail_return_lines_quantity_positive"
            ),
        ),
        sa.CheckConstraint(
            "unit_amount >= 0",
            name=(
                "ck_retail_return_lines_unit_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "line_total >= 0",
            name=(
                "ck_retail_return_lines_total_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["return_id"],
            ["retail_returns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sale_line_id"],
            ["retail_sale_lines.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    for column in (
        "id",
        "return_id",
        "sale_line_id",
    ):
        op.create_index(
            f"ix_retail_return_lines_{column}",
            "retail_return_lines",
            [column],
        )


def downgrade() -> None:
    for column in reversed(
        (
            "id",
            "return_id",
            "sale_line_id",
        )
    ):
        op.drop_index(
            f"ix_retail_return_lines_{column}",
            table_name="retail_return_lines",
        )

    op.drop_table("retail_return_lines")

    for column in reversed(
        (
            "id",
            "return_uuid",
            "sale_id",
            "cashier_staff_id",
            "authorizer_staff_id",
            "created_at",
        )
    ):
        op.drop_index(
            f"ix_retail_returns_{column}",
            table_name="retail_returns",
        )

    op.drop_table("retail_returns")

    for column in reversed(
        (
            "id",
            "sale_id",
            "payment_uuid",
            "method",
        )
    ):
        op.drop_index(
            f"ix_retail_payments_{column}",
            table_name="retail_payments",
        )

    op.drop_table("retail_payments")

    for column in reversed(
        (
            "id",
            "sale_id",
            "item_id",
            "item_type",
            "presentation_id",
        )
    ):
        op.drop_index(
            f"ix_retail_sale_lines_{column}",
            table_name="retail_sale_lines",
        )

    op.drop_table("retail_sale_lines")

    for column in reversed(
        (
            "id",
            "sale_uuid",
            "branch_id",
            "module_code",
            "terminal_id",
            "cashier_staff_id",
            "status",
            "paid_at",
            "created_at",
        )
    ):
        op.drop_index(
            f"ix_retail_sales_{column}",
            table_name="retail_sales",
        )

    op.drop_table("retail_sales")
