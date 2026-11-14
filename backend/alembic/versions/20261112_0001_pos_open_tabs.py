"""POS open tabs and rounds.

Revision ID: 20261112_0001
Revises: 20261030_0002
"""

from alembic import op
import sqlalchemy as sa


revision = "20261112_0001"
down_revision = "20261030_0002"

branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "pos_tabs",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "tab_uuid",
            sa.String(36),
            nullable=False,
        ),

        sa.Column(
            "branch_id",
            sa.Integer(),
            sa.ForeignKey(
                "branches.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),

        sa.Column(
            "terminal_id",
            sa.String(80),
            nullable=False,
        ),

        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey(
                "pos_customers.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),

        sa.Column(
            "order_type",
            sa.String(40),
            nullable=False,
            server_default="DINE_IN",
        ),

        sa.Column(
            "order_name",
            sa.String(160),
            nullable=True,
        ),

        sa.Column(
            "table_number",
            sa.String(80),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(24),
            nullable=False,
            server_default="OPEN",
        ),

        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "total",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default="MXN",
        ),

        sa.Column(
            "opened_at_client",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "closed_order_id",
            sa.Integer(),
            sa.ForeignKey(
                "pos_orders.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.CheckConstraint(
            "status IN ('OPEN','CLOSED','CANCELLED')",
            name="ck_pos_tabs_status",
        ),

        sa.CheckConstraint(
            "subtotal >= 0",
            name="ck_pos_tabs_subtotal_nonnegative",
        ),

        sa.CheckConstraint(
            "total >= 0",
            name="ck_pos_tabs_total_nonnegative",
        ),

        sa.UniqueConstraint(
            "tab_uuid",
            name="uq_pos_tabs_tab_uuid",
        ),

        sa.UniqueConstraint(
            "closed_order_id",
            name="uq_pos_tabs_closed_order_id",
        ),
    )


    op.create_index(
        "ix_pos_tabs_tab_uuid",
        "pos_tabs",
        ["tab_uuid"],
    )

    op.create_index(
        "ix_pos_tabs_branch_id",
        "pos_tabs",
        ["branch_id"],
    )

    op.create_index(
        "ix_pos_tabs_terminal_id",
        "pos_tabs",
        ["terminal_id"],
    )

    op.create_index(
        "ix_pos_tabs_customer_id",
        "pos_tabs",
        ["customer_id"],
    )

    op.create_index(
        "ix_pos_tabs_status",
        "pos_tabs",
        ["status"],
    )


    op.create_table(
        "pos_tab_rounds",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "round_uuid",
            sa.String(36),
            nullable=False,
        ),

        sa.Column(
            "tab_id",
            sa.Integer(),
            sa.ForeignKey(
                "pos_tabs.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "sequence_no",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "pos_order_id",
            sa.Integer(),
            sa.ForeignKey(
                "pos_orders.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),

        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            nullable=False,
        ),

        sa.Column(
            "total",
            sa.Numeric(12, 2),
            nullable=False,
        ),

        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default="MXN",
        ),

        sa.Column(
            "created_at_client",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.CheckConstraint(
            "sequence_no > 0",
            name="ck_pos_tab_rounds_sequence_positive",
        ),

        sa.CheckConstraint(
            "subtotal >= 0",
            name="ck_pos_tab_rounds_subtotal_nonnegative",
        ),

        sa.CheckConstraint(
            "total >= 0",
            name="ck_pos_tab_rounds_total_nonnegative",
        ),

        sa.UniqueConstraint(
            "round_uuid",
            name="uq_pos_tab_rounds_round_uuid",
        ),

        sa.UniqueConstraint(
            "pos_order_id",
            name="uq_pos_tab_rounds_order",
        ),

        sa.UniqueConstraint(
            "tab_id",
            "sequence_no",
            name="uq_pos_tab_rounds_tab_sequence",
        ),
    )


    op.create_index(
        "ix_pos_tab_rounds_round_uuid",
        "pos_tab_rounds",
        ["round_uuid"],
    )

    op.create_index(
        "ix_pos_tab_rounds_tab_id",
        "pos_tab_rounds",
        ["tab_id"],
    )

    op.create_index(
        "ix_pos_tab_rounds_pos_order_id",
        "pos_tab_rounds",
        ["pos_order_id"],
    )


def downgrade():

    op.drop_table(
        "pos_tab_rounds"
    )

    op.drop_table(
        "pos_tabs"
    )
