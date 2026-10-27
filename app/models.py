from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    teachers: Mapped[list["Teacher"]] = relationship(back_populates="department")


class Teacher(Base):
    __tablename__ = "teachers"
    __table_args__ = (
        CheckConstraint(
            "employment_status IN ('active', 'paused', 'ended')",
            name="ck_teacher_employment_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    academic_degree: Mapped[str | None] = mapped_column(String(80), nullable=True)
    academic_title: Mapped[str | None] = mapped_column(String(80), nullable=True)
    employment_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )

    department: Mapped[Department] = relationship(back_populates="teachers")
