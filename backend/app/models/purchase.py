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


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
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
    pin_code = Column(String(6), unique=True, nullable=True, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    plan = relationship("Plan")
