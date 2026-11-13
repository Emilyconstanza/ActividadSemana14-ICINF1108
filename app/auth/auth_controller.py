from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.auth_schemas import (
    ForgotPasswordDto,
    LoginDto,
    MessageResponseDto,
    RegisterDto,
    ResetPasswordDto,
    User,
)
from app.auth.auth_service import AuthServiceDep
from app.auth.session import (
    UNAUTHORIZED_MESSAGE,
    CurrentSession,
    destroy_session,
    session_cookie,
    start_session,
)
from app.shared.database import DbSession
from app.users.users_repository import UsersRepository

router = APIRouter(prefix="/api/auth", tags=["Auth"])

SessionCookie = Annotated[str | None, Depends(session_cookie)]


# Crea la cuenta e inicia sesión de inmediato.
@router.post("/register", status_code=201)
def register(
    body: RegisterDto,
    response: Response,
    service: AuthServiceDep,
    db: DbSession,
    session_id: SessionCookie,
) -> User:
    user = service.register(body)
    start_session(db, response, user, session_id)
    return User.model_validate(user)


@router.post("/login")
def login(
    body: LoginDto,
    response: Response,
    service: AuthServiceDep,
    db: DbSession,
    session_id: SessionCookie,
) -> User:
    user = service.login(body)
    start_session(db, response, user, session_id)
    return User.model_validate(user)


@router.post("/logout")
def logout(response: Response, db: DbSession, session_id: SessionCookie) -> None:
    destroy_session(db, response, session_id)


@router.get("/me")
def me(session: CurrentSession, response: Response, db: DbSession) -> User:
    user = UsersRepository(db).find_by_id(session.userId)

    # La sesión apunta a un usuario que ya no existe.
    if user is None:
        destroy_session(db, response, session.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=UNAUTHORIZED_MESSAGE
        )

    return User.model_validate(user)


@router.post(
    "/forgot-password",
    response_model=MessageResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Solicitar recuperación de contraseña",
    description="Genera un token JWT de un solo uso y envía instrucciones si el correo existe.",
    responses={
        200: {"description": "Solicitud procesada correctamente"},
        400: {"description": "Datos de entrada inválidos"},
    },
)
def forgot_password(
    body: ForgotPasswordDto,
    service: AuthServiceDep,
) -> MessageResponseDto:
    service.request_password_reset(body.email)
    return MessageResponseDto(
        message="Si el correo está registrado, recibirás un enlace de recuperación válido por 15 minutos."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Restablecer contraseña con token JWT",
    description="Valida el token JWT de un solo uso, actualiza la contraseña e invalida sesiones previas.",
    responses={
        200: {"description": "Contraseña actualizada exitosamente"},
        400: {"description": "Token inválido, expirado o ya utilizado"},
        401: {"description": "Token no autorizado"},
    },
)
def reset_password(
    body: ResetPasswordDto,
    service: AuthServiceDep,
) -> MessageResponseDto:
    service.reset_password(body.token, body.newPassword)
    return MessageResponseDto(message="Contraseña actualizada exitosamente.")