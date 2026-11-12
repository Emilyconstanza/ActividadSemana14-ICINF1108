from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.pets.pets_models import PetModel
from app.pets.pets_repository import PetsRepository
from app.shared.database import DbSession, parse_uuid
from app.shared.exceptions import conflict
from app.shared.types import FieldErrors
from app.students.students_models import StudentModel
from app.students.students_repository import StudentsRepository
from app.students.students_schemas import (
    CreateStudentDto,
    Student,
    StudentList,
    UpdateStudentDto,
)


class StudentsService:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.repository = StudentsRepository(db)
        self.pets_repository = PetsRepository(db)

    def find_all(self) -> StudentList:
        students = [Student.model_validate(s) for s in self.repository.find_all()]

        return StudentList(total=len(students), items=students)

    def find_by_id(self, student_id: str) -> Student:
        return Student.model_validate(self.get_or_404(student_id))

    def create(self, data: CreateStudentDto) -> Student:
        # El estudiante y sus mascotas se insertan en una sola transacción: nada
        # queda guardado hasta el `commit`. Si una mascota falla, se lanza la
        # excepción antes del commit y la sesión hace rollback al cerrarse.
        self.assert_no_conflicts(data)

        student = self.repository.add(
            StudentModel(
                name=data.name,
                username=data.username,
                email=data.email,
                age=data.age,
            )
        )

        for pet_data in data.pets:
            existing = self.pets_repository.find_by_student_and_name(
                student.id, pet_data.name
            )

            if existing is not None:
                raise conflict(
                    {"name": {"message": "Ya tienes una mascota con ese nombre"}}
                )

            self.pets_repository.add(
                PetModel(
                    studentId=student.id,
                    name=pet_data.name,
                    species=pet_data.species,
                    age=pet_data.age,
                )
            )

        self.db.commit()

        return Student.model_validate(student)

    def update(self, student_id: str, data: UpdateStudentDto) -> Student:
        student = self.get_or_404(student_id)
        self.assert_no_conflicts(data, except_id=student.id)

        # Los campos que no vienen en el body (None) no se modifican.
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(student, field, value)

        self.db.commit()

        return Student.model_validate(student)

    def delete(self, student_id: str) -> Student:
        student = self.get_or_404(student_id)
        deleted = Student.model_validate(student)

        # Las mascotas se eliminan en cascada (ON DELETE CASCADE).
        self.repository.delete(student)
        self.db.commit()

        return deleted

    def get_or_404(self, student_id: str) -> StudentModel:
        # Un id que no es UUID no puede existir: se responde 404 igual.
        parsed = parse_uuid(student_id)
        student = self.repository.find_by_id(parsed) if parsed else None

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estudiante no encontrado",
            )

        return student

    def assert_no_conflicts(
        self,
        data: CreateStudentDto | UpdateStudentDto,
        except_id: UUID | None = None,
    ) -> None:
        errors: FieldErrors = {}

        if data.email:
            existing = self.repository.find_by_email(data.email)
            if existing and existing.id != except_id:
                errors["email"] = {"message": "El correo electrónico ya está en uso"}

        if data.username:
            existing = self.repository.find_by_username(data.username)
            if existing and existing.id != except_id:
                errors["username"] = {"message": "El nombre de usuario ya está en uso"}

        if errors:
            raise conflict(errors)


# FastAPI crea un servicio por petición, con su propia sesión de base de datos.
StudentsServiceDep = Annotated[StudentsService, Depends()]
