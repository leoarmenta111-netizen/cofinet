import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class PinBatchStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class PinBatch(Base):
    __tablename__ = "pin_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_uuid = Column(String(36), unique=True, nullable=False, index=True)
    request_uuid = Column(String(36), unique=True, nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    requested_quantity = Column(Integer, nullable=False)
    created_quantity = Column(Integer, nullable=False, default=0, server_default="0")
    failed_quantity = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(
        Enum(
            PinBatchStatus,
            name="pin_batch_status",
            values_callable=lambda values: [item.value for item in values],
        ),
        nullable=False,
        default=PinBatchStatus.PROCESSING,
        server_default=PinBatchStatus.PROCESSING.value,
        index=True,
    )
    created_by_admin_id = Column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    plan = relationship("Plan")
    created_by_admin = relationship("Admin", foreign_keys=[created_by_admin_id])
    purchases = relationship("Purchase", back_populates="pin_batch")
    failures = relationship(
        "PinBatchFailure",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="PinBatchFailure.id",
    )

    __table_args__ = (
        CheckConstraint(
            "requested_quantity >= 1 AND requested_quantity <= 100",
            name="ck_pin_batches_requested_quantity",
        ),
        CheckConstraint(
            "created_quantity >= 0 AND failed_quantity >= 0",
            name="ck_pin_batches_result_counts",
        ),
    )


class PinBatchFailure(Base):
    __tablename__ = "pin_batch_failures"

    id = Column(Integer, primary_key=True, index=True)
    pin_batch_id = Column(
        Integer,
        ForeignKey("pin_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pin_code = Column(String(6), nullable=True)
    error_code = Column(String(40), nullable=False)
    error_message = Column(String(240), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    batch = relationship("PinBatch", back_populates="failures")


class InternalHotspotCredential(Base):
    __tablename__ = "internal_hotspot_credentials"

    id = Column(Integer, primary_key=True, index=True)
    request_uuid = Column(String(36), unique=True, nullable=False, index=True)
    label = Column(String(120), unique=True, nullable=False, index=True)
    pin_code = Column(String(6), unique=True, nullable=False, index=True)
    creation_source = Column(
        String(32), nullable=False, default="internal_device", server_default="internal_device"
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="true", index=True)
    created_by_admin_id = Column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    created_by_admin = relationship("Admin", foreign_keys=[created_by_admin_id])

    __table_args__ = (
        CheckConstraint(
            "creation_source = 'internal_device'",
            name="ck_internal_hotspot_credentials_source",
        ),
    )
