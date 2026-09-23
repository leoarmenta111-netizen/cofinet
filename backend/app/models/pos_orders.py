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


class PosOrder(Base):
    __tablename__ = "pos_orders"
    __table_args__ = (
        CheckConstraint(
            "subtotal >= 0",
            name="ck_pos_orders_subtotal_nonnegative",
        ),
        CheckConstraint(
            "total >= 0",
            name="ck_pos_orders_total_nonnegative",
        ),
        CheckConstraint(
            "status IN ('NEW','PREPARING','READY','DELIVERED','CANCELLED')",
            name="ck_pos_orders_status",
        ),
        CheckConstraint(
            "payment_status IN ('PENDING','PAID','REFUNDED')",
            name="ck_pos_orders_payment_status",
        ),
        CheckConstraint(
            "source IN ('POS','KIOSK','BAR_TABLET')",
            name='ck_pos_orders_source',
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    order_uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )

    folio = Column(
        String(40),
        nullable=True,
        unique=True,
        index=True,
    )

    branch_id = Column(
        Integer,
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    customer_id = Column(
        Integer,
        ForeignKey(
            "pos_customers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    customer = relationship(
        "Customer",
        foreign_keys=[customer_id],
    )

    terminal_id = Column(
        String(80),
        nullable=False,
        index=True,
    )

    source = Column(
        String(24),
        nullable=False,
        default='POS',
        server_default='POS',
        index=True,
    )

    self_order_id = Column(
        Integer,
        ForeignKey('self_orders.id', ondelete='SET NULL'),
        nullable=True,
        unique=True,
        index=True,
    )

    status = Column(
        String(24),
        nullable=False,
        default="NEW",
        server_default="NEW",
        index=True,
    )

    payment_status = Column(
        String(24),
        nullable=False,
        default="PAID",
        server_default="PAID",
        index=True,
    )

    subtotal = Column(
        Numeric(12, 2),
        nullable=False,
    )

    total = Column(
        Numeric(12, 2),
        nullable=False,
    )

    currency = Column(
        String(3),
        nullable=False,
        default="MXN",
        server_default="MXN",
    )

    notes = Column(
        Text,
        nullable=True,
    )

    created_at_client = Column(
        DateTime(timezone=True),
        nullable=False,
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

    synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    branch = relationship("Branch")

    self_order = relationship(
        'SelfOrder',
        back_populates='pos_order',
    )

    items = relationship(
        "PosOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    payments = relationship(
        "PosPayment",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    station_states = relationship(
        "PosOrderStation",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class PosOrderStation(Base):
    __tablename__ = "pos_order_stations"
    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "station",
            name="uq_pos_order_stations_order_station",
        ),
        CheckConstraint(
            "station IN ('KITCHEN','BAR')",
            name="ck_pos_order_stations_station",
        ),
        CheckConstraint(
            "status IN ('NEW','PREPARING','READY','DELIVERED')",
            name="ck_pos_order_stations_status",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    order_id = Column(
        Integer,
        ForeignKey(
            "pos_orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    station = Column(
        String(16),
        nullable=False,
        index=True,
    )

    status = Column(
        String(24),
        nullable=False,
        default="NEW",
        server_default="NEW",
        index=True,
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    ready_at = Column(
        DateTime(timezone=True),
        nullable=True,
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

    order = relationship(
        "PosOrder",
        back_populates="station_states",
    )


class PosOrderItem(Base):
    __tablename__ = "pos_order_items"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_pos_order_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_pos_order_items_unit_price_nonnegative",
        ),
        CheckConstraint(
            "line_total >= 0",
            name="ck_pos_order_items_line_total_nonnegative",
        ),
        CheckConstraint(
            "preparation_station IN ('KITCHEN','BAR','NONE')",
            name="ck_pos_order_items_preparation_station",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("pos_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("pos_products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    product_name = Column(
        String(160),
        nullable=False,
    )

    preparation_station = Column(
        String(16),
        nullable=False,
        default="NONE",
        server_default="NONE",
        index=True,
    )

    quantity = Column(
        Integer,
        nullable=False,
    )

    unit_base_price = Column(
        Numeric(12, 2),
        nullable=False,
    )

    unit_modifier_total = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    unit_price = Column(
        Numeric(12, 2),
        nullable=False,
    )

    line_total = Column(
        Numeric(12, 2),
        nullable=False,
    )

    notes = Column(
        Text,
        nullable=True,
    )

    order = relationship(
        "PosOrder",
        back_populates="items",
    )

    modifiers = relationship(
        "PosOrderItemModifier",
        back_populates="order_item",
        cascade="all, delete-orphan",
    )


class PosOrderItemModifier(Base):
    __tablename__ = "pos_order_item_modifiers"

    id = Column(Integer, primary_key=True, index=True)

    order_item_id = Column(
        Integer,
        ForeignKey("pos_order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    modifier_group_id = Column(
        Integer,
        ForeignKey(
            "pos_modifier_groups.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    modifier_option_id = Column(
        Integer,
        ForeignKey(
            "pos_modifier_options.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    group_name = Column(
        String(120),
        nullable=False,
    )

    option_name = Column(
        String(120),
        nullable=False,
    )

    price_delta = Column(
        Numeric(12, 2),
        nullable=False,
    )

    order_item = relationship(
        "PosOrderItem",
        back_populates="modifiers",
    )


class PosPayment(Base):
    __tablename__ = "pos_payments"
    __table_args__ = (
        UniqueConstraint(
            "payment_uuid",
            name="uq_pos_payments_payment_uuid",
        ),
        CheckConstraint(
            "method IN ('CASH','CARD_EXTERNAL')",
            name="ck_pos_payments_method",
        ),
        CheckConstraint(
            "amount >= 0",
            name="ck_pos_payments_amount_nonnegative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    payment_uuid = Column(
        String(36),
        nullable=False,
        index=True,
    )

    order_id = Column(
        Integer,
        ForeignKey("pos_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    method = Column(
        String(24),
        nullable=False,
        index=True,
    )

    amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    amount_tendered = Column(
        Numeric(12, 2),
        nullable=True,
    )

    change_due = Column(
        Numeric(12, 2),
        nullable=True,
    )

    external_reference = Column(
        String(120),
        nullable=True,
    )

    created_at_client = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order = relationship(
        "PosOrder",
        back_populates="payments",
    )
