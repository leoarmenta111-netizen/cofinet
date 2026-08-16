import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class PurchaseStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PurchaseCreationSource(str, enum.Enum):
    ADMIN_CASH = "admin_cash"
    ADMIN_BATCH = "admin_batch"
    MERCADOPAGO = "mercadopago"
    SYSTEM = "system"


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by_admin_id = Column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pin_batch_id = Column(
        Integer,
        ForeignKey("pin_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    branch_id = Column(
        Integer,
        ForeignKey("branches.id"),
        nullable=False,
        default=1,
        server_default="1",
        index=True,
    )

    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        Enum(
            PurchaseStatus,
            name="purchase_status",
            values_callable=lambda statuses: [item.value for item in statuses],
        ),
        nullable=False,
        default=PurchaseStatus.PAID,
        index=True,
    )
    creation_source = Column(
        Enum(
            PurchaseCreationSource,
            name="purchase_creation_source",
            values_callable=lambda sources: [item.value for item in sources],
        ),
        nullable=False,
        default=PurchaseCreationSource.SYSTEM,
        server_default=PurchaseCreationSource.SYSTEM.value,
        index=True,
    )
    pin_code = Column(String(6), unique=True, nullable=True, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    branch = relationship("Branch", back_populates="purchases")
    user = relationship("User")
    plan = relationship("Plan")
    created_by_admin = relationship("Admin", foreign_keys=[created_by_admin_id])
    pin_batch = relationship("PinBatch", back_populates="purchases")
