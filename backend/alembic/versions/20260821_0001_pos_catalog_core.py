"""POS catalogue core

Revision ID: 20260821_0001
Revises: 20260816_0001
Create Date: 2026-08-21

"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0001"
down_revision = "20260816_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # Categories
    # ---------------------------------------------------------

    op.create_table(
        "pos_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "slug",
            name="uq_pos_categories_slug",
        ),
    )

    op.create_index(
        op.f("ix_pos_categories_id"),
        "pos_categories",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_categories_is_active"),
        "pos_categories",
        ["is_active"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Products
    # ---------------------------------------------------------

    op.create_table(
        "pos_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sku", sa.String(length=80), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "base_price >= 0",
            name="ck_pos_products_base_price_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["pos_categories.id"],
            name="fk_pos_products_category_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sku",
            name="uq_pos_products_sku",
        ),
    )

    op.create_index(
        op.f("ix_pos_products_id"),
        "pos_products",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_products_category_id"),
        "pos_products",
        ["category_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_products_is_active"),
        "pos_products",
        ["is_active"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Products per branch
    # ---------------------------------------------------------

    op.create_table(
        "pos_branch_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "is_available",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "price IS NULL OR price >= 0",
            name="ck_pos_branch_products_price_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_branch_products_branch_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["pos_products.id"],
            name="fk_pos_branch_products_product_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "branch_id",
            "product_id",
            name="uq_pos_branch_products_branch_product",
        ),
    )

    op.create_index(
        op.f("ix_pos_branch_products_id"),
        "pos_branch_products",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_branch_products_branch_id"),
        "pos_branch_products",
        ["branch_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_branch_products_product_id"),
        "pos_branch_products",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_branch_products_is_available"),
        "pos_branch_products",
        ["is_available"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Modifier groups
    # ---------------------------------------------------------

    op.create_table(
        "pos_modifier_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "min_select",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "max_select",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "min_select >= 0",
            name="ck_pos_modifier_groups_min_select",
        ),
        sa.CheckConstraint(
            "max_select >= 1",
            name="ck_pos_modifier_groups_max_select",
        ),
        sa.CheckConstraint(
            "min_select <= max_select",
            name="ck_pos_modifier_groups_selection_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_pos_modifier_groups_id"),
        "pos_modifier_groups",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_modifier_groups_is_active"),
        "pos_modifier_groups",
        ["is_active"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Modifier options
    # ---------------------------------------------------------

    op.create_table(
        "pos_modifier_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "price_delta",
            sa.Numeric(10, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["pos_modifier_groups.id"],
            name="fk_pos_modifier_options_group_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id",
            "name",
            name="uq_pos_modifier_options_group_name",
        ),
    )

    op.create_index(
        op.f("ix_pos_modifier_options_id"),
        "pos_modifier_options",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_modifier_options_group_id"),
        "pos_modifier_options",
        ["group_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_pos_modifier_options_is_active"),
        "pos_modifier_options",
        ["is_active"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Product <-> modifier groups
    # ---------------------------------------------------------

    op.create_table(
        "pos_product_modifier_groups",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("modifier_group_id", sa.Integer(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["pos_products.id"],
            name="fk_pos_product_modifier_groups_product_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["modifier_group_id"],
            ["pos_modifier_groups.id"],
            name="fk_pos_product_modifier_groups_modifier_group_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "product_id",
            "modifier_group_id",
        ),
    )

    op.create_index(
        op.f("ix_pos_product_modifier_groups_modifier_group_id"),
        "pos_product_modifier_groups",
        ["modifier_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pos_product_modifier_groups_modifier_group_id"),
        table_name="pos_product_modifier_groups",
    )
    op.drop_table("pos_product_modifier_groups")

    op.drop_index(
        op.f("ix_pos_modifier_options_is_active"),
        table_name="pos_modifier_options",
    )
    op.drop_index(
        op.f("ix_pos_modifier_options_group_id"),
        table_name="pos_modifier_options",
    )
    op.drop_index(
        op.f("ix_pos_modifier_options_id"),
        table_name="pos_modifier_options",
    )
    op.drop_table("pos_modifier_options")

    op.drop_index(
        op.f("ix_pos_modifier_groups_is_active"),
        table_name="pos_modifier_groups",
    )
    op.drop_index(
        op.f("ix_pos_modifier_groups_id"),
        table_name="pos_modifier_groups",
    )
    op.drop_table("pos_modifier_groups")

    op.drop_index(
        op.f("ix_pos_branch_products_is_available"),
        table_name="pos_branch_products",
    )
    op.drop_index(
        op.f("ix_pos_branch_products_product_id"),
        table_name="pos_branch_products",
    )
    op.drop_index(
        op.f("ix_pos_branch_products_branch_id"),
        table_name="pos_branch_products",
    )
    op.drop_index(
        op.f("ix_pos_branch_products_id"),
        table_name="pos_branch_products",
    )
    op.drop_table("pos_branch_products")

    op.drop_index(
        op.f("ix_pos_products_is_active"),
        table_name="pos_products",
    )
    op.drop_index(
        op.f("ix_pos_products_category_id"),
        table_name="pos_products",
    )
    op.drop_index(
        op.f("ix_pos_products_id"),
        table_name="pos_products",
    )
    op.drop_table("pos_products")

    op.drop_index(
        op.f("ix_pos_categories_is_active"),
        table_name="pos_categories",
    )
    op.drop_index(
        op.f("ix_pos_categories_id"),
        table_name="pos_categories",
    )
    op.drop_table("pos_categories")
