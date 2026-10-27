from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, DATABASE_URL, create_database
from app.models import Department, Teacher
from app.schemas import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    TeacherCreate,
    TeacherRead,
    TeacherUpdate,
)

STATIC_DIR = Path(__file__).parent / "static"


def create_app(database_url: str = DATABASE_URL) -> FastAPI:
    engine, session_factory = create_database(database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(bind=engine)
        yield
        engine.dispose()

    application = FastAPI(
        title="Teacher Management API",
        description="API nền tảng quản lý khoa và hồ sơ giảng viên.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.session_factory = session_factory
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/", include_in_schema=False)
    def frontend() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    def get_db(request: Request) -> Generator[Session, None, None]:
        with request.app.state.session_factory() as session:
            yield session

    DbSession = Annotated[Session, Depends(get_db)]

    @application.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @application.post(
        "/departments",
        response_model=DepartmentRead,
        status_code=status.HTTP_201_CREATED,
        tags=["departments"],
    )
    def create_department(payload: DepartmentCreate, db: DbSession) -> Department:
        department = Department(**payload.model_dump())
        db.add(department)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Department code already exists.",
            )
        db.refresh(department)
        return department

    @application.get(
        "/departments",
        response_model=list[DepartmentRead],
        tags=["departments"],
    )
    def list_departments(
        db: DbSession,
        include_inactive: bool = False,
    ) -> list[Department]:
        statement = select(Department).order_by(Department.name, Department.id)
        if not include_inactive:
            statement = statement.where(Department.is_active.is_(True))
        return list(db.scalars(statement))

    @application.patch(
        "/departments/{department_id}",
        response_model=DepartmentRead,
        tags=["departments"],
    )
    def update_department(
        department_id: int, payload: DepartmentUpdate, db: DbSession
    ) -> Department:
        department = db.get(Department, department_id)
        if department is None:
            raise HTTPException(status_code=404, detail="Department not found.")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(department, field, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Department code already exists.",
            )
        db.refresh(department)
        return department

    @application.post(
        "/teachers",
        response_model=TeacherRead,
        status_code=status.HTTP_201_CREATED,
        tags=["teachers"],
    )
    def create_teacher(payload: TeacherCreate, db: DbSession) -> Teacher:
        if db.get(Department, payload.department_id) is None:
            raise HTTPException(status_code=404, detail="Department not found.")

        teacher = Teacher(**payload.model_dump())
        db.add(teacher)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Teacher employee code already exists.",
            )
        db.refresh(teacher)
        return teacher

    @application.get(
        "/teachers",
        response_model=list[TeacherRead],
        tags=["teachers"],
    )
    def list_teachers(
        db: DbSession,
        q: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
        department_id: int | None = Query(default=None, gt=0),
        academic_degree: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
        employment_status: str | None = Query(
            default=None, pattern="^(active|paused|ended)$"
        ),
    ) -> list[Teacher]:
        statement = select(Teacher)
        if q:
            search_term = f"%{q}%"
            statement = statement.where(
                or_(
                    Teacher.employee_code.ilike(search_term),
                    Teacher.full_name.ilike(search_term),
                )
            )
        if department_id is not None:
            statement = statement.where(Teacher.department_id == department_id)
        if academic_degree:
            statement = statement.where(Teacher.academic_degree == academic_degree)
        if employment_status:
            statement = statement.where(Teacher.employment_status == employment_status)
        statement = statement.order_by(Teacher.full_name, Teacher.id)
        return list(db.scalars(statement))

    @application.get(
        "/teachers/{teacher_id}",
        response_model=TeacherRead,
        tags=["teachers"],
    )
    def get_teacher(teacher_id: int, db: DbSession) -> Teacher:
        teacher = db.get(Teacher, teacher_id)
        if teacher is None:
            raise HTTPException(status_code=404, detail="Teacher not found.")
        return teacher

    @application.patch(
        "/teachers/{teacher_id}",
        response_model=TeacherRead,
        tags=["teachers"],
    )
    def update_teacher(
        teacher_id: int, payload: TeacherUpdate, db: DbSession
    ) -> Teacher:
        teacher = db.get(Teacher, teacher_id)
        if teacher is None:
            raise HTTPException(status_code=404, detail="Teacher not found.")

        changes = payload.model_dump(exclude_unset=True)
        if "department_id" in changes and db.get(Department, changes["department_id"]) is None:
            raise HTTPException(status_code=404, detail="Department not found.")
        for field, value in changes.items():
            setattr(teacher, field, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Teacher employee code already exists.",
            )
        db.refresh(teacher)
        return teacher

    return application


app = create_app()
