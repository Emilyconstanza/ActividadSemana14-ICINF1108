from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.students.students_models import StudentModel


class StudentsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_all(self) -> list[StudentModel]:
        query = select(StudentModel).order_by(StudentModel.createdAt.desc())
        return list(self.db.scalars(query))

    def find_by_id(self, student_id: UUID) -> StudentModel | None:
        return self.db.get(StudentModel, student_id)

    def find_by_email(self, email: str) -> StudentModel | None:
        query = select(StudentModel).where(StudentModel.email == email)
        return self.db.scalar(query)

    def find_by_username(self, username: str) -> StudentModel | None:
        query = select(StudentModel).where(StudentModel.username == username)
        return self.db.scalar(query)

    def add(self, student: StudentModel) -> StudentModel:
        self.db.add(student)
        # `flush` envía el INSERT (sin confirmar la transacción) para que el
        # estudiante exista antes de insertar sus mascotas.
        self.db.flush()
        return student

    def delete(self, student: StudentModel) -> None:
        self.db.delete(student)
        self.db.flush()
