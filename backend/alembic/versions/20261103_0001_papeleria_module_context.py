"""Add operational module context for COFI POS.

Revision ID: 20261103_0001
Revises: 20261030_0002
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0001"
down_revision = "20261030_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pos_staff",
        sa.Column(
            "module_code",
            sa.String(length=20),
            server_default="CAFE",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_pos_staff_module_code",
        "pos_staff",
        "module_code IN ('CAFE','PAPELERIA')",
    )
    op.create_index(
        "ix_pos_staff_module_code",
        "pos_staff",
        ["module_code"],
    )

    op.add_column(
        "pos_cash_shifts",
        sa.Column(
            "module_code",
            sa.String(length=20),
            server_default="CAFE",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_pos_cash_shifts_module_code",
        "pos_cash_shifts",
        "module_code IN ('CAFE','PAPELERIA')",
    )
    op.create_index(
        "ix_pos_cash_shifts_module_code",
        "pos_cash_shifts",
        ["module_code"],
    )

    op.drop_index(
        "uq_pos_cash_shifts_active_branch_terminal",
        table_name="pos_cash_shifts",
    )
    op.create_index(
        "uq_pos_cash_shifts_active_branch_terminal",
        "pos_cash_shifts",
        [
            "branch_id",
            "terminal_id",
            "module_code",
        ],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('OPEN','CLOSING')"
        ),
        sqlite_where=sa.text(
            "status IN ('OPEN','CLOSING')"
        ),
    )

    op.add_column(
        "pos_audit_events",
        sa.Column(
            "module_code",
            sa.String(length=20),
            server_default="CAFE",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_pos_audit_events_module_code",
        "pos_audit_events",
        "module_code IN ('CAFE','PAPELERIA')",
    )
    op.create_index(
        "ix_pos_audit_events_module_code",
        "pos_audit_events",
        ["module_code"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_audit_events_module_code",
        table_name="pos_audit_events",
    )
    op.drop_constraint(
        "ck_pos_audit_events_module_code",
        "pos_audit_events",
        type_="check",
    )
    op.drop_column(
        "pos_audit_events",
        "module_code",
    )

    op.drop_index(
        "uq_pos_cash_shifts_active_branch_terminal",
        table_name="pos_cash_shifts",
    )
    op.create_index(
        "uq_pos_cash_shifts_active_branch_terminal",
        "pos_cash_shifts",
        ["branch_id", "terminal_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('OPEN','CLOSING')"
        ),
        sqlite_where=sa.text(
            "status IN ('OPEN','CLOSING')"
        ),
    )

    op.drop_index(
        "ix_pos_cash_shifts_module_code",
        table_name="pos_cash_shifts",
    )
    op.drop_constraint(
        "ck_pos_cash_shifts_module_code",
        "pos_cash_shifts",
        type_="check",
    )
    op.drop_column(
        "pos_cash_shifts",
        "module_code",
    )

    op.drop_index(
        "ix_pos_staff_module_code",
        table_name="pos_staff",
    )
    op.drop_constraint(
        "ck_pos_staff_module_code",
        "pos_staff",
        type_="check",
    )
    op.drop_column(
        "pos_staff",
        "module_code",
    )
