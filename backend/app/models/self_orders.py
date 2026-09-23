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
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class SelfOrderDevice(Base):
    __tablename__ = 'self_order_devices'
    __table_args__ = (
        CheckConstraint(
            "source IN ('KIOSK','BAR_TABLET')",
            name='ck_self_order_devices_source',
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    device_code = Column(
        String(80),
        nullable=False,
        unique=True,
        index=True,
    )

    branch_id = Column(
        Integer,
        ForeignKey('branches.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )

    source = Column(
        String(24),
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default='true',
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

    branch = relationship('Branch')


class SelfOrder(Base):
    __tablename__ = 'self_orders'
    __table_args__ = (
        CheckConstraint(
            "status IN ('AWAITING_PAYMENT','PAYMENT_PROCESSING','PAYMENT_DECLINED','PAYMENT_UNKNOWN','PAID','SUBMITTED','CANCELLED','EXPIRED')",
            name='ck_self_orders_status',
        ),
        CheckConstraint(
            'subtotal >= 0',
            name='ck_self_orders_subtotal_nonnegative',
        ),
        CheckConstraint(
            'total >= 0',
            name='ck_self_orders_total_nonnegative',
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    self_order_uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )

    branch_id = Column(
        Integer,
        ForeignKey('branches.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )

    device_id = Column(
        Integer,
        ForeignKey('self_order_devices.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )

    status = Column(
        String(32),
        nullable=False,
        default='AWAITING_PAYMENT',
        server_default='AWAITING_PAYMENT',
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
        default='MXN',
        server_default='MXN',
    )

    expires_at = Column(
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

    branch = relationship('Branch')
    device = relationship('SelfOrderDevice')

    items = relationship(
        'SelfOrderItem',
        back_populates='self_order',
        cascade='all, delete-orphan',
    )

    payment_attempts = relationship(
        'SelfOrderPaymentAttempt',
        back_populates='self_order',
        cascade='all, delete-orphan',
    )

    pos_order = relationship(
        'PosOrder',
        back_populates='self_order',
        uselist=False,
    )


class SelfOrderItem(Base):
    __tablename__ = 'self_order_items'
    __table_args__ = (
        CheckConstraint(
            'quantity > 0',
            name='ck_self_order_items_quantity_positive',
        ),
        CheckConstraint(
            'unit_base_price >= 0',
            name='ck_self_order_items_base_price_nonnegative',
        ),
        CheckConstraint(
            'unit_price >= 0',
            name='ck_self_order_items_unit_price_nonnegative',
        ),
        CheckConstraint(
            'line_total >= 0',
            name='ck_self_order_items_line_total_nonnegative',
        ),
        CheckConstraint(
            "preparation_station IN ('KITCHEN','BAR','NONE')",
            name='ck_self_order_items_preparation_station',
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    self_order_id = Column(
        Integer,
        ForeignKey('self_orders.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey('pos_products.id', ondelete='SET NULL'),
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
        default='NONE',
        server_default='NONE',
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
        server_default='0',
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

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    self_order = relationship(
        'SelfOrder',
        back_populates='items',
    )

    modifiers = relationship(
        'SelfOrderItemModifier',
        back_populates='item',
        cascade='all, delete-orphan',
    )


class SelfOrderItemModifier(Base):
    __tablename__ = 'self_order_item_modifiers'

    id = Column(Integer, primary_key=True, index=True)

    self_order_item_id = Column(
        Integer,
        ForeignKey('self_order_items.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    modifier_option_id = Column(
        Integer,
        ForeignKey('pos_modifier_options.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
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

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    item = relationship(
        'SelfOrderItem',
        back_populates='modifiers',
    )


class SelfOrderPaymentAttempt(Base):
    __tablename__ = 'self_order_payment_attempts'
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROCESSING','APPROVED','DECLINED','UNKNOWN')",
            name='ck_self_order_payment_attempts_status',
        ),
        CheckConstraint(
            'amount >= 0',
            name='ck_self_order_payment_attempts_amount_nonnegative',
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    payment_attempt_uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )

    self_order_id = Column(
        Integer,
        ForeignKey('self_orders.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    provider = Column(
        String(40),
        nullable=False,
    )

    status = Column(
        String(24),
        nullable=False,
        default='PROCESSING',
        server_default='PROCESSING',
        index=True,
    )

    amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    external_reference = Column(
        String(160),
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

    self_order = relationship(
        'SelfOrder',
        back_populates='payment_attempts',
    )
