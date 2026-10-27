from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class DepartmentCreate(InputModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class DepartmentUpdate(InputModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_changes(self) -> "DepartmentUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        if "code" in self.model_fields_set and self.code is None:
            raise ValueError("Department code cannot be null.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Department name cannot be null.")
        return self


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    is_active: bool


class TeacherCreate(InputModel):
    employee_code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=160)
    department_id: int = Field(gt=0)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)
    academic_degree: str | None = Field(default=None, max_length=80)
    academic_title: str | None = Field(default=None, max_length=80)
    employment_status: Literal["active", "paused", "ended"] = "active"


class TeacherUpdate(InputModel):
    employee_code: str | None = Field(default=None, min_length=1, max_length=40)
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    department_id: int | None = Field(default=None, gt=0)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254)
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
