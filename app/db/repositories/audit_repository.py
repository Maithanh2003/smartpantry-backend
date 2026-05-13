from sqlalchemy.orm import Session

from app.db.models import AuditLogs


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def write(
        self,
        *,
        action: str,
        actor_user_id: int | None,
        entity_type: str,
        entity_id: str,
        before_json: dict | None = None,
        after_json: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.db.add(
            AuditLogs(
                actor_user_id=actor_user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                before_json=before_json,
                after_json=after_json,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        self.db.commit()
