"""Allow delivered status for POS preparation stations.

Revision ID: 20260915_0001
Revises: 20260908_0002
Create Date: 2026-09-15
"""

from alembic import op


revision = "20260915_0001"
down_revision = "20260908_0002"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = (
    "ck_pos_order_stations_status"
)

OLD_STATUS_CHECK = (
    "status IN "
    "('NEW','PREPARING','READY')"
)

NEW_STATUS_CHECK = (
    "status IN "
    "('NEW','PREPARING','READY','DELIVERED')"
)


def upgrade() -> None:
    with op.batch_alter_table(
        "pos_order_stations"
    ) as batch_op:
        batch_op.drop_constraint(
            CONSTRAINT_NAME,
            type_="check",
        )

        batch_op.create_check_constraint(
            CONSTRAINT_NAME,
            NEW_STATUS_CHECK,
        )


def downgrade() -> None:
    op.execute(
        "UPDATE pos_order_stations "
        "SET status = 'READY' "
        "WHERE status = 'DELIVERED'"
    )

    with op.batch_alter_table(
        "pos_order_stations"
    ) as batch_op:
        batch_op.drop_constraint(
            CONSTRAINT_NAME,
            type_="check",
        )

        batch_op.create_check_constraint(
            CONSTRAINT_NAME,
            OLD_STATUS_CHECK,
        )
