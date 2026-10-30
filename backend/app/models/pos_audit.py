from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.sql import func

from app.database.session import Base


class PosAuditEvent(Base):
    __tablename__ = "pos_audit_events"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    event_type = Column(
        String(40),
        nullable=False,
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

    terminal_id = Column(
        String(80),
        nullable=False,
        index=True,
    )

    actor_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    authorizer_staff_id = Column(
        Integer,
        ForeignKey(
            "pos_staff.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    target_type = Column(
        String(80),
        nullable=True,
    )

    target_id = Column(
        String(120),
        nullable=True,
    )

    metadata_json = Column(
        "metadata",
        JSON,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "event_type IN "
            "('SHIFT_OPENED','SHIFT_CLOSED','CASH_MOVEMENT')",
            name="ck_pos_audit_events_event_type",
        ),
    )
