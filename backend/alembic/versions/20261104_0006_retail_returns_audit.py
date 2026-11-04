"""retail returns and cancellation audit events

Revision ID: 20261104_0006
Revises: 20261103_0005
"""

from alembic import op


revision = "20261104_0006"
down_revision = "20261103_0005"
branch_labels = None
depends_on = None


OLD_EVENTS = (
    "event_type IN "
    "('SHIFT_OPENED','SHIFT_CLOSED',"
    "'CASH_MOVEMENT',"
    "'RETAIL_DISCOUNT_AUTHORIZED')"
)

NEW_EVENTS = (
    "event_type IN "
    "('SHIFT_OPENED','SHIFT_CLOSED',"
    "'CASH_MOVEMENT',"
    "'RETAIL_DISCOUNT_AUTHORIZED',"
    "'RETAIL_RETURN_AUTHORIZED',"
    "'RETAIL_CANCELLATION_AUTHORIZED')"
)


def _replace_constraint(
    expression: str,
) -> None:
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "pos_audit_events"
        ) as batch_op:
            batch_op.drop_constraint(
                "ck_pos_audit_events_event_type",
                type_="check",
            )
            batch_op.create_check_constraint(
                "ck_pos_audit_events_event_type",
                expression,
            )
        return

    op.drop_constraint(
        "ck_pos_audit_events_event_type",
        "pos_audit_events",
        type_="check",
    )

    op.create_check_constraint(
        "ck_pos_audit_events_event_type",
        "pos_audit_events",
        expression,
    )


def upgrade() -> None:
    _replace_constraint(NEW_EVENTS)


def downgrade() -> None:
    _replace_constraint(OLD_EVENTS)
