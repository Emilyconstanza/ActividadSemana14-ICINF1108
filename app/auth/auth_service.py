import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth.auth_schemas import LoginDto, RegisterDto
from app.auth.password import hash_password, verify_password
from app.auth.password_reset_token import (
    InvalidResetTokenError,
    create_password_reset_token,
    verify_password_reset_token,
)
from app.shared.database import DbSession
from app.shared.exceptions import conflict
from app.users.users_models import UserModel
from app.users.users_repository import UsersRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AuthService:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.users_repository = UsersRepository(db)

    def register(self, data: RegisterDto) -> UserModel:
        if self.users_repository.find_by_email(data.email) is not None:
            raise conflict(
                {"email": {"message": "El correo electrónico ya está registrado"}}
            )

        user = self.users_repository.add(
            UserModel(
                name=data.name,
                email=data.email,
                passwordHash=hash_password(data.password),
            )
        )
        self.db.commit()

        return user

    def login(self, data: LoginDto) -> UserModel:
        user = self.users_repository.find_by_email(data.email)

        # Mismo mensaje si el correo no existe o la contraseña es incorrecta,
        # para no revelar qué correos están registrados.
        if user is None or not verify_password(data.password, user.passwordHash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos",
            )

        return user

    def request_password_reset(self, email: str) -> str | None:
        email = email.strip().lower()
        user = self.users_repository.find_by_email(email)

        if user is None:
            return None

        token, jti, expires_at = create_password_reset_token(user.id)

        self.users_repository.create_password_reset_token(
            jti=jti,
            user_id=user.id,
            expires_at=expires_at,
        )
        self.db.commit()

        reset_link = f"http://localhost:3000/reset-password?token={token}"

        logger.warning(
            "Correo de recuperación simulado para %s. Enlace: %s",
            email,
            reset_link,
        )

        return reset_link


    def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> None:
        try:
            user_id, jti = verify_password_reset_token(token)
        except InvalidResetTokenError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
            ) from error

        actualizado = (
            self.users_repository.consume_password_reset_token_and_update_password(
                jti=jti,
                user_id=user_id,
                new_password_hash=hash_password(new_password),
                used_at=datetime.now(UTC),
            )
        )

        if not actualizado:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El token expiró, ya fue utilizado o no es válido.",
            )

AuthServiceDep = Annotated[AuthService, Depends()]