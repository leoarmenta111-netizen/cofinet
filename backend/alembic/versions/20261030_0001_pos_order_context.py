"""add POS order type, name and table reference

Revision ID: 20261030_0001
Revises: 20260917_0001
"""

from alembic import op
import sqlalchemy as sa


revision = "20261030_0001"
down_revision = "20260917_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pos_orders",
        sa.Column(
            "order_type",
            sa.String(length=24),
            nullable=False,
            server_default="DINE_IN",
        ),
    )

    op.add_column(
        "pos_orders",
        sa.Column(
            "order_name",
            sa.String(length=120),
            nullable=True,
        ),
    )

    op.add_column(
        "pos_orders",
        sa.Column(
            "table_number",
            sa.String(length=80),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_pos_orders_order_type",
        "pos_orders",
        "order_type IN ('DINE_IN','TAKEOUT','DELIVERY')",
    )


def downgrade():
    op.drop_constraint(
        "ck_pos_orders_order_type",
        "pos_orders",
        type_="check",
    )

    op.drop_column("pos_orders", "table_number")
    op.drop_column("pos_orders", "order_name")
    op.drop_column("pos_orders", "order_type")
