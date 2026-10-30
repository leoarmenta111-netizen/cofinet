"""Add persistent POS audit log.

Revision ID: 20261014_0002
Revises: 20261014_0001
Create Date: 2026-10-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20261014_0002"
down_revision = "20261014_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_audit_events",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "terminal_id",
            sa.String(length=80),
            nullable=False,
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
            "target_type",
            sa.String(length=80),
            nullable=True,
        ),
        sa.Column(
            "target_id",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN "
            "('SHIFT_OPENED','SHIFT_CLOSED','CASH_MOVEMENT')",
            name="ck_pos_audit_events_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_audit_events_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_staff_id"],
            ["pos_staff.id"],
            name="fk_pos_audit_events_actor_staff_id_pos_staff",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["authorizer_staff_id"],
            ["pos_staff.id"],
            name="fk_pos_audit_events_authorizer_staff_id_pos_staff",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pos_audit_events_id",
        "pos_audit_events",
        ["id"],
    )

    op.create_index(
        "ix_pos_audit_events_event_type",
        "pos_audit_events",
        ["event_type"],
    )

    op.create_index(
        "ix_pos_audit_events_branch_id",
        "pos_audit_events",
        ["branch_id"],
    )

    op.create_index(
        "ix_pos_audit_events_terminal_id",
        "pos_audit_events",
        ["terminal_id"],
    )

    op.create_index(
        "ix_pos_audit_events_actor_staff_id",
        "pos_audit_events",
        ["actor_staff_id"],
    )

    op.create_index(
        "ix_pos_audit_events_authorizer_staff_id",
        "pos_audit_events",
        ["authorizer_staff_id"],
    )

    op.create_index(
        "ix_pos_audit_events_created_at",
        "pos_audit_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_audit_events_created_at",
        table_name="pos_audit_events",
    )

    op.drop_index(
        "ix_pos_audit_events_authorizer_staff_id",
        table_name="pos_audit_events",
    )

    op.drop_index(
        "ix_pos_audit_events_actor_staff_id",
        table_name="pos_audit_events",
    )

    op.drop_index(
        "ix_pos_audit_events_terminal_id",
        table_name="pos_audit_events",
    )

    op.drop_index(
        "ix_pos_audit_events_branch_id",
        table_name="pos_audit_events",
    )

    op.drop_index(
        "ix_pos_audit_events_event_type",
        table_name="pos_audit_events",
    )

    op.drop_index(
        "ix_pos_audit_events_id",
        table_name="pos_audit_events",
    )

    op.drop_table("pos_audit_events")
