import secrets
from datetime import timedelta
from typing import Annotated, Final

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import APIKeyCookie
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.shared.config import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_MAX_AGE_SECONDS,
)
from app.shared.database import DbSession
from app.shared.datetimes import utc_now
from app.users.users_models import UserModel, UserSessionModel

UNAUTHORIZED_MESSAGE: Final[str] = "Debes iniciar sesión para acceder a este recurso"

# Lee la cookie `sid`. Además agrega el botón "Authorize" en /docs.
session_cookie = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)


def start_session(
    db: Session, response: Response, user: UserModel, previous_id: str | None
) -> None:
    # Siempre se crea un id de sesión nuevo para evitar ataques de fijación de
    # sesión. La sesión anterior (si había) y las expiradas se eliminan.
    db.execute(
        delete(UserSessionModel).where(
            (UserSessionModel.id == previous_id)
            | (UserSessionModel.expiresAt <= utc_now())
        )
    )

    session_id = secrets.token_urlsafe(32)
    db.add(
        UserSessionModel(
            id=session_id,
            userId=user.id,
            expiresAt=utc_now() + timedelta(seconds=SESSION_MAX_AGE_SECONDS),
        )
    )
    db.commit()

    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_COOKIE_SECURE,
    )


def destroy_session(db: Session, response: Response, session_id: str | None) -> None:
    if session_id:
        db.execute(delete(UserSessionModel).where(UserSessionModel.id == session_id))
        db.commit()

    response.delete_cookie(SESSION_COOKIE_NAME)


def require_session(
    db: DbSession,
    session_id: Annotated[str | None, Depends(session_cookie)],
) -> UserSessionModel:
    # Deja pasar la petición solo si la cookie apunta a una sesión vigente.
    session = None

    if session_id:
        session = db.scalar(
            select(UserSessionModel).where(
                UserSessionModel.id == session_id,
                UserSessionModel.expiresAt > utc_now(),
            )
        )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=UNAUTHORIZED_MESSAGE
        )

    return session


CurrentSession = Annotated[UserSessionModel, Depends(require_session)]
