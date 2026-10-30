from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'hr', 'manager')",
            name="ck_user_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class LoginSession(Base):
    __tablename__ = "login_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    teachers: Mapped[list["Teacher"]] = relationship(back_populates="department")
    parent: Mapped["Department | None"] = relationship(
        remote_side="Department.id", back_populates="children"
    )
    children: Mapped[list["Department"]] = relationship(back_populates="parent")


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    department: Mapped[Department] = relationship(back_populates="teachers")
    qualifications: Mapped[list["Qualification"]] = relationship(back_populates="teacher")
    contracts: Mapped[list["EmploymentContract"]] = relationship(back_populates="teacher")
    work_history: Mapped[list["WorkHistory"]] = relationship(back_populates="teacher")
    documents: Mapped[list["EvidenceDocument"]] = relationship(back_populates="teacher")


class Qualification(Base):
    __tablename__ = "qualifications"
    __table_args__ = (
        CheckConstraint(
            "qualification_type IN ('degree', 'certificate', 'research', 'other')",
            name="ck_qualification_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    qualification_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(160))
    institution: Mapped[str | None] = mapped_column(String(200))
    issued_on: Mapped[date | None] = mapped_column(Date)
    issued_year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    teacher: Mapped[Teacher] = relationship(back_populates="qualifications")
    documents: Mapped[list["EvidenceDocument"]] = relationship(back_populates="qualification")


class EmploymentContract(Base):
    __tablename__ = "employment_contracts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'terminated')",
            name="ck_contract_status",
        ),
        CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_contract_date_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    contract_code: Mapped[str] = mapped_column(String(80), index=True)
    contract_type: Mapped[str] = mapped_column(String(120))
    signed_on: Mapped[date | None] = mapped_column(Date)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    teacher: Mapped[Teacher] = relationship(back_populates="contracts")
    documents: Mapped[list["EvidenceDocument"]] = relationship(back_populates="contract")


class WorkHistory(Base):
    __tablename__ = "work_history"
    __table_args__ = (
        CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_work_history_date_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    position_title: Mapped[str | None] = mapped_column(String(120))
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(500))
    change_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("change_requests.id", ondelete="RESTRICT"), nullable=True
    )

    teacher: Mapped[Teacher] = relationship(back_populates="work_history")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    classification: Mapped[str] = mapped_column(String(20), default="conditional", nullable=False)
    applicability: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TeacherChecklistRequirement(Base):
    __tablename__ = "teacher_checklist_requirements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('required', 'optional', 'not_applicable', 'review')",
            name="ck_teacher_checklist_requirement_status",
        ),
        UniqueConstraint(
            "teacher_id", "checklist_item_id",
            name="uq_teacher_checklist_requirement",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    checklist_item_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_items.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="review", nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EvidenceDocument(Base):
    __tablename__ = "evidence_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    checklist_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("checklist_items.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    qualification_id: Mapped[int | None] = mapped_column(
        ForeignKey("qualifications.id", ondelete="RESTRICT"), nullable=True
    )
    contract_id: Mapped[int | None] = mapped_column(
        ForeignKey("employment_contracts.id", ondelete="RESTRICT"), nullable=True
    )
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    teacher: Mapped[Teacher] = relationship(back_populates="documents")
    qualification: Mapped[Qualification | None] = relationship(back_populates="documents")
    contract: Mapped[EmploymentContract | None] = relationship(back_populates="documents")


class ChangeRequest(Base):
    __tablename__ = "change_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'needs_info', 'approved', 'rejected', 'processing')",
            name="ck_change_request_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    change_type: Mapped[str] = mapped_column(String(100))
    current_value: Mapped[str] = mapped_column(Text)
    proposed_value: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(1000))
    effective_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    processor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_reason: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class ChangeRequestEvent(Base):
    __tablename__ = "change_request_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    change_request_id: Mapped[int] = mapped_column(
        ForeignKey("change_requests.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    event_type: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), index=True)
    outcome: Mapped[str] = mapped_column(String(30))
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
