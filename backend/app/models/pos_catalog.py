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
from app.models.branch import Branch  # noqa: F401


class PosCategory(Base):
    __tablename__ = "pos_categories"
    __table_args__ = (
        UniqueConstraint(
            "slug",
            name="uq_pos_categories_slug",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String(120),
        nullable=False,
    )

    slug = Column(
        String(80),
        nullable=False,
    )

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
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

    products = relationship(
        "PosProduct",
        back_populates="category",
    )


class PosVariantGroup(Base):
    __tablename__ = "pos_variant_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    variants = relationship("PosVariant", back_populates="group")
    products = relationship("PosProduct", back_populates="variant_group")


class PosVariant(Base):
    __tablename__ = "pos_variants"
    __table_args__ = (
        UniqueConstraint("variant_group_id", "name", name="uq_pos_variants_group_name"),
    )

    id = Column(Integer, primary_key=True)
    variant_group_id = Column(Integer, ForeignKey("pos_variant_groups.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(160), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    group = relationship("PosVariantGroup", back_populates="variants")
    product_variants = relationship("PosProductVariant", back_populates="variant")


class PosProductVariant(Base):
    __tablename__ = "pos_product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "variant_id", name="uq_pos_product_variants_product_variant"),
        CheckConstraint("price >= 0", name="ck_pos_product_variants_price_nonnegative"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("pos_products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("pos_variants.id", ondelete="RESTRICT"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    product = relationship("PosProduct", back_populates="product_variants")
    variant = relationship("PosVariant", back_populates="product_variants")
    branch_overrides = relationship("PosBranchProductVariant", back_populates="product_variant")


class PosBranchProductVariant(Base):
    __tablename__ = "pos_branch_product_variants"
    __table_args__ = (
        UniqueConstraint("branch_id", "product_variant_id", name="uq_pos_branch_product_variants_branch_product_variant"),
        CheckConstraint("price_override IS NULL OR price_override >= 0", name="ck_pos_branch_product_variants_price_override_nonnegative"),
    )

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    product_variant_id = Column(Integer, ForeignKey("pos_product_variants.id", ondelete="CASCADE"), nullable=False)
    price_override = Column(Numeric(10, 2), nullable=True)
    is_available = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    branch = relationship("Branch")
    product_variant = relationship("PosProductVariant", back_populates="branch_overrides")


class PosProduct(Base):
    __tablename__ = "pos_products"
    __table_args__ = (
        UniqueConstraint(
            "sku",
            name="uq_pos_products_sku",
        ),
        CheckConstraint(
            "base_price >= 0",
            name="ck_pos_products_base_price_nonnegative",
        ),
        CheckConstraint(
            "preparation_station IN ('KITCHEN','BAR','NONE')",
            name="ck_pos_products_preparation_station",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    category_id = Column(
        Integer,
        ForeignKey(
            "pos_categories.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    variant_group_id = Column(
        Integer,
        ForeignKey(
            "pos_variant_groups.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    name = Column(
        String(160),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    sku = Column(
        String(80),
        nullable=True,
    )

    base_price = Column(
        Numeric(10, 2),
        nullable=False,
    )

    image_url = Column(
        String(500),
        nullable=True,
    )

    preparation_station = Column(
        String(16),
        nullable=False,
        default="NONE",
        server_default="NONE",
        index=True,
    )

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
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

    category = relationship(
        "PosCategory",
        back_populates="products",
    )

    variant_group = relationship(
        "PosVariantGroup",
        back_populates="products",
    )

    product_variants = relationship(
        "PosProductVariant",
        back_populates="product",
    )

    branch_products = relationship(
        "PosBranchProduct",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    modifier_links = relationship(
        "PosProductModifierGroup",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class PosBranchProduct(Base):
    __tablename__ = "pos_branch_products"
    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "product_id",
            name="uq_pos_branch_products_branch_product",
        ),
        CheckConstraint(
            "price IS NULL OR price >= 0",
            name="ck_pos_branch_products_price_nonnegative",
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

    product_id = Column(
        Integer,
        ForeignKey(
            "pos_products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # NULL = use PosProduct.base_price.
    # This lets a branch override the price without duplicating the product.
    price = Column(
        Numeric(10, 2),
        nullable=True,
    )

    is_available = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
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

    product = relationship(
        "PosProduct",
        back_populates="branch_products",
    )


class PosModifierGroup(Base):
    __tablename__ = "pos_modifier_groups"
    __table_args__ = (
        CheckConstraint(
            "min_select >= 0",
            name="ck_pos_modifier_groups_min_select",
        ),
        CheckConstraint(
            "max_select >= 1",
            name="ck_pos_modifier_groups_max_select",
        ),
        CheckConstraint(
            "min_select <= max_select",
            name="ck_pos_modifier_groups_selection_range",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String(120),
        nullable=False,
    )

    required = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    min_select = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    max_select = Column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
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

    options = relationship(
        "PosModifierOption",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    product_links = relationship(
        "PosProductModifierGroup",
        back_populates="modifier_group",
        cascade="all, delete-orphan",
    )


class PosModifierOption(Base):
    __tablename__ = "pos_modifier_options"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "name",
            name="uq_pos_modifier_options_group_name",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    group_id = Column(
        Integer,
        ForeignKey(
            "pos_modifier_groups.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name = Column(
        String(120),
        nullable=False,
    )

    price_delta = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    image_url = Column(
        String(500),
        nullable=True,
    )

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
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

    group = relationship(
        "PosModifierGroup",
        back_populates="options",
    )


class PosProductModifierGroup(Base):
    __tablename__ = "pos_product_modifier_groups"

    product_id = Column(
        Integer,
        ForeignKey(
            "pos_products.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    modifier_group_id = Column(
        Integer,
        ForeignKey(
            "pos_modifier_groups.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
        index=True,
    )

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    product = relationship(
        "PosProduct",
        back_populates="modifier_links",
    )

    modifier_group = relationship(
        "PosModifierGroup",
        back_populates="product_links",
    )
