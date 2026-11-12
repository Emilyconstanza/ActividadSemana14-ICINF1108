from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.pets.pets_models import PetModel


class PetsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_all_by_student(self, student_id: UUID) -> list[PetModel]:
        query = (
            select(PetModel)
            .where(PetModel.studentId == student_id)
            .order_by(PetModel.createdAt.desc())
        )
        return list(self.db.scalars(query))

    def find_by_id(self, pet_id: UUID) -> PetModel | None:
        return self.db.get(PetModel, pet_id)

    def find_by_student_and_name(self, student_id: UUID, name: str) -> PetModel | None:
        query = select(PetModel).where(
            PetModel.studentId == student_id, PetModel.name == name
        )
        return self.db.scalar(query)

    def add(self, pet: PetModel) -> PetModel:
        self.db.add(pet)
        self.db.flush()
        return pet

    def delete(self, pet: PetModel) -> None:
        self.db.delete(pet)
        self.db.flush()
