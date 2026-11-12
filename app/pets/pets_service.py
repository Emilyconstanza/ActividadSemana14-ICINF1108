from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.pets.pets_models import PetModel
from app.pets.pets_repository import PetsRepository
from app.pets.pets_schemas import CreatePetDto, Pet, PetList, UpdatePetDto
from app.shared.database import DbSession, parse_uuid
from app.shared.exceptions import conflict
from app.students.students_service import StudentsService


class PetsService:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.repository = PetsRepository(db)
        self.students_service = StudentsService(db)

    def find_all_for_student(self, student_id: str) -> PetList:
        student = self.students_service.get_or_404(student_id)

        pets = [
            Pet.model_validate(pet)
            for pet in self.repository.find_all_by_student(student.id)
        ]

        return PetList(total=len(pets), items=pets)

    def create(self, student_id: str, data: CreatePetDto) -> Pet:
        student = self.students_service.get_or_404(student_id)
        self.assert_no_conflicts(student.id, data)

        pet = self.repository.add(
            PetModel(
                studentId=student.id,
                name=data.name,
                species=data.species,
                age=data.age,
            )
        )
        self.db.commit()

        return Pet.model_validate(pet)

    def update(self, student_id: str, pet_id: str, data: UpdatePetDto) -> Pet:
        pet = self.find_owned(student_id, pet_id)
        self.assert_no_conflicts(pet.studentId, data, except_id=pet.id)

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(pet, field, value)

        self.db.commit()

        return Pet.model_validate(pet)

    def delete(self, student_id: str, pet_id: str) -> Pet:
        pet = self.find_owned(student_id, pet_id)
        deleted = Pet.model_validate(pet)

        self.repository.delete(pet)
        self.db.commit()

        return deleted

    def find_owned(self, student_id: str, pet_id: str) -> PetModel:
        student = self.students_service.get_or_404(student_id)

        parsed = parse_uuid(pet_id)
        pet = self.repository.find_by_id(parsed) if parsed else None

        if pet is None or pet.studentId != student.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mascota no encontrada",
            )

        return pet

    def assert_no_conflicts(
        self,
        student_id: UUID,
        data: CreatePetDto | UpdatePetDto,
        except_id: UUID | None = None,
    ) -> None:
        if not data.name:
            return

        existing = self.repository.find_by_student_and_name(student_id, data.name)

        if existing and existing.id != except_id:
            raise conflict(
                {"name": {"message": "Ya tienes una mascota con ese nombre"}}
            )


PetsServiceDep = Annotated[PetsService, Depends()]
