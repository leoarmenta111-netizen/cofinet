from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String(120),
        nullable=False,
    )

    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
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
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    purchases = relationship(
        "Purchase",
        back_populates="branch",
    )

    pin_batches = relationship(
        "PinBatch",
        back_populates="branch",
    )

    internal_hotspot_credentials = relationship(
        "InternalHotspotCredential",
        back_populates="branch",
    )
