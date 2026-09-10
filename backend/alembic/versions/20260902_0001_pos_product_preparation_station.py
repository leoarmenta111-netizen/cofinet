"""Add POS product preparation station.

Revision ID: 20260902_0001
Revises: 20260827_0001
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0001"
down_revision = "20260827_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pos_products",
        sa.Column(
            "preparation_station",
            sa.String(length=16),
            server_default="NONE",
            nullable=False,
        ),
    )

    op.create_check_constraint(
        "ck_pos_products_preparation_station",
        "pos_products",
        (
            "preparation_station "
            "IN ('KITCHEN','BAR','NONE')"
        ),
    )

    op.create_index(
        "ix_pos_products_preparation_station",
        "pos_products",
        ["preparation_station"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_products_preparation_station",
        table_name="pos_products",
    )

    op.drop_constraint(
        "ck_pos_products_preparation_station",
        "pos_products",
        type_="check",
    )

    op.drop_column(
        "pos_products",
        "preparation_station",
    )
