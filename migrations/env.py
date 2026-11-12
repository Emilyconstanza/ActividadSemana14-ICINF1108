from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# Se importan todos los modelos para que Alembic conozca sus tablas
# (lo necesita `alembic revision --autogenerate`).
import app.pets.pets_models  # noqa: F401
import app.students.students_models  # noqa: F401
import app.users.users_models  # noqa: F401
from app.shared.config import DATABASE_URL
from app.shared.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # Genera el SQL sin conectarse a la base de datos (`alembic upgrade --sql`).
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
