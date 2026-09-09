"""Add POS receipt settings foundation.

Revision ID: 20260908_0001
Revises: 20260902_0002
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260908_0001"
down_revision = "20260902_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pos_business_receipt_settings",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "business_name",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "logo_ref",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "phone",
            sa.String(length=40),
            nullable=True,
        ),
        sa.Column(
            "web_social",
            sa.String(length=240),
            nullable=True,
        ),
        sa.Column(
            "footer_message",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "tax_mode",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "tax_rate",
            sa.Numeric(precision=8, scale=4),
            nullable=False,
        ),
        sa.Column(
            "receipt_width_mm",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "folio_prefix",
            sa.String(length=8),
            nullable=False,
        ),
        sa.Column(
            "auto_print_customer",
            sa.Boolean(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "id = 1",
            name="ck_pos_business_receipt_settings_singleton",
        ),
        sa.CheckConstraint(
            "tax_mode IN ('NONE','INCLUDED','ADDED')",
            name="ck_pos_business_receipt_settings_tax_mode",
        ),
        sa.CheckConstraint(
            "tax_rate >= 0",
            name="ck_pos_business_receipt_settings_tax_rate",
        ),
        sa.CheckConstraint(
            "receipt_width_mm = 80",
            name="ck_pos_business_receipt_settings_width",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pos_branch_receipt_settings",
        sa.Column(
            "branch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=160),
            nullable=True,
        ),
        sa.Column(
            "address",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "phone",
            sa.String(length=40),
            nullable=True,
        ),
        sa.Column(
            "web_social",
            sa.String(length=240),
            nullable=True,
        ),
        sa.Column(
            "footer_message",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "tax_mode",
            sa.String(length=16),
            nullable=True,
        ),
        sa.Column(
            "tax_rate",
            sa.Numeric(precision=8, scale=4),
            nullable=True,
        ),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "folio_prefix",
            sa.String(length=8),
            nullable=True,
        ),
        sa.Column(
            "auto_print_customer",
            sa.Boolean(),
            nullable=True,
        ),
        sa.CheckConstraint(
            "tax_mode IS NULL OR "
            "tax_mode IN ('NONE','INCLUDED','ADDED')",
            name="ck_pos_branch_receipt_settings_tax_mode",
        ),
        sa.CheckConstraint(
            "tax_rate IS NULL OR tax_rate >= 0",
            name="ck_pos_branch_receipt_settings_tax_rate",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name=(
                "fk_pos_branch_receipt_settings_"
                "branch_id_branches"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("branch_id"),
    )

    business_table = sa.table(
        "pos_business_receipt_settings",
        sa.column("id", sa.Integer()),
        sa.column("business_name", sa.String()),
        sa.column("currency", sa.String()),
        sa.column("tax_mode", sa.String()),
        sa.column("tax_rate", sa.Numeric(8, 4)),
        sa.column("receipt_width_mm", sa.Integer()),
        sa.column("timezone", sa.String()),
        sa.column("folio_prefix", sa.String()),
        sa.column("auto_print_customer", sa.Boolean()),
    )

    op.bulk_insert(
        business_table,
        [
            {
                "id": 1,
                "business_name": "CofiCenter",
                "currency": "MXN",
                "tax_mode": "NONE",
                "tax_rate": 0.0000,
                "receipt_width_mm": 80,
                "timezone": "America/Bahia_Banderas",
                "folio_prefix": "CF",
                "auto_print_customer": False,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("pos_branch_receipt_settings")
    op.drop_table("pos_business_receipt_settings")
