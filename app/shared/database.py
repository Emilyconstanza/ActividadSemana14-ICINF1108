from collections.abc import Iterator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import DateTime, MetaData, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.shared.config import DATABASE_URL
from app.shared.datetimes import utc_now

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# `expire_on_commit=False`: después del commit los objetos conservan sus valores
# y se pueden devolver en la respuesta sin volver a consultar la base de datos.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# Nombres predecibles para índices y restricciones (los usan las migraciones).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    # Los atributos van en camelCase (como en la respuesta JSON) y las columnas
    # en snake_case, igual que el @map de Prisma en la rama de NestJS.
    createdAt: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


def get_db() -> Iterator[Session]:
    # Una sesión de base de datos por petición. Si algo falla antes del
    # commit, al cerrarla se hace rollback de lo que no se confirmó.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
