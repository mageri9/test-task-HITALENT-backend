from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.employee import EmployeeResponse, EmployeeCreate
from app.services.employee_service import create_employee


router = APIRouter()

@router.post(
    "/{department_id}/employees/",
    response_model=EmployeeResponse,
    status_code=201,
)


def create(
    department_id: int,
    data: EmployeeCreate,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    """Create an employee in a department."""
    employee = create_employee(db, department_id, data)
    return EmployeeResponse.model_validate(employee)