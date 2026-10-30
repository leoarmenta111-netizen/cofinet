"""Add POS cash movement ledger.

Revision ID: 20261014_0004
Revises: 20261014_0003
Create Date: 2026-10-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20261014_0004"
down_revision = "20261014_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_cash_movements",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "movement_uuid",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "shift_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "direction",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "note",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "requesting_staff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "authorizing_staff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "direction IN ('INFLOW','OUTFLOW')",
            name="ck_pos_cash_movements_direction",
        ),
        sa.CheckConstraint(
            "category IN "
            "('CHANGE','EXPENSE','SAFE_WITHDRAWAL',"
            "'DEPOSIT','CORRECTION','OTHER')",
            name="ck_pos_cash_movements_category",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_pos_cash_movements_amount_positive",
        ),
        sa.CheckConstraint(
            "length(trim(note)) > 0",
            name="ck_pos_cash_movements_note_required",
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["pos_cash_shifts.id"],
            name="fk_pos_cash_movements_shift_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requesting_staff_id"],
            ["pos_staff.id"],
            name=(
                "fk_pos_cash_movements_"
                "requesting_staff_id"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["authorizing_staff_id"],
            ["pos_staff.id"],
            name=(
                "fk_pos_cash_movements_"
                "authorizing_staff_id"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pos_cash_movements_id",
        "pos_cash_movements",
        ["id"],
    )
    op.create_index(
        "ix_pos_cash_movements_movement_uuid",
        "pos_cash_movements",
        ["movement_uuid"],
        unique=True,
    )
    op.create_index(
        "ix_pos_cash_movements_shift_id",
        "pos_cash_movements",
        ["shift_id"],
    )
    op.create_index(
        "ix_pos_cash_movements_direction",
        "pos_cash_movements",
        ["direction"],
    )
    op.create_index(
        "ix_pos_cash_movements_category",
        "pos_cash_movements",
        ["category"],
    )
    op.create_index(
        "ix_pos_cash_movements_requesting_staff_id",
        "pos_cash_movements",
        ["requesting_staff_id"],
    )
    op.create_index(
        "ix_pos_cash_movements_authorizing_staff_id",
        "pos_cash_movements",
        ["authorizing_staff_id"],
    )
    op.create_index(
        "ix_pos_cash_movements_idempotency_key",
        "pos_cash_movements",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_pos_cash_movements_created_at",
        "pos_cash_movements",
        ["created_at"],
    )

    op.create_table(
        "pos_cash_ledger_entries",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "shift_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "entry_type",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "reference_type",
            sa.String(length=80),
            nullable=True,
        ),
        sa.Column(
            "reference_id",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount <> 0",
            name=(
                "ck_pos_cash_ledger_entries_"
                "amount_nonzero"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["pos_cash_shifts.id"],
            name="fk_pos_cash_ledger_entries_shift_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pos_cash_ledger_entries_id",
        "pos_cash_ledger_entries",
        ["id"],
    )
    op.create_index(
        "ix_pos_cash_ledger_entries_shift_id",
        "pos_cash_ledger_entries",
        ["shift_id"],
    )
    op.create_index(
        "ix_pos_cash_ledger_entries_entry_type",
        "pos_cash_ledger_entries",
        ["entry_type"],
    )
    op.create_index(
        "ix_pos_cash_ledger_entries_idempotency_key",
        "pos_cash_ledger_entries",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_pos_cash_ledger_entries_created_at",
        "pos_cash_ledger_entries",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_cash_ledger_entries_created_at",
        table_name="pos_cash_ledger_entries",
    )
    op.drop_index(
        "ix_pos_cash_ledger_entries_idempotency_key",
        table_name="pos_cash_ledger_entries",
    )
    op.drop_index(
        "ix_pos_cash_ledger_entries_entry_type",
        table_name="pos_cash_ledger_entries",
    )
    op.drop_index(
        "ix_pos_cash_ledger_entries_shift_id",
        table_name="pos_cash_ledger_entries",
    )
    op.drop_index(
        "ix_pos_cash_ledger_entries_id",
        table_name="pos_cash_ledger_entries",
    )
    op.drop_table("pos_cash_ledger_entries")

    op.drop_index(
        "ix_pos_cash_movements_created_at",
        table_name="pos_cash_movements",
    )
    op.drop_index(
        "ix_pos_cash_movements_idempotency_key",
        table_name="pos_cash_movements",
    )
    op.drop_index(
        "ix_pos_cash_movements_authorizing_staff_id",
        table_name="pos_cash_movements",
    )
    op.drop_index(
        "ix_pos_cash_movements_requesting_staff_id",
        table_name="pos_cash_movements",
    )
    op.drop_index(
        "ix_pos_cash_movements_category",
        table_name="pos_cash_movements",
    )
    op.drop_index(
        "ix_pos_cash_movements_direction",
        table_name="pos_cash_movements",
    )
    op.drop_index(
        "ix_pos_cash_movements_shift_id",
        table_name="pos_cash_movements",
    )
    op.drop_index(
        "ix_pos_cash_movements_movement_uuid",
        table_name="pos_cash_movements",
    )
    op.drop_index(
        "ix_pos_cash_movements_id",
        table_name="pos_cash_movements",
    )
    op.drop_table("pos_cash_movements")
