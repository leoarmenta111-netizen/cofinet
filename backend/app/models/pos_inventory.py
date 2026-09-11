from sqlalchemy import (
    Boolean,
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
from sqlalchemy.sql import func

from app.database.session import Base
from app.models.admin import Admin  # noqa: F401
from app.models.branch import Branch  # noqa: F401
from app.models.pos_catalog import PosProduct  # noqa: F401
from app.models.pos_orders import PosOrder, PosOrderItem  # noqa: F401


class PosInventoryItem(Base):
    __tablename__ = "pos_inventory_items"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            name="uq_pos_inventory_items_product_id",
        ),
        CheckConstraint(
            "unit_code IN ('EA')",
            name="ck_pos_inventory_items_unit_code",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("pos_products.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    name = Column(
        String(160),
        nullable=False,
    )

    unit_code = Column(
        String(16),
        nullable=False,
        default="EA",
        server_default="EA",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PosInventoryBalance(Base):
    __tablename__ = "pos_inventory_balances"
    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "inventory_item_id",
            name="uq_pos_inventory_balances_branch_item",
        ),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_pos_inventory_balances_threshold_nonnegative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    branch_id = Column(
        Integer,
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    inventory_item_id = Column(
        Integer,
        ForeignKey("pos_inventory_items.id", ondelete="RESTRICT"),
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
        nullable=False,
        default=0,
        server_default="0",
    )

    is_tracked = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PosInventoryMovement(Base):
    __tablename__ = "pos_inventory_movements"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_pos_inventory_movements_idempotency_key",
        ),
        CheckConstraint(
            "movement_type IN "
            "('INITIAL','RECEIPT','SALE','SALE_REVERSAL','WASTE','ADJUSTMENT')",
            name="ck_pos_inventory_movements_type",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    branch_id = Column(
        Integer,
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    inventory_item_id = Column(
        Integer,
        ForeignKey("pos_inventory_items.id", ondelete="RESTRICT"),
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

    order_id = Column(
        Integer,
        ForeignKey("pos_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    order_item_id = Column(
        Integer,
        ForeignKey("pos_order_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    idempotency_key = Column(
        String(180),
        nullable=True,
    )

    note = Column(
        Text,
        nullable=True,
    )

    created_by_admin_id = Column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
