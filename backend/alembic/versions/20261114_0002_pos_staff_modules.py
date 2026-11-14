"""add POS staff multi-module permissions

Revision ID: 20261114_0002
Revises: 20261114_0001
"""

from alembic import op
import sqlalchemy as sa


revision = "20261114_0002"
down_revision = "20261114_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_staff_modules",
        sa.Column(
            "staff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "module_code",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "module_code IN ('CAFE','PAPELERIA')",
            name="ck_pos_staff_modules_module_code",
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["pos_staff.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "staff_id",
            "module_code",
            name="pk_pos_staff_modules",
        ),
    )

    op.create_index(
        "ix_pos_staff_modules_module_code",
        "pos_staff_modules",
        ["module_code"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO pos_staff_modules (
            staff_id,
            module_code
        )
        SELECT
            id,
            module_code
        FROM pos_staff
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_staff_modules_module_code",
        table_name="pos_staff_modules",
    )

    op.drop_table("pos_staff_modules")
