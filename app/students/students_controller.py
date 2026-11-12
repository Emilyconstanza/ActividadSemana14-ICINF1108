from fastapi import APIRouter, Depends

from app.auth.session import require_session
from app.students.students_schemas import (
    CreateStudentDto,
    Student,
    StudentList,
    UpdateStudentDto,
)
from app.students.students_service import StudentsServiceDep

# Todas las rutas de este router exigen una sesión iniciada.
router = APIRouter(
    prefix="/api/students",
    tags=["Students"],
    dependencies=[Depends(require_session)],
)


@router.get("")
def find_all(service: StudentsServiceDep) -> StudentList:
    return service.find_all()


@router.get("/{studentId}")
def find_by_id(studentId: str, service: StudentsServiceDep) -> Student:
    return service.find_by_id(studentId)


@router.post("", status_code=201)
def create(body: CreateStudentDto, service: StudentsServiceDep) -> Student:
    return service.create(body)


@router.patch("/{studentId}")
def update(
    studentId: str, body: UpdateStudentDto, service: StudentsServiceDep
) -> Student:
    return service.update(studentId, body)


@router.delete("/{studentId}")
def delete(studentId: str, service: StudentsServiceDep) -> Student:
    return service.delete(studentId)
