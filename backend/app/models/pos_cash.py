from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


ACTIVE_SHIFT_STATUSES = ("OPEN", "CLOSING")

VALID_MXN_DENOMINATIONS_CENTS = (
    100,
    200,
    500,
    1000,
    2000,
    5000,
    10000,
    20000,
    50000,
    100000,
)


class PosCashShift(Base):
    __tablename__ = "pos_cash_shifts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    shift_uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid4()),
    )

    branch_id = Column(
        Integer,
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    terminal_id = Column(
        String(80),
        nullable=False,
        index=True,
    )

    status = Column(
        String(16),
        nullable=False,
        default="OPEN",
        server_default="OPEN",
        index=True,
    )

    opened_by_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    opening_authorized_by_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    opening_total = Column(
        Numeric(12, 2),
        nullable=False,
    )

    opened_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    closed_by_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    closing_authorized_by_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    closing_total = Column(
        Numeric(12, 2),
        nullable=True,
    )

    expected_total = Column(
        Numeric(12, 2),
        nullable=True,
    )

    variance = Column(
        Numeric(12, 2),
        nullable=True,
    )

    variance_note = Column(
        Text,
        nullable=True,
    )

    closed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    denomination_counts = relationship(
        "PosCashDenominationCount",
        back_populates="shift",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN','CLOSING','CLOSED')",
            name="ck_pos_cash_shifts_status",
        ),
        CheckConstraint(
            "opening_total >= 0",
            name="ck_pos_cash_shifts_opening_total_nonnegative",
        ),
        Index(
            "uq_pos_cash_shifts_active_branch_terminal",
            "branch_id",
            "terminal_id",
            unique=True,
            sqlite_where=text(
                "status IN ('OPEN','CLOSING')"
            ),
            postgresql_where=text(
                "status IN ('OPEN','CLOSING')"
            ),
        ),
    )


class PosCashDenominationCount(Base):
    __tablename__ = "pos_cash_denomination_counts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    shift_id = Column(
        Integer,
        ForeignKey(
            "pos_cash_shifts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    stage = Column(
        String(16),
        nullable=False,
        index=True,
    )

    denomination_cents = Column(
        Integer,
        nullable=False,
    )

    quantity = Column(
        Integer,
        nullable=False,
    )

    amount_cents = Column(
        Integer,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    shift = relationship(
        "PosCashShift",
        back_populates="denomination_counts",
    )

    __table_args__ = (
        CheckConstraint(
            "stage IN ('OPENING','CLOSING')",
            name="ck_pos_cash_denomination_counts_stage",
        ),
        CheckConstraint(
            "denomination_cents IN "
            "(100,200,500,1000,2000,5000,"
            "10000,20000,50000,100000)",
            name="ck_pos_cash_denomination_counts_denomination",
        ),
        CheckConstraint(
            "quantity >= 0",
            name="ck_pos_cash_denomination_counts_quantity_nonnegative",
        ),
        CheckConstraint(
            "amount_cents = denomination_cents * quantity",
            name="ck_pos_cash_denomination_counts_amount",
        ),
        UniqueConstraint(
            "shift_id",
            "stage",
            "denomination_cents",
            name="uq_pos_cash_count_shift_stage_denomination",
        ),
    )


class PosCashMovement(Base):
    __tablename__ = "pos_cash_movements"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    movement_uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid4()),
    )

    shift_id = Column(
        Integer,
        ForeignKey(
            "pos_cash_shifts.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    direction = Column(
        String(16),
        nullable=False,
        index=True,
    )

    category = Column(
        String(32),
        nullable=False,
        index=True,
    )

    amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    note = Column(
        Text,
        nullable=False,
    )

    requesting_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    authorizing_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    idempotency_key = Column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "direction IN ('INFLOW','OUTFLOW')",
            name="ck_pos_cash_movements_direction",
        ),
        CheckConstraint(
            "category IN "
            "('CHANGE','EXPENSE','SAFE_WITHDRAWAL',"
            "'DEPOSIT','CORRECTION','OTHER')",
            name="ck_pos_cash_movements_category",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_pos_cash_movements_amount_positive",
        ),
        CheckConstraint(
            "length(trim(note)) > 0",
            name="ck_pos_cash_movements_note_required",
        ),
    )


class PosCashLedgerEntry(Base):
    __tablename__ = "pos_cash_ledger_entries"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    shift_id = Column(
        Integer,
        ForeignKey(
            "pos_cash_shifts.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    entry_type = Column(
        String(40),
        nullable=False,
        index=True,
    )

    amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    idempotency_key = Column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    reference_type = Column(
        String(80),
        nullable=True,
    )

    reference_id = Column(
        String(120),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "amount <> 0",
            name="ck_pos_cash_ledger_entries_amount_nonzero",
        ),
    )
