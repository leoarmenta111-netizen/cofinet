"""multi branch core

Revision ID: 20260816_0001
Revises: 20260724_0002
Create Date: 2026-08-16

"""

from alembic import op
import sqlalchemy as sa


revision = "20260816_0001"
down_revision = "20260724_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # Branches
    # ---------------------------------------------------------

    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_branches_id"),
        "branches",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_branches_code"),
        "branches",
        ["code"],
        unique=True,
    )

    op.create_index(
        op.f("ix_branches_is_active"),
        "branches",
        ["is_active"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Existing production location becomes legacy/default #1.
    #
    # We intentionally use a neutral name because it can later
    # be renamed without changing historical relationships.
    # ---------------------------------------------------------

    op.execute(
        """
        INSERT INTO branches (
            id,
            name,
            code,
            is_active
        )
        VALUES (
            1,
            'Sucursal Principal',
            'principal',
            true
        )
        """
    )

    # Keep PostgreSQL sequence aligned after explicit id=1.
    op.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('branches', 'id'),
            (SELECT MAX(id) FROM branches)
        )
        """
    )

    # ---------------------------------------------------------
    # Purchases
    # ---------------------------------------------------------

    op.add_column(
        "purchases",
        sa.Column(
            "branch_id",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )

    op.create_index(
        op.f("ix_purchases_branch_id"),
        "purchases",
        ["branch_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_purchases_branch_id_branches",
        "purchases",
        "branches",
        ["branch_id"],
        ["id"],
    )

    # ---------------------------------------------------------
    # PIN batches
    # ---------------------------------------------------------

    op.add_column(
        "pin_batches",
        sa.Column(
            "branch_id",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )

    op.create_index(
        op.f("ix_pin_batches_branch_id"),
        "pin_batches",
        ["branch_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_pin_batches_branch_id_branches",
        "pin_batches",
        "branches",
        ["branch_id"],
        ["id"],
    )

    # ---------------------------------------------------------
    # Permanent/internal devices
    # ---------------------------------------------------------

    op.add_column(
        "internal_hotspot_credentials",
        sa.Column(
            "branch_id",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )

    op.create_index(
        op.f("ix_internal_hotspot_credentials_branch_id"),
        "internal_hotspot_credentials",
        ["branch_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_internal_hotspot_credentials_branch_id_branches",
        "internal_hotspot_credentials",
        "branches",
        ["branch_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_internal_hotspot_credentials_branch_id_branches",
        "internal_hotspot_credentials",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_internal_hotspot_credentials_branch_id"),
        table_name="internal_hotspot_credentials",
    )
    op.drop_column(
        "internal_hotspot_credentials",
        "branch_id",
    )

    op.drop_constraint(
        "fk_pin_batches_branch_id_branches",
        "pin_batches",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_pin_batches_branch_id"),
        table_name="pin_batches",
    )
    op.drop_column(
        "pin_batches",
        "branch_id",
    )

    op.drop_constraint(
        "fk_purchases_branch_id_branches",
        "purchases",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_purchases_branch_id"),
        table_name="purchases",
    )
    op.drop_column(
        "purchases",
        "branch_id",
    )

    op.drop_index(
        op.f("ix_branches_is_active"),
        table_name="branches",
    )
    op.drop_index(
        op.f("ix_branches_code"),
        table_name="branches",
    )
    op.drop_index(
        op.f("ix_branches_id"),
        table_name="branches",
    )

    op.drop_table("branches")
