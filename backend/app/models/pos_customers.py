from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class Customer(Base):
    __tablename__ = "pos_customers"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    customer_uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )

    name = Column(
        String(160),
        nullable=False,
        index=True,
    )

    phone = Column(
        String(40),
        nullable=False,
    )

    phone_normalized = Column(
        String(24),
        nullable=False,
        unique=True,
        index=True,
    )

    email = Column(
        String(254),
        nullable=True,
    )

    birthday = Column(
        Date,
        nullable=True,
    )

    last_activity_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    loyalty_entries = relationship(
        "LoyaltyLedgerEntry",
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class LoyaltyLedgerEntry(Base):
    __tablename__ = "pos_loyalty_ledger"

    __table_args__ = (
        CheckConstraint(
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
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    entry_uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )

    customer_id = Column(
        Integer,
        ForeignKey(
            "pos_customers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    points = Column(
        Integer,
        nullable=False,
    )

    entry_type = Column(
        String(32),
        nullable=False,
        index=True,
    )

    order_uuid = Column(
        String(36),
        nullable=True,
        index=True,
    )

    branch_id = Column(
        Integer,
        ForeignKey(
            "branches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
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
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    customer = relationship(
        "Customer",
        back_populates="loyalty_entries",
    )
