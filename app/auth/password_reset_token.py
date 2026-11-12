from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from app.shared.config import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    PASSWORD_RESET_EXPIRE_MINUTES,
)


class InvalidResetTokenError(ValueError):
    """Error cuando un token de recuperación no es válido."""


def create_password_reset_token(
    user_id: UUID,
) -> tuple[str, str, datetime]:
    """Genera un JWT de recuperación de contraseña de un solo uso."""

    ahora = datetime.now(UTC)
    fecha_expiracion = ahora + timedelta(
        minutes=PASSWORD_RESET_EXPIRE_MINUTES
    )

    identificador_unico = uuid4().hex

    payload = {
        "sub": str(user_id),
        "jti": identificador_unico,
        "purpose": "password_reset",
        "iat": ahora,
        "exp": fecha_expiracion,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return token, identificador_unico, fecha_expiracion



def verify_password_reset_token(
    token: str,
) -> tuple[UUID, str]:
    """Valida el JWT y devuelve el ID del usuario y el JTI."""

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={
                "require": ["exp", "sub", "iat", "jti"],
            },
        )
    except jwt.InvalidTokenError as error:
        raise InvalidResetTokenError(
            "El token es inválido, expiró o su firma no es válida."
        ) from error

    if payload.get("purpose") != "password_reset":
        raise InvalidResetTokenError(
            "El token no corresponde a una recuperación de contraseña."
        )

    try:
        user_id = UUID(payload["sub"])
        identificador_unico = payload["jti"]

        if not isinstance(identificador_unico, str) or not identificador_unico:
            raise InvalidResetTokenError(
                "El identificador del token no es válido."
            )

        return user_id, identificador_unico

    except (ValueError, KeyError, TypeError) as error:
        raise InvalidResetTokenError(
            "Los datos del token de recuperación no son válidos."
        ) from error

