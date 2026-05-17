from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate

import logging


logger = logging.getLogger(__name__)

def create_employee(
        db: Session,
        department_id: int,
        data: EmployeeCreate
) -> Employee:
    """Create an employee in a department."""
    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )
    if department is None:
        raise NotFoundException(
            f"Department with id {department_id} not found."
        )

    employee = Employee(
        department_id=department_id,
        full_name=data.full_name,
        position=data.position,
        hired_at=data.hired_at,
    )
    logger.info("Creating employee '%s' in department id=%s", data.full_name, department_id)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee