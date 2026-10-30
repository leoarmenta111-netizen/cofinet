from sqlalchemy.orm import Session

from app.models.pos_audit import PosAuditEvent


class PosAuditService:
    @staticmethod
    def record(
        db: Session,
        *,
        event_type: str,
        branch_id: int,
        terminal_id: str,
        actor_staff_id: int | None,
        authorizer_staff_id: int | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        metadata: dict | None = None,
    ) -> PosAuditEvent:
        event = PosAuditEvent(
            event_type=event_type,
            branch_id=branch_id,
            terminal_id=terminal_id,
            actor_staff_id=actor_staff_id,
            authorizer_staff_id=authorizer_staff_id,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata,
        )

        db.add(event)
        db.flush()

        return event
