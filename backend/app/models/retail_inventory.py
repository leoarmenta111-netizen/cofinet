from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class RetailInventoryBalance(Base):
    __tablename__ = "retail_inventory_balances"

    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "item_id",
            name=(
                "uq_retail_inventory_balances_"
                "branch_item"
            ),
        ),
        CheckConstraint(
            (
                "low_stock_threshold IS NULL "
                "OR low_stock_threshold >= 0"
            ),
            name=(
                "ck_retail_inventory_balances_"
                "low_stock_nonnegative"
            ),
        ),
        CheckConstraint(
            "max_stock IS NULL OR max_stock >= 0",
            name=(
                "ck_retail_inventory_balances_"
                "max_stock_nonnegative"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
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

    item_id = Column(
        Integer,
        ForeignKey(
            "retail_catalog_items.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity_on_hand = Column(
        Numeric(14, 3),
        nullable=False,
        default=0,
        server_default="0",
    )

    low_stock_threshold = Column(
        Numeric(14, 3),
        nullable=True,
    )

    max_stock = Column(
        Numeric(14, 3),
        nullable=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    branch = relationship("Branch")
    item = relationship("RetailCatalogItem")


class RetailInventoryMovement(Base):
    __tablename__ = "retail_inventory_movements"

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name=(
                "uq_retail_inventory_movements_"
                "idempotency_key"
            ),
        ),
        CheckConstraint(
            (
                "movement_type IN ("
                "'INITIAL',"
                "'MANUAL_ENTRY',"
                "'MANUAL_REMOVAL',"
                "'ADJUSTMENT',"
                "'SALE',"
                "'RETURN',"
                "'CANCELLATION_REVERSAL'"
                ")"
            ),
            name=(
                "ck_retail_inventory_movements_type"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
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

    item_id = Column(
        Integer,
        ForeignKey(
            "retail_catalog_items.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    movement_type = Column(
        String(32),
        nullable=False,
        index=True,
    )

    quantity_delta = Column(
        Numeric(14, 3),
        nullable=False,
    )

    balance_after = Column(
        Numeric(14, 3),
        nullable=False,
    )

    # Retail sales are introduced in the next implementation
    # phase. These IDs intentionally remain nullable scalar
    # references until those tables exist.
    sale_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    sale_line_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    note = Column(
        Text,
        nullable=True,
    )

    actor_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    authorizer_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    created_by_admin_id = Column(
        Integer,
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    idempotency_key = Column(
        String(180),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    branch = relationship("Branch")
    item = relationship("RetailCatalogItem")
