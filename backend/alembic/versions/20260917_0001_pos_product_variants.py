"""Add POS product price variants.

Revision ID: 20260917_0001
Revises: 20260915_0001
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260917_0001"
down_revision = "20260915_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_variant_groups",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_pos_variant_groups",
        ),
    )

    op.create_table(
        "pos_variants",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "variant_group_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["variant_group_id"],
            ["pos_variant_groups.id"],
            name="fk_pos_variants_variant_group_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_pos_variants",
        ),
        sa.UniqueConstraint(
            "variant_group_id",
            "name",
            name="uq_pos_variants_group_name",
        ),
    )

    op.create_table(
        "pos_product_variants",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "price",
            sa.Numeric(10, 2),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "price >= 0",
            name="ck_pos_product_variants_price_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["pos_products.id"],
            name="fk_pos_product_variants_product_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["pos_variants.id"],
            name="fk_pos_product_variants_variant_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_pos_product_variants",
        ),
        sa.UniqueConstraint(
            "product_id",
            "variant_id",
            name="uq_pos_product_variants_product_variant",
        ),
    )

    op.create_table(
        "pos_branch_product_variants",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "product_variant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "price_override",
            sa.Numeric(10, 2),
            nullable=True,
        ),
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "price_override IS NULL OR price_override >= 0",
            name=(
                "ck_pos_branch_product_variants_"
                "price_override_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_pos_branch_product_variants_branch_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_variant_id"],
            ["pos_product_variants.id"],
            name=(
                "fk_pos_branch_product_variants_"
                "product_variant_id"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_pos_branch_product_variants",
        ),
        sa.UniqueConstraint(
            "branch_id",
            "product_variant_id",
            name=(
                "uq_pos_branch_product_variants_"
                "branch_product_variant"
            ),
        ),
    )

    with op.batch_alter_table(
        "pos_products",
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "variant_group_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_pos_products_variant_group_id",
            "pos_variant_groups",
            ["variant_group_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table(
        "pos_order_items",
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "product_variant_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "variant_name",
                sa.String(length=160),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_pos_order_items_product_variant_id",
            "pos_product_variants",
            ["product_variant_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "pos_order_items",
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_pos_order_items_product_variant_id",
            type_="foreignkey",
        )
        batch_op.drop_column(
            "variant_name",
        )
        batch_op.drop_column(
            "product_variant_id",
        )

    with op.batch_alter_table(
        "pos_products",
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_pos_products_variant_group_id",
            type_="foreignkey",
        )
        batch_op.drop_column(
            "variant_group_id",
        )

    op.drop_table(
        "pos_branch_product_variants",
    )

    op.drop_table(
        "pos_product_variants",
    )

    op.drop_table(
        "pos_variants",
    )

    op.drop_table(
        "pos_variant_groups",
    )
