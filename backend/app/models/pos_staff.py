from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class PosStaffRole(str, Enum):
    CASHIER = "CASHIER"
    MANAGER = "MANAGER"


class PosStaff(Base):
    __tablename__ = "pos_staff"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    branch_id = Column(
        Integer,
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    display_name = Column(
        String(120),
        nullable=False,
    )

    role = Column(
        String(20),
        nullable=False,
        default=PosStaffRole.CASHIER.value,
        server_default=PosStaffRole.CASHIER.value,
        index=True,
    )

    pin_hash = Column(
        String(255),
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    branch = relationship("Branch")

    __table_args__ = (
        CheckConstraint(
            "role IN ('CASHIER','MANAGER')",
            name="ck_pos_staff_role",
        ),
    )
