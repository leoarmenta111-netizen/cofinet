import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class MembershipStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CANCELLED = "cancelled"


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    plan_code = Column(String(50), nullable=False)
    plan_name = Column(String(120), nullable=False)
    monthly_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(MembershipStatus, name="membership_status", values_callable=lambda values: [value.value for value in values]), nullable=False, default=MembershipStatus.PENDING, index=True)
    provider_preapproval_id = Column(String(255), unique=True, nullable=True, index=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user = relationship("User")
