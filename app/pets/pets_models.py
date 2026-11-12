from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base, TimestampMixin


class PetModel(TimestampMixin, Base):
    __tablename__ = "pets"
    # Un estudiante no puede tener dos mascotas con el mismo nombre.
    __table_args__ = (
        UniqueConstraint("student_id", "name", name="uq_pets_student_id_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # Al eliminar un estudiante, Postgres elimina sus mascotas (ON DELETE CASCADE).
    studentId: Mapped[UUID] = mapped_column(
        "student_id", ForeignKey("students.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(50))
    species: Mapped[str] = mapped_column(String(50))
    age: Mapped[int | None]
