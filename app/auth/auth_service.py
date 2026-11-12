from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth.auth_schemas import LoginDto, RegisterDto
from app.auth.password import hash_password, verify_password
from app.shared.database import DbSession
from app.shared.exceptions import conflict
from app.users.users_models import UserModel
from app.users.users_repository import UsersRepository


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


AuthServiceDep = Annotated[AuthService, Depends()]
