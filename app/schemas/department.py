from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import NameStr
from app.schemas.employee import EmployeeResponse


class DepartmentCreate(BaseModel):
    name: NameStr
    parent_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[NameStr] = None
    parent_id: Optional[int] = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    created_at: datetime
    employees: list[EmployeeResponse] = Field(default_factory=list)
    children: list[DepartmentResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)