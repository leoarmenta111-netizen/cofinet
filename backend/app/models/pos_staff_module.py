from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.database.session import Base


class PosStaffModule(Base):
    __tablename__ = "pos_staff_modules"

    staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    module_code = Column(
        String(20),
        primary_key=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "module_code IN ('CAFE','PAPELERIA')",
            name="ck_pos_staff_modules_module_code",
        ),
    )
