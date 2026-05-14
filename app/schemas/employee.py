from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import NameStr

class EmployeeCreate(BaseModel):
    full_name: NameStr
    position: NameStr
    hired_at: Optional[date] = None


class EmployeeResponse(BaseModel):
    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: Optional[date] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)