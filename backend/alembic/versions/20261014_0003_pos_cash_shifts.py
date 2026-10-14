"""Add POS cash shifts and denomination counts.

Revision ID: 20261014_0003
Revises: 20261014_0002
Create Date: 2026-10-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20261014_0003"
down_revision = "20261014_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_cash_shifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "shift_uuid",
            sa.String(length=36),
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
            "status",
            sa.String(length=16),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column(
            "opened_by_staff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "opening_authorized_by_staff_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "opening_total",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "closed_by_staff_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "closing_authorized_by_staff_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "closing_total",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "expected_total",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "variance",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "variance_note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('OPEN','CLOSING','CLOSED')",
            name="ck_pos_cash_shifts_status",
        ),
        sa.CheckConstraint(
            "opening_total >= 0",
            name="ck_pos_cash_shifts_opening_total_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_cash_shifts_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_staff_id"],
            ["pos_staff.id"],
            name="fk_pos_cash_shifts_opened_by_staff_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opening_authorized_by_staff_id"],
            ["pos_staff.id"],
            name="fk_pos_cash_shifts_opening_authorizer",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_staff_id"],
            ["pos_staff.id"],
            name="fk_pos_cash_shifts_closed_by_staff_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["closing_authorized_by_staff_id"],
            ["pos_staff.id"],
            name="fk_pos_cash_shifts_closing_authorizer",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shift_uuid",
            name="uq_pos_cash_shifts_shift_uuid",
        ),
    )

    op.create_index(
        "ix_pos_cash_shifts_id",
        "pos_cash_shifts",
        ["id"],
    )
    op.create_index(
        "ix_pos_cash_shifts_shift_uuid",
        "pos_cash_shifts",
        ["shift_uuid"],
        unique=True,
    )
    op.create_index(
        "ix_pos_cash_shifts_branch_id",
        "pos_cash_shifts",
        ["branch_id"],
    )
    op.create_index(
        "ix_pos_cash_shifts_terminal_id",
        "pos_cash_shifts",
        ["terminal_id"],
    )
    op.create_index(
        "ix_pos_cash_shifts_status",
        "pos_cash_shifts",
        ["status"],
    )
    op.create_index(
        "ix_pos_cash_shifts_opened_by_staff_id",
        "pos_cash_shifts",
        ["opened_by_staff_id"],
    )
    op.create_index(
        "ix_pos_cash_shifts_opening_authorized_by_staff_id",
        "pos_cash_shifts",
        ["opening_authorized_by_staff_id"],
    )
    op.create_index(
        "ix_pos_cash_shifts_opened_at",
        "pos_cash_shifts",
        ["opened_at"],
    )

    # Final database-level race barrier. PostgreSQL production and
    # SQLite regression tests both support partial unique indexes.
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

    op.create_table(
        "pos_cash_denomination_counts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "shift_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "stage",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "denomination_cents",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "amount_cents",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "stage IN ('OPENING','CLOSING')",
            name="ck_pos_cash_denomination_counts_stage",
        ),
        sa.CheckConstraint(
            "denomination_cents IN "
            "(100,200,500,1000,2000,5000,"
            "10000,20000,50000,100000)",
            name="ck_pos_cash_denomination_counts_denomination",
        ),
        sa.CheckConstraint(
            "quantity >= 0",
            name="ck_pos_cash_denomination_counts_quantity_nonnegative",
        ),
        sa.CheckConstraint(
            "amount_cents = denomination_cents * quantity",
            name="ck_pos_cash_denomination_counts_amount",
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["pos_cash_shifts.id"],
            name="fk_pos_cash_counts_shift_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shift_id",
            "stage",
            "denomination_cents",
            name="uq_pos_cash_count_shift_stage_denomination",
        ),
    )

    op.create_index(
        "ix_pos_cash_denomination_counts_id",
        "pos_cash_denomination_counts",
        ["id"],
    )
    op.create_index(
        "ix_pos_cash_denomination_counts_shift_id",
        "pos_cash_denomination_counts",
        ["shift_id"],
    )
    op.create_index(
        "ix_pos_cash_denomination_counts_stage",
        "pos_cash_denomination_counts",
        ["stage"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pos_cash_denomination_counts_stage",
        table_name="pos_cash_denomination_counts",
    )
    op.drop_index(
        "ix_pos_cash_denomination_counts_shift_id",
        table_name="pos_cash_denomination_counts",
    )
    op.drop_index(
        "ix_pos_cash_denomination_counts_id",
        table_name="pos_cash_denomination_counts",
    )
    op.drop_table("pos_cash_denomination_counts")

    op.drop_index(
        "uq_pos_cash_shifts_active_branch_terminal",
        table_name="pos_cash_shifts",
    )
    op.drop_index(
        "ix_pos_cash_shifts_opened_at",
        table_name="pos_cash_shifts",
    )
    op.drop_index(
        "ix_pos_cash_shifts_opening_authorized_by_staff_id",
        table_name="pos_cash_shifts",
    )
    op.drop_index(
        "ix_pos_cash_shifts_opened_by_staff_id",
        table_name="pos_cash_shifts",
    )
    op.drop_index(
        "ix_pos_cash_shifts_status",
        table_name="pos_cash_shifts",
    )
    op.drop_index(
        "ix_pos_cash_shifts_terminal_id",
        table_name="pos_cash_shifts",
    )
    op.drop_index(
        "ix_pos_cash_shifts_branch_id",
        table_name="pos_cash_shifts",
    )
    op.drop_index(
        "ix_pos_cash_shifts_shift_uuid",
        table_name="pos_cash_shifts",
    )
    op.drop_index(
        "ix_pos_cash_shifts_id",
        table_name="pos_cash_shifts",
    )
    op.drop_table("pos_cash_shifts")
