from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class RetailSale(Base):
    __tablename__ = "retail_sales"

    __table_args__ = (
        UniqueConstraint(
            "sale_uuid",
            name="uq_retail_sales_sale_uuid",
        ),
        CheckConstraint(
            "module_code = 'PAPELERIA'",
            name="ck_retail_sales_module",
        ),
        CheckConstraint(
            (
                "status IN ("
                "'HELD',"
                "'PAID',"
                "'PARTIALLY_RETURNED',"
                "'RETURNED',"
                "'CANCELLED'"
                ")"
            ),
            name="ck_retail_sales_status",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name=(
                "ck_retail_sales_subtotal_nonnegative"
            ),
        ),
        CheckConstraint(
            "discount_total >= 0",
            name=(
                "ck_retail_sales_discount_nonnegative"
            ),
        ),
        CheckConstraint(
            "total >= 0",
            name=(
                "ck_retail_sales_total_nonnegative"
            ),
        ),
        CheckConstraint(
            "discount_total <= subtotal",
            name=(
                "ck_retail_sales_discount_lte_subtotal"
            ),
        ),
        CheckConstraint(
            "currency = 'MXN'",
            name="ck_retail_sales_currency",
        ),
        CheckConstraint(
            (
                "receipt_snapshot IS NULL "
                "OR status <> 'HELD'"
            ),
            name=(
                "ck_retail_sales_held_no_receipt"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    sale_uuid = Column(
        String(36),
        nullable=False,
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

    module_code = Column(
        String(16),
        nullable=False,
        default="PAPELERIA",
        server_default="PAPELERIA",
        index=True,
    )

    terminal_id = Column(
        String(80),
        nullable=False,
        index=True,
    )

    cashier_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    status = Column(
        String(24),
        nullable=False,
        default="HELD",
        server_default="HELD",
        index=True,
    )

    label = Column(
        String(160),
        nullable=True,
    )

    subtotal = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    discount_total = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    total = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    currency = Column(
        String(3),
        nullable=False,
        default="MXN",
        server_default="MXN",
    )

    receipt_snapshot = Column(
        JSON(none_as_null=True),
        nullable=True,
    )

    paid_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    branch = relationship("Branch")

    cashier = relationship(
        "PosStaff",
        foreign_keys=[cashier_staff_id],
    )

    lines = relationship(
        "RetailSaleLine",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="RetailSaleLine.id",
    )

    payments = relationship(
        "RetailPayment",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="RetailPayment.id",
    )

    returns = relationship(
        "RetailReturn",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="RetailReturn.id",
    )


class RetailSaleLine(Base):
    __tablename__ = "retail_sale_lines"

    __table_args__ = (
        CheckConstraint(
            (
                "item_type IN ("
                "'PRODUCT',"
                "'SERVICE'"
                ")"
            ),
            name="ck_retail_sale_lines_item_type",
        ),
        CheckConstraint(
            "conversion_factor > 0",
            name=(
                "ck_retail_sale_lines_conversion_positive"
            ),
        ),
        CheckConstraint(
            "quantity > 0",
            name=(
                "ck_retail_sale_lines_quantity_positive"
            ),
        ),
        CheckConstraint(
            "unit_price >= 0",
            name=(
                "ck_retail_sale_lines_unit_price_nonnegative"
            ),
        ),
        CheckConstraint(
            "line_subtotal >= 0",
            name=(
                "ck_retail_sale_lines_subtotal_nonnegative"
            ),
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name=(
                "ck_retail_sale_lines_discount_nonnegative"
            ),
        ),
        CheckConstraint(
            "line_total >= 0",
            name=(
                "ck_retail_sale_lines_total_nonnegative"
            ),
        ),
        CheckConstraint(
            "discount_amount <= line_subtotal",
            name=(
                "ck_retail_sale_lines_discount_lte_subtotal"
            ),
        ),
        CheckConstraint(
            "unit_cost_snapshot >= 0",
            name=(
                "ck_retail_sale_lines_cost_nonnegative"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    sale_id = Column(
        Integer,
        ForeignKey(
            "retail_sales.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    item_id = Column(
        Integer,
        ForeignKey(
            "retail_catalog_items.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    item_type = Column(
        String(16),
        nullable=False,
        index=True,
    )

    sku = Column(
        String(80),
        nullable=True,
    )

    item_name = Column(
        String(180),
        nullable=False,
    )

    presentation_id = Column(
        Integer,
        ForeignKey(
            "retail_presentations.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    presentation_name = Column(
        String(120),
        nullable=True,
    )

    barcode = Column(
        String(120),
        nullable=True,
    )

    conversion_factor = Column(
        Numeric(14, 3),
        nullable=False,
        default=1,
        server_default="1",
    )

    quantity = Column(
        Numeric(14, 3),
        nullable=False,
    )

    unit_price = Column(
        Numeric(12, 2),
        nullable=False,
    )

    line_subtotal = Column(
        Numeric(12, 2),
        nullable=False,
    )

    discount_amount = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    line_total = Column(
        Numeric(12, 2),
        nullable=False,
    )

    unit_cost_snapshot = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sale = relationship(
        "RetailSale",
        back_populates="lines",
    )


class RetailPayment(Base):
    __tablename__ = "retail_payments"

    __table_args__ = (
        UniqueConstraint(
            "payment_uuid",
            name=(
                "uq_retail_payments_payment_uuid"
            ),
        ),
        UniqueConstraint(
            "sale_id",
            name=(
                "uq_retail_payments_sale_id"
            ),
        ),
        CheckConstraint(
            "method IN ('CASH','CARD')",
            name="ck_retail_payments_method",
        ),
        CheckConstraint(
            "amount >= 0",
            name=(
                "ck_retail_payments_amount_nonnegative"
            ),
        ),
        CheckConstraint(
            (
                "amount_tendered IS NULL "
                "OR amount_tendered >= 0"
            ),
            name=(
                "ck_retail_payments_tendered_nonnegative"
            ),
        ),
        CheckConstraint(
            "change_due >= 0",
            name=(
                "ck_retail_payments_change_nonnegative"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    sale_id = Column(
        Integer,
        ForeignKey(
            "retail_sales.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    payment_uuid = Column(
        String(36),
        nullable=False,
        index=True,
    )

    method = Column(
        String(16),
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
        nullable=False,
        default=0,
        server_default="0",
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

    sale = relationship(
        "RetailSale",
        back_populates="payments",
    )


class RetailReturn(Base):
    __tablename__ = "retail_returns"

    __table_args__ = (
        UniqueConstraint(
            "return_uuid",
            name=(
                "uq_retail_returns_return_uuid"
            ),
        ),
        CheckConstraint(
            "subtotal >= 0",
            name=(
                "ck_retail_returns_subtotal_nonnegative"
            ),
        ),
        CheckConstraint(
            "total >= 0",
            name=(
                "ck_retail_returns_total_nonnegative"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    return_uuid = Column(
        String(36),
        nullable=False,
        index=True,
    )

    sale_id = Column(
        Integer,
        ForeignKey(
            "retail_sales.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    cashier_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    authorizer_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    reason = Column(
        Text,
        nullable=False,
    )

    subtotal = Column(
        Numeric(12, 2),
        nullable=False,
    )

    total = Column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    sale = relationship(
        "RetailSale",
        back_populates="returns",
    )

    cashier = relationship(
        "PosStaff",
        foreign_keys=[cashier_staff_id],
    )

    authorizer = relationship(
        "PosStaff",
        foreign_keys=[authorizer_staff_id],
    )

    lines = relationship(
        "RetailReturnLine",
        back_populates="retail_return",
        cascade="all, delete-orphan",
        order_by="RetailReturnLine.id",
    )


class RetailReturnLine(Base):
    __tablename__ = "retail_return_lines"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name=(
                "ck_retail_return_lines_quantity_positive"
            ),
        ),
        CheckConstraint(
            "unit_amount >= 0",
            name=(
                "ck_retail_return_lines_unit_nonnegative"
            ),
        ),
        CheckConstraint(
            "line_total >= 0",
            name=(
                "ck_retail_return_lines_total_nonnegative"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    return_id = Column(
        Integer,
        ForeignKey(
            "retail_returns.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    sale_line_id = Column(
        Integer,
        ForeignKey(
            "retail_sale_lines.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity = Column(
        Numeric(14, 3),
        nullable=False,
    )

    unit_amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    line_total = Column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    retail_return = relationship(
        "RetailReturn",
        back_populates="lines",
    )

    sale_line = relationship(
        "RetailSaleLine",
    )
