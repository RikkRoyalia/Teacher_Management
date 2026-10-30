from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


class InputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


def _blank_email_as_none(value: object) -> object:
    return None if isinstance(value, str) and not value.strip() else value


OptionalEmail = Annotated[EmailStr | None, BeforeValidator(_blank_email_as_none)]


class LoginInput(InputModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(InputModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class UserCreate(InputModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=256)
    role: Literal["admin", "hr", "manager"]


class UserUpdate(InputModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    role: Literal["admin", "hr", "manager"] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_changes(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        for field in ("full_name", "role", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class DepartmentCreate(InputModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    parent_id: int | None = Field(default=None, gt=0)


class DepartmentUpdate(InputModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    parent_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_changes_and_values(self) -> "DepartmentUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        for field in ("code", "name"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    parent_id: int | None
    is_active: bool


class TeacherCreate(InputModel):
    employee_code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=160)
    department_id: int = Field(gt=0)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=40)
    email: OptionalEmail = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)
    academic_degree: str | None = Field(default=None, max_length=80)
    academic_title: str | None = Field(default=None, max_length=80)
    employment_status: Literal["active", "paused", "ended"] = "active"

    @model_validator(mode="after")
    def validate_birth_date(self) -> "TeacherCreate":
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return self


class TeacherUpdate(InputModel):
    employee_code: str | None = Field(default=None, min_length=1, max_length=40)
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    department_id: int | None = Field(default=None, gt=0)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=40)
    email: OptionalEmail = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)
    academic_degree: str | None = Field(default=None, max_length=80)
    academic_title: str | None = Field(default=None, max_length=80)
    employment_status: Literal["active", "paused", "ended"] | None = None

    @model_validator(mode="after")
    def require_changes_and_values(self) -> "TeacherUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        for field in ("employee_code", "full_name", "department_id", "employment_status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return self


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    date_of_birth: date | None
    gender: str | None
    email: str | None
    phone: str | None
    address: str | None
    department_id: int
    academic_degree: str | None
    academic_title: str | None
    employment_status: str


class QualificationCreate(InputModel):
    qualification_type: Literal["degree", "certificate", "research", "other"]
    title: str = Field(min_length=1, max_length=200)
    specialty: str | None = Field(default=None, max_length=160)
    institution: str | None = Field(default=None, max_length=200)
    issued_on: date | None = None
    issued_year: int | None = Field(default=None, ge=1900, le=2200)


class QualificationUpdate(InputModel):
    qualification_type: Literal["degree", "certificate", "research", "other"] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    specialty: str | None = Field(default=None, max_length=160)
    institution: str | None = Field(default=None, max_length=200)
    issued_on: date | None = None
    issued_year: int | None = Field(default=None, ge=1900, le=2200)

    @model_validator(mode="after")
    def require_changes(self) -> "QualificationUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        for field in ("qualification_type", "title"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class QualificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    qualification_type: str
    title: str
    specialty: str | None
    institution: str | None
    issued_on: date | None
    issued_year: int | None


class ContractCreate(InputModel):
    contract_code: str = Field(min_length=1, max_length=80)
    contract_type: str = Field(min_length=1, max_length=120)
    signed_on: date | None = None
    starts_on: date
    ends_on: date | None = None
    status: Literal["active", "terminated"] = "active"

    @model_validator(mode="after")
    def validate_dates(self) -> "ContractCreate":
        if self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Contract end date cannot be before its start date.")
        return self


class ContractUpdate(InputModel):
    contract_code: str | None = Field(default=None, min_length=1, max_length=80)
    contract_type: str | None = Field(default=None, min_length=1, max_length=120)
    signed_on: date | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    status: Literal["active", "terminated"] | None = None

    @model_validator(mode="after")
    def require_changes(self) -> "ContractUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        for field in ("contract_code", "contract_type", "starts_on", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    contract_code: str
    contract_type: str
    signed_on: date | None
    starts_on: date
    ends_on: date | None
    status: str
    display_status: str


class WorkHistoryCreate(InputModel):
    department_id: int = Field(gt=0)
    position_title: str | None = Field(default=None, max_length=120)
    starts_on: date
    ends_on: date | None = None
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self) -> "WorkHistoryCreate":
        if self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Work period end date cannot be before its start date.")
        return self


class WorkHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    department_id: int
    position_title: str | None
    starts_on: date
    ends_on: date | None
    reason: str | None


class ChecklistItemCreate(InputModel):
    code: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_-]+$")
    label: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    classification: Literal["required", "conditional", "optional"] = "conditional"
    applicability: str = Field(default="", max_length=500)
    is_sensitive: bool = False


class ChecklistItemUpdate(InputModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    classification: Literal["required", "conditional", "optional"] | None = None
    applicability: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    is_sensitive: bool | None = None

    @model_validator(mode="after")
    def require_changes(self) -> "ChecklistItemUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        for field in ("label", "category", "classification", "applicability", "is_active", "is_sensitive"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    category: str
    classification: str
    applicability: str
    is_active: bool
    is_sensitive: bool


class TeacherChecklistRequirementUpdate(InputModel):
    status: Literal["required", "optional", "not_applicable", "review"]


class TeacherChecklistRequirementRead(BaseModel):
    item_id: int
    code: str
    label: str
    category: str
    classification: str
    applicability: str
    is_sensitive: bool
    status: str
    reviewed_at: datetime | None


class ChangeRequestCreate(InputModel):
    change_type: str = Field(min_length=1, max_length=100)
    current_value: dict[str, object] = Field(default_factory=dict)
    proposed_value: dict[str, object]
    reason: str = Field(min_length=1, max_length=1000)
    effective_on: date | None = None

    @model_validator(mode="after")
    def require_proposal(self) -> "ChangeRequestCreate":
        if not self.proposed_value:
            raise ValueError("Proposed value cannot be empty.")
        return self


class ChangeRequestUpdate(InputModel):
    proposed_value: dict[str, object]
    reason: str = Field(min_length=1, max_length=1000)
    effective_on: date | None = None


class ChangeDecision(InputModel):
    action: Literal["approve", "reject", "request_info"]
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_resolution_reason(self) -> "ChangeDecision":
        if self.action in {"reject", "request_info"} and not (self.reason or "").strip():
            raise ValueError("A reason is required for this decision.")
        return self


class ChangeRequestRead(BaseModel):
    id: int
    teacher_id: int
    requester_id: int
    change_type: str
    current_value: dict[str, object]
    proposed_value: dict[str, object]
    reason: str
    effective_on: date | None
    status: str
    processor_id: int | None
    processed_at: datetime | None
    resolution_reason: str | None
    created_at: datetime


class EvidenceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    checklist_item_id: int | None
    qualification_id: int | None
    contract_id: int | None
    original_name: str
    content_type: str
    size_bytes: int
    uploaded_by: int
    created_at: datetime


class ContractAlert(BaseModel):
    contract_id: int
    teacher_id: int
    teacher_name: str
    contract_code: str
    ends_on: date
    days_remaining: int
    status: str
