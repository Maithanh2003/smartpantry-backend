from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Users


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> Users | None:
        stmt = select(Users).where(Users.email == email.lower(), Users.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, email: str, password_hash: str, full_name: str | None = None) -> Users:
        user = Users(
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
