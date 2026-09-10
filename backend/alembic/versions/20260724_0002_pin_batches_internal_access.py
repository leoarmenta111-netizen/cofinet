"""Add auditable PIN batches and permanent internal Hotspot credentials.

Revision ID: 20260724_0002
Revises: 20260724_0001
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260724_0002"
down_revision: str | None = "20260724_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


pin_batch_status = postgresql.ENUM(
    "processing", "completed", "partial", "failed", name="pin_batch_status"
)
pin_batch_status_column = postgresql.ENUM(
    "processing",
    "completed",
    "partial",
    "failed",
    name="pin_batch_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # Purchase creation_source remains strongly typed. Existing values and rows
    # are untouched; this only adds the new auditable batch source.
    op.execute("ALTER TYPE purchase_creation_source ADD VALUE IF NOT EXISTS 'admin_batch'")
    pin_batch_status.create(bind, checkfirst=True)

    if "pin_batches" not in tables:
        op.create_table(
            "pin_batches",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("batch_uuid", sa.String(length=36), nullable=False),
            sa.Column("request_uuid", sa.String(length=36), nullable=False),
            sa.Column("plan_id", sa.Integer(), nullable=False),
            sa.Column("requested_quantity", sa.Integer(), nullable=False),
            sa.Column("created_quantity", sa.Integer(), server_default="0", nullable=False),
            sa.Column("failed_quantity", sa.Integer(), server_default="0", nullable=False),
            sa.Column(
                "status",
                pin_batch_status_column,
                server_default="processing",
                nullable=False,
            ),
            sa.Column("created_by_admin_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "requested_quantity >= 1 AND requested_quantity <= 100",
                name="ck_pin_batches_requested_quantity",
            ),
            sa.CheckConstraint(
                "created_quantity >= 0 AND failed_quantity >= 0",
                name="ck_pin_batches_result_counts",
            ),
            sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
            sa.ForeignKeyConstraint(
                ["created_by_admin_id"], ["admins.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("batch_uuid"),
            sa.UniqueConstraint("request_uuid"),
        )
        op.create_index("ix_pin_batches_id", "pin_batches", ["id"])
        op.create_index("ix_pin_batches_batch_uuid", "pin_batches", ["batch_uuid"])
        op.create_index("ix_pin_batches_request_uuid", "pin_batches", ["request_uuid"])
        op.create_index("ix_pin_batches_plan_id", "pin_batches", ["plan_id"])
        op.create_index("ix_pin_batches_status", "pin_batches", ["status"])
        op.create_index(
            "ix_pin_batches_created_by_admin_id", "pin_batches", ["created_by_admin_id"]
        )

    if "pin_batch_failures" not in tables:
        op.create_table(
            "pin_batch_failures",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pin_batch_id", sa.Integer(), nullable=False),
            sa.Column("pin_code", sa.String(length=6), nullable=True),
            sa.Column("error_code", sa.String(length=40), nullable=False),
            sa.Column("error_message", sa.String(length=240), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.ForeignKeyConstraint(
                ["pin_batch_id"], ["pin_batches.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_pin_batch_failures_id", "pin_batch_failures", ["id"])
        op.create_index(
            "ix_pin_batch_failures_pin_batch_id", "pin_batch_failures", ["pin_batch_id"]
        )

    if "internal_hotspot_credentials" not in tables:
        op.create_table(
            "internal_hotspot_credentials",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("request_uuid", sa.String(length=36), nullable=False),
            sa.Column("label", sa.String(length=120), nullable=False),
            sa.Column("pin_code", sa.String(length=6), nullable=False),
            sa.Column(
                "creation_source",
                sa.String(length=32),
                server_default="internal_device",
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_by_admin_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "creation_source = 'internal_device'",
                name="ck_internal_hotspot_credentials_source",
            ),
            sa.ForeignKeyConstraint(
                ["created_by_admin_id"], ["admins.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("label"),
            sa.UniqueConstraint("pin_code"),
            sa.UniqueConstraint("request_uuid"),
        )
        op.create_index(
            "ix_internal_hotspot_credentials_id", "internal_hotspot_credentials", ["id"]
        )
        op.create_index(
            "ix_internal_hotspot_credentials_request_uuid",
            "internal_hotspot_credentials",
            ["request_uuid"],
        )
        op.create_index(
            "ix_internal_hotspot_credentials_label",
            "internal_hotspot_credentials",
            ["label"],
        )
        op.create_index(
            "ix_internal_hotspot_credentials_pin_code",
            "internal_hotspot_credentials",
            ["pin_code"],
        )
        op.create_index(
            "ix_internal_hotspot_credentials_is_active",
            "internal_hotspot_credentials",
            ["is_active"],
        )
        op.create_index(
            "ix_internal_hotspot_credentials_created_by_admin_id",
            "internal_hotspot_credentials",
            ["created_by_admin_id"],
        )

    inspector = sa.inspect(bind)
    purchase_columns = {column["name"] for column in inspector.get_columns("purchases")}
    if "pin_batch_id" not in purchase_columns:
        op.add_column("purchases", sa.Column("pin_batch_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_purchases_pin_batch_id_pin_batches",
            "purchases",
            "pin_batches",
            ["pin_batch_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_purchases_pin_batch_id", "purchases", ["pin_batch_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "purchases" in tables:
        columns = {column["name"] for column in inspector.get_columns("purchases")}
        indexes = {index["name"] for index in inspector.get_indexes("purchases")}
        foreign_keys = {
            item["name"] for item in inspector.get_foreign_keys("purchases") if item["name"]
        }
        if "ix_purchases_pin_batch_id" in indexes:
            op.drop_index("ix_purchases_pin_batch_id", table_name="purchases")
        if "pin_batch_id" in columns:
            if "fk_purchases_pin_batch_id_pin_batches" in foreign_keys:
                op.drop_constraint(
                    "fk_purchases_pin_batch_id_pin_batches", "purchases", type_="foreignkey"
                )
            op.drop_column("purchases", "pin_batch_id")

    for table in ("pin_batch_failures", "internal_hotspot_credentials", "pin_batches"):
        if table in tables:
            op.drop_table(table)
    pin_batch_status.drop(bind, checkfirst=True)

    # PostgreSQL cannot directly remove an enum value. Convert through text,
    # remap batch rows to the legacy admin_cash source, and recreate the type.
    op.execute(
        "UPDATE purchases SET creation_source = 'admin_cash' "
        "WHERE creation_source::text = 'admin_batch'"
    )
    op.execute("ALTER TABLE purchases ALTER COLUMN creation_source DROP DEFAULT")
    op.execute(
        "ALTER TABLE purchases ALTER COLUMN creation_source TYPE VARCHAR(32) "
        "USING creation_source::text"
    )
    op.execute("DROP TYPE purchase_creation_source")
    op.execute(
        "CREATE TYPE purchase_creation_source AS ENUM "
        "('admin_cash', 'mercadopago', 'system')"
    )
    op.execute(
        "ALTER TABLE purchases ALTER COLUMN creation_source TYPE purchase_creation_source "
        "USING creation_source::purchase_creation_source"
    )
    op.execute(
        "ALTER TABLE purchases ALTER COLUMN creation_source SET DEFAULT "
        "'system'::purchase_creation_source"
    )
