"""add modifier option images

Revision ID: 20261030_0002
Revises: 20261030_0001
"""

from alembic import op
import sqlalchemy as sa


revision = "20261030_0002"
down_revision = "20261030_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pos_modifier_options",
        sa.Column(
            "image_url",
            sa.String(length=500),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "pos_modifier_options",
        "image_url",
    )
