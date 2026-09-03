"""Persist POS order preparation routing.

Revision ID: 20260902_0002
Revises: 20260902_0001
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0002"
down_revision = "20260902_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pos_order_items",
        sa.Column(
            "preparation_station",
            sa.String(length=16),
            server_default="NONE",
            nullable=False,
        ),
    )

    op.create_check_constraint(
        "ck_pos_order_items_preparation_station",
        "pos_order_items",
        (
            "preparation_station "
            "IN ('KITCHEN','BAR','NONE')"
        ),
    )

    op.create_index(
        "ix_pos_order_items_preparation_station",
        "pos_order_items",
        ["preparation_station"],
    )

    op.create_table(
        "pos_order_stations",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "station",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="NEW",
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ready_at",
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
            "station IN ('KITCHEN','BAR')",
            name="ck_pos_order_stations_station",
        ),
        sa.CheckConstraint(
            "status IN ('NEW','PREPARING','READY')",
            name="ck_pos_order_stations_status",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["pos_orders.id"],
            name="fk_pos_order_stations_order_id_pos_orders",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "order_id",
            "station",
            name="uq_pos_order_stations_order_station",
        ),
    )

    op.create_index(
        "ix_pos_order_stations_id",
        "pos_order_stations",
        ["id"],
    )

    op.create_index(
        "ix_pos_order_stations_order_id",
        "pos_order_stations",
        ["order_id"],
    )

    op.create_index(
        "ix_pos_order_stations_station",
        "pos_order_stations",
        ["station"],
    )

    op.create_index(
        "ix_pos_order_stations_status",
        "pos_order_stations",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_order_stations_status",
        table_name="pos_order_stations",
    )

    op.drop_index(
        "ix_pos_order_stations_station",
        table_name="pos_order_stations",
    )

    op.drop_index(
        "ix_pos_order_stations_order_id",
        table_name="pos_order_stations",
    )

    op.drop_index(
        "ix_pos_order_stations_id",
        table_name="pos_order_stations",
    )

    op.drop_table(
        "pos_order_stations",
    )

    op.drop_index(
        "ix_pos_order_items_preparation_station",
        table_name="pos_order_items",
    )

    op.drop_constraint(
        "ck_pos_order_items_preparation_station",
        "pos_order_items",
        type_="check",
    )

    op.drop_column(
        "pos_order_items",
        "preparation_station",
    )
