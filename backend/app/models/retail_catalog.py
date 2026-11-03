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
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class RetailCatalogItem(Base):
    __tablename__ = "retail_catalog_items"

    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "sku",
            name="uq_retail_catalog_items_branch_sku",
        ),
        CheckConstraint(
            "item_type IN ('PRODUCT','SERVICE')",
            name="ck_retail_catalog_items_type",
        ),
        CheckConstraint(
            "cost >= 0",
            name="ck_retail_catalog_items_cost_nonnegative",
        ),
        CheckConstraint(
            (
                "low_stock_threshold IS NULL "
                "OR low_stock_threshold >= 0"
            ),
            name=(
                "ck_retail_catalog_items_"
                "low_stock_nonnegative"
            ),
        ),
        CheckConstraint(
            "max_stock IS NULL OR max_stock >= 0",
            name=(
                "ck_retail_catalog_items_"
                "max_stock_nonnegative"
            ),
        ),
        CheckConstraint(
            (
                "item_type = 'PRODUCT' "
                "OR inventory_tracked = false"
            ),
            name=(
                "ck_retail_catalog_items_"
                "service_not_inventory_tracked"
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
            ondelete="CASCADE",
        ),
        nullable=False,
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
        index=True,
    )

    name = Column(
        String(180),
        nullable=False,
        index=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    category = Column(
        String(120),
        nullable=True,
        index=True,
    )

    base_unit_code = Column(
        String(32),
        nullable=False,
    )

    cost = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    inventory_tracked = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    low_stock_threshold = Column(
        Numeric(14, 3),
        nullable=True,
    )

    max_stock = Column(
        Numeric(14, 3),
        nullable=True,
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

    branch = relationship(
        "Branch",
    )

    presentations = relationship(
        "RetailPresentation",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="RetailPresentation.id",
    )

    service_price_tiers = relationship(
        "RetailServicePriceTier",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="RetailServicePriceTier.min_quantity",
    )


class RetailPresentation(Base):
    __tablename__ = "retail_presentations"

    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "barcode",
            name=(
                "uq_retail_presentations_"
                "branch_barcode"
            ),
        ),
        CheckConstraint(
            "conversion_factor > 0",
            name=(
                "ck_retail_presentations_"
                "conversion_positive"
            ),
        ),
        CheckConstraint(
            "sale_price >= 0",
            name=(
                "ck_retail_presentations_"
                "sale_price_nonnegative"
            ),
        ),
        CheckConstraint(
            (
                "bulk_price IS NULL "
                "OR bulk_price >= 0"
            ),
            name=(
                "ck_retail_presentations_"
                "bulk_price_nonnegative"
            ),
        ),
        CheckConstraint(
            (
                "bulk_min_quantity IS NULL "
                "OR bulk_min_quantity > 0"
            ),
            name=(
                "ck_retail_presentations_"
                "bulk_min_positive"
            ),
        ),
        CheckConstraint(
            (
                "(bulk_price IS NULL "
                "AND bulk_min_quantity IS NULL) "
                "OR "
                "(bulk_price IS NOT NULL "
                "AND bulk_min_quantity IS NOT NULL)"
            ),
            name=(
                "ck_retail_presentations_"
                "bulk_pair"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    item_id = Column(
        Integer,
        ForeignKey(
            "retail_catalog_items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    branch_id = Column(
        Integer,
        ForeignKey(
            "branches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name = Column(
        String(120),
        nullable=False,
    )

    barcode = Column(
        String(120),
        nullable=True,
        index=True,
    )

    conversion_factor = Column(
        Numeric(14, 3),
        nullable=False,
    )

    sale_price = Column(
        Numeric(12, 2),
        nullable=False,
    )

    bulk_price = Column(
        Numeric(12, 2),
        nullable=True,
    )

    bulk_min_quantity = Column(
        Numeric(14, 3),
        nullable=True,
    )

    is_default = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
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

    item = relationship(
        "RetailCatalogItem",
        back_populates="presentations",
    )

    branch = relationship(
        "Branch",
    )


class RetailServicePriceTier(Base):
    __tablename__ = "retail_service_price_tiers"

    __table_args__ = (
        CheckConstraint(
            "min_quantity > 0",
            name=(
                "ck_retail_service_tiers_"
                "min_positive"
            ),
        ),
        CheckConstraint(
            (
                "max_quantity IS NULL "
                "OR max_quantity >= min_quantity"
            ),
            name=(
                "ck_retail_service_tiers_"
                "valid_range"
            ),
        ),
        CheckConstraint(
            "unit_price >= 0",
            name=(
                "ck_retail_service_tiers_"
                "price_nonnegative"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    item_id = Column(
        Integer,
        ForeignKey(
            "retail_catalog_items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    min_quantity = Column(
        Numeric(14, 3),
        nullable=False,
    )

    max_quantity = Column(
        Numeric(14, 3),
        nullable=True,
    )

    unit_price = Column(
        Numeric(12, 2),
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

    item = relationship(
        "RetailCatalogItem",
        back_populates="service_price_tiers",
    )
