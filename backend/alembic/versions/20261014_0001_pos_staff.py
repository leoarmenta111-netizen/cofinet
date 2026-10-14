"""Add POS staff authentication foundation.

Revision ID: 20261014_0001
Revises: 20260923_0001
Create Date: 2026-10-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20261014_0001"
down_revision = "20260923_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_staff",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            server_default="CASHIER",
            nullable=False,
        ),
        sa.Column(
            "pin_hash",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
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
            "role IN ('CASHIER','MANAGER')",
            name="ck_pos_staff_role",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_staff_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pos_staff_id",
        "pos_staff",
        ["id"],
    )

    op.create_index(
        "ix_pos_staff_branch_id",
        "pos_staff",
        ["branch_id"],
    )

    op.create_index(
        "ix_pos_staff_role",
        "pos_staff",
        ["role"],
    )

    op.create_index(
        "ix_pos_staff_is_active",
        "pos_staff",
        ["is_active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_staff_is_active",
        table_name="pos_staff",
    )

    op.drop_index(
        "ix_pos_staff_role",
        table_name="pos_staff",
    )

    op.drop_index(
        "ix_pos_staff_branch_id",
        table_name="pos_staff",
    )

    op.drop_index(
        "ix_pos_staff_id",
        table_name="pos_staff",
    )

    op.drop_table("pos_staff")
