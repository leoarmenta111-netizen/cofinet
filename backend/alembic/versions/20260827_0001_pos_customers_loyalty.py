"""POS customers and loyalty foundation.

Revision ID: 20260827_0001
Revises: 20260821_0002
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260827_0001"
down_revision = "20260821_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # Global customers
    # ---------------------------------------------------------

    op.create_table(
        "pos_customers",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "customer_uuid",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "phone",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "phone_normalized",
            sa.String(length=24),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=254),
            nullable=True,
        ),
        sa.Column(
            "birthday",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
        sa.UniqueConstraint(
            "customer_uuid",
            name="uq_pos_customers_customer_uuid",
        ),
        sa.UniqueConstraint(
            "phone_normalized",
            name="uq_pos_customers_phone_normalized",
        ),
    )

    op.create_index(
        "ix_pos_customers_id",
        "pos_customers",
        ["id"],
    )

    op.create_index(
        "ix_pos_customers_customer_uuid",
        "pos_customers",
        ["customer_uuid"],
        unique=True,
    )

    op.create_index(
        "ix_pos_customers_name",
        "pos_customers",
        ["name"],
    )

    op.create_index(
        "ix_pos_customers_phone_normalized",
        "pos_customers",
        ["phone_normalized"],
        unique=True,
    )

    op.create_index(
        "ix_pos_customers_last_activity_at",
        "pos_customers",
        ["last_activity_at"],
    )


    # ---------------------------------------------------------
    # Loyalty ledger
    # ---------------------------------------------------------

    op.create_table(
        "pos_loyalty_ledger",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "entry_uuid",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "points",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "entry_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "order_uuid",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            entry_type IN (
                'EARN',
                'REDEEM',
                'SALE_REVERSAL',
                'REDEMPTION_REVERSAL',
                'EXPIRE'
            )
            """,
            name="ck_pos_loyalty_ledger_entry_type",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["pos_customers.id"],
            name="fk_pos_loyalty_ledger_customer_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_loyalty_ledger_branch_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entry_uuid",
            name="uq_pos_loyalty_ledger_entry_uuid",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_pos_loyalty_ledger_idempotency_key",
        ),
    )

    op.create_index(
        "ix_pos_loyalty_ledger_id",
        "pos_loyalty_ledger",
        ["id"],
    )

    op.create_index(
        "ix_pos_loyalty_ledger_entry_uuid",
        "pos_loyalty_ledger",
        ["entry_uuid"],
        unique=True,
    )

    op.create_index(
        "ix_pos_loyalty_ledger_customer_id",
        "pos_loyalty_ledger",
        ["customer_id"],
    )

    op.create_index(
        "ix_pos_loyalty_ledger_entry_type",
        "pos_loyalty_ledger",
        ["entry_type"],
    )

    op.create_index(
        "ix_pos_loyalty_ledger_order_uuid",
        "pos_loyalty_ledger",
        ["order_uuid"],
    )

    op.create_index(
        "ix_pos_loyalty_ledger_branch_id",
        "pos_loyalty_ledger",
        ["branch_id"],
    )

    op.create_index(
        "ix_pos_loyalty_ledger_idempotency_key",
        "pos_loyalty_ledger",
        ["idempotency_key"],
        unique=True,
    )

    op.create_index(
        "ix_pos_loyalty_ledger_created_at",
        "pos_loyalty_ledger",
        ["created_at"],
    )


    # ---------------------------------------------------------
    # Optional customer association on POS order
    # ---------------------------------------------------------

    op.add_column(
        "pos_orders",
        sa.Column(
            "customer_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_pos_orders_customer_id_pos_customers",
        "pos_orders",
        "pos_customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_pos_orders_customer_id",
        "pos_orders",
        ["customer_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_orders_customer_id",
        table_name="pos_orders",
    )

    op.drop_constraint(
        "fk_pos_orders_customer_id_pos_customers",
        "pos_orders",
        type_="foreignkey",
    )

    op.drop_column(
        "pos_orders",
        "customer_id",
    )

    op.drop_table(
        "pos_loyalty_ledger",
    )

    op.drop_table(
        "pos_customers",
    )
