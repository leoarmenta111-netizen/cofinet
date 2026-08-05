"""Add administrator RBAC and PIN creation audit fields.

Revision ID: 20260724_0001
Revises: None
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260724_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


admin_role = postgresql.ENUM("super_admin", "pin_operator", name="admin_role")
admin_role_column = postgresql.ENUM(
    "super_admin", "pin_operator", name="admin_role", create_type=False
)
purchase_creation_source = postgresql.ENUM(
    "admin_cash", "mercadopago", "system", name="purchase_creation_source"
)
purchase_creation_source_column = postgresql.ENUM(
    "admin_cash",
    "mercadopago",
    "system",
    name="purchase_creation_source",
    create_type=False,
)


def _column_names(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def _index_names(inspector, table: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table)}


def _foreign_key_names(inspector, table: str) -> set[str]:
    return {key["name"] for key in inspector.get_foreign_keys(table) if key["name"]}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "admins" in tables:
        columns = _column_names(inspector, "admins")
        admin_role.create(bind, checkfirst=True)
        if "role" not in columns:
            op.add_column(
                "admins",
                sa.Column(
                    "role",
                    admin_role_column,
                    nullable=False,
                    server_default="super_admin",
                ),
            )
            op.alter_column("admins", "role", server_default=None)
        if "updated_at" not in columns:
            op.add_column(
                "admins",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
            )
        if "last_login_at" not in columns:
            op.add_column(
                "admins", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)
            )
        if "created_by_admin_id" not in columns:
            op.add_column(
                "admins", sa.Column("created_by_admin_id", sa.Integer(), nullable=True)
            )
            op.create_foreign_key(
                "fk_admins_created_by_admin_id_admins",
                "admins",
                "admins",
                ["created_by_admin_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.execute("UPDATE admins SET role = 'super_admin' WHERE role IS NULL")
        inspector = sa.inspect(bind)
        indexes = _index_names(inspector, "admins")
        if "ix_admins_role" not in indexes:
            op.create_index("ix_admins_role", "admins", ["role"])
        if "ix_admins_created_by_admin_id" not in indexes:
            op.create_index(
                "ix_admins_created_by_admin_id", "admins", ["created_by_admin_id"]
            )

    inspector = sa.inspect(bind)
    if "purchases" in set(inspector.get_table_names()):
        columns = _column_names(inspector, "purchases")
        purchase_creation_source.create(bind, checkfirst=True)
        if "created_by_admin_id" not in columns:
            op.add_column(
                "purchases", sa.Column("created_by_admin_id", sa.Integer(), nullable=True)
            )
            if "admins" in tables:
                op.create_foreign_key(
                    "fk_purchases_created_by_admin_id_admins",
                    "purchases",
                    "admins",
                    ["created_by_admin_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if "creation_source" not in columns:
            op.add_column(
                "purchases",
                sa.Column(
                    "creation_source",
                    purchase_creation_source_column,
                    nullable=False,
                    server_default="system",
                ),
            )
        if "payments" in tables:
            op.execute(
                """
                UPDATE purchases AS purchase
                SET creation_source = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM payments AS payment
                        WHERE payment.purchase_id = purchase.id
                          AND payment.provider = 'mercadopago'
                    ) THEN 'mercadopago'::purchase_creation_source
                    WHEN purchase.user_id IS NULL AND purchase.pin_code IS NOT NULL
                        THEN 'admin_cash'::purchase_creation_source
                    ELSE 'system'::purchase_creation_source
                END
                """
            )
        inspector = sa.inspect(bind)
        indexes = _index_names(inspector, "purchases")
        if "ix_purchases_created_by_admin_id" not in indexes:
            op.create_index(
                "ix_purchases_created_by_admin_id", "purchases", ["created_by_admin_id"]
            )
        if "ix_purchases_creation_source" not in indexes:
            op.create_index(
                "ix_purchases_creation_source", "purchases", ["creation_source"]
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "purchases" in tables:
        columns = _column_names(inspector, "purchases")
        indexes = _index_names(inspector, "purchases")
        foreign_keys = _foreign_key_names(inspector, "purchases")
        if "ix_purchases_creation_source" in indexes:
            op.drop_index("ix_purchases_creation_source", table_name="purchases")
        if "ix_purchases_created_by_admin_id" in indexes:
            op.drop_index("ix_purchases_created_by_admin_id", table_name="purchases")
        if "created_by_admin_id" in columns:
            if "fk_purchases_created_by_admin_id_admins" in foreign_keys:
                op.drop_constraint(
                    "fk_purchases_created_by_admin_id_admins", "purchases", type_="foreignkey"
                )
            op.drop_column("purchases", "created_by_admin_id")
        if "creation_source" in columns:
            op.drop_column("purchases", "creation_source")

    inspector = sa.inspect(bind)
    if "admins" in tables:
        columns = _column_names(inspector, "admins")
        indexes = _index_names(inspector, "admins")
        foreign_keys = _foreign_key_names(inspector, "admins")
        if "ix_admins_created_by_admin_id" in indexes:
            op.drop_index("ix_admins_created_by_admin_id", table_name="admins")
        if "ix_admins_role" in indexes:
            op.drop_index("ix_admins_role", table_name="admins")
        if "created_by_admin_id" in columns:
            if "fk_admins_created_by_admin_id_admins" in foreign_keys:
                op.drop_constraint(
                    "fk_admins_created_by_admin_id_admins", "admins", type_="foreignkey"
                )
            op.drop_column("admins", "created_by_admin_id")
        for column in ("last_login_at", "updated_at", "role"):
            if column in columns:
                op.drop_column("admins", column)

    purchase_creation_source.drop(bind, checkfirst=True)
    admin_role.drop(bind, checkfirst=True)
