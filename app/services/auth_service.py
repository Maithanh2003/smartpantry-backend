from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.db.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    def register(self, email: str, password: str, full_name: str | None = None) -> dict:
        existing_user = self.user_repo.get_by_email(email)
        if existing_user:
            raise ValueError("EMAIL_ALREADY_EXISTS")

        user = self.user_repo.create(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
        )
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
            },
            "tokens": {
                "token_type": "bearer",
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
        }

    def login(self, email: str, password: str) -> dict:
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("INVALID_CREDENTIALS")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
            },
            "tokens": {
                "token_type": "bearer",
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
        }
