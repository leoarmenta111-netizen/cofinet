"""Add immutable POS receipt snapshots.

Revision ID: 20260908_0002
Revises: 20260908_0001
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260908_0002"
down_revision = "20260908_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_receipt_snapshots",
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
            "schema_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_json",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text(
                "CURRENT_TIMESTAMP"
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = 1",
            name=(
                "ck_pos_receipt_snapshots_"
                "schema_version_v1"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["pos_orders.id"],
            name=(
                "fk_pos_receipt_snapshots_"
                "order_id_pos_orders"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pos_receipt_snapshots_order_id",
        "pos_receipt_snapshots",
        ["order_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_receipt_snapshots_order_id",
        table_name="pos_receipt_snapshots",
    )

    op.drop_table(
        "pos_receipt_snapshots"
    )
