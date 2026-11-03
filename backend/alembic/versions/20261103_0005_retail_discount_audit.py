"""Allow Papeleria retail discount audit events.

Revision ID: 20261103_0005
Revises: 20261103_0004
Create Date: 2026-11-03
"""

from alembic import op


revision = "20261103_0005"
down_revision = "20261103_0004"
branch_labels = None
depends_on = None


_CONSTRAINT = (
    "ck_pos_audit_events_event_type"
)

_OLD_CHECK = (
    "event_type IN "
    "('SHIFT_OPENED','SHIFT_CLOSED',"
    "'CASH_MOVEMENT')"
)

_NEW_CHECK = (
    "event_type IN "
    "('SHIFT_OPENED','SHIFT_CLOSED',"
    "'CASH_MOVEMENT',"
    "'RETAIL_DISCOUNT_AUTHORIZED')"
)


def upgrade() -> None:
    op.drop_constraint(
        _CONSTRAINT,
        "pos_audit_events",
        type_="check",
    )

    op.create_check_constraint(
        _CONSTRAINT,
        "pos_audit_events",
        _NEW_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint(
        _CONSTRAINT,
        "pos_audit_events",
        type_="check",
    )

    op.create_check_constraint(
        _CONSTRAINT,
        "pos_audit_events",
        _OLD_CHECK,
    )
