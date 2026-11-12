
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.users.users_models import (
    PasswordResetTokenModel,
    UserModel,
    UserSessionModel,
)


class UsersRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_by_id(self, user_id: UUID) -> UserModel | None:
        return self.db.get(UserModel, user_id)

    def find_by_email(self, email: str) -> UserModel | None:
        return self.db.scalar(select(UserModel).where(UserModel.email == email))

    def add(self, user: UserModel) -> UserModel:
        self.db.add(user)
        self.db.flush()
        return user

    # Crea el registro del token de recuperación.
    def create_password_reset_token(
        self,
        jti: str,
        user_id: UUID,
        expires_at: datetime,
    ) -> PasswordResetTokenModel:
        token = PasswordResetTokenModel(
            jti=jti,
            userId=user_id,
            expiresAt=expires_at,
            usedAt=None,
        )

        self.db.add(token)
        self.db.flush()

        return token

    # Busca un token de recuperación mediante su identificador único.
    def get_password_reset_token(
        self,
        jti: str,
    ) -> PasswordResetTokenModel | None:
        return self.db.scalar(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.jti == jti
            )
        )

    # Consume el token, actualiza la contraseña y elimina las sesiones
    # activas dentro de una única transacción.
    def consume_password_reset_token_and_update_password(
        self,
        jti: str,
        user_id: UUID,
        new_password_hash: str,
        used_at: datetime,
    ) -> bool:
        try:
            resultado = self.db.execute(
                update(PasswordResetTokenModel)
                .where(
                    PasswordResetTokenModel.jti == jti,
                    PasswordResetTokenModel.userId == user_id,
                    PasswordResetTokenModel.usedAt.is_(None),
                    PasswordResetTokenModel.expiresAt > used_at,
                )
                .values(usedAt=used_at)
                .execution_options(synchronize_session=False)
            )

            # Si el token no existe, expiró o ya fue utilizado,
            # se cancela toda la operación.
            if resultado.rowcount != 1:
                self.db.rollback()
                return False

            resultado_usuario = self.db.execute(
                update(UserModel)
                .where(UserModel.id == user_id)
                .values(passwordHash=new_password_hash)
                .execution_options(synchronize_session=False)
            )

            if resultado_usuario.rowcount != 1:
                self.db.rollback()
                return False

            # Revoca todas las sesiones activas del usuario.
            self.db.execute(
                delete(UserSessionModel).where(
                    UserSessionModel.userId == user_id
                )
            )

            # Un único commit para confirmar todas las operaciones.
            self.db.commit()

            return True

        except Exception:
            self.db.rollback()
            raise
