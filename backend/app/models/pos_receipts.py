from sqlalchemy import CheckConstraint
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.database.session import Base


class PosBusinessReceiptSettings(Base):
    __tablename__ = "pos_business_receipt_settings"

    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="ck_pos_business_receipt_settings_singleton",
        ),
        CheckConstraint(
            "tax_mode IN ('NONE','INCLUDED','ADDED')",
            name="ck_pos_business_receipt_settings_tax_mode",
        ),
        CheckConstraint(
            "tax_rate >= 0",
            name="ck_pos_business_receipt_settings_tax_rate",
        ),
        CheckConstraint(
            "receipt_width_mm = 80",
            name="ck_pos_business_receipt_settings_width",
        ),
    )


    id = Column(Integer, primary_key=True)
    business_name = Column(String(160), nullable=False)
    logo_ref = Column(String(500), nullable=True)
    phone = Column(String(40), nullable=True)
    web_social = Column(String(240), nullable=True)
    footer_message = Column(String(500), nullable=True)
    currency = Column(String(3), nullable=False, default="MXN")
    tax_mode = Column(String(16), nullable=False, default="NONE")
    tax_rate = Column(Numeric(8, 4), nullable=False, default=0)
    receipt_width_mm = Column(Integer, nullable=False, default=80)
    timezone = Column(String(64), nullable=False)
    folio_prefix = Column(String(8), nullable=False)
    auto_print_customer = Column(Boolean, nullable=False, default=False)



class PosBranchReceiptSettings(Base):
    __tablename__ = "pos_branch_receipt_settings"

    __table_args__ = (
        CheckConstraint(
            "tax_mode IS NULL OR tax_mode IN ('NONE','INCLUDED','ADDED')",
            name="ck_pos_branch_receipt_settings_tax_mode",
        ),
        CheckConstraint(
            "tax_rate IS NULL OR tax_rate >= 0",
            name="ck_pos_branch_receipt_settings_tax_rate",
        ),
    )


    branch_id = Column(
        Integer,
        ForeignKey("branches.id", ondelete="CASCADE"),
        primary_key=True,
    )

    display_name = Column(String(160), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(40), nullable=True)
    web_social = Column(String(240), nullable=True)
    footer_message = Column(String(500), nullable=True)
    tax_mode = Column(String(16), nullable=True)
    tax_rate = Column(Numeric(8, 4), nullable=True)
    timezone = Column(String(64), nullable=True)
    folio_prefix = Column(String(8), nullable=True)
    auto_print_customer = Column(Boolean, nullable=True)



class PosReceiptSnapshot(Base):
    __tablename__ = "pos_receipt_snapshots"
    __table_args__ = (
        CheckConstraint(
            "schema_version = 1",
            name="ck_pos_receipt_snapshots_schema_version_v1",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
    )

    order_id = Column(
        Integer,
        ForeignKey(
            "pos_orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    schema_version = Column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    snapshot_json = Column(
        JSON,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
