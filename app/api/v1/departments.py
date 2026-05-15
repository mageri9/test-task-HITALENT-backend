from typing import Literal

from fastapi import Depends, APIRouter, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse

from app.services.department_service import (
    create_department,
    update_department,
    get_department,
    delete_department_cascade,
    delete_department_reassign,
)

router = APIRouter()


@router.post("/", response_model=DepartmentResponse, status_code=201)
def create(
        data: DepartmentCreate,
        db: Session = Depends(get_db),
) -> DepartmentResponse:
    """Create a new department."""
    department = create_department(db, data)
    return DepartmentResponse.model_validate(department)


@router.get("/{department_id}", response_model=DepartmentResponse)
def get(
        department_id: int,
        depth: int = Query(1, ge=1, le=5),
        include_employees: bool = Query(True),
        db: Session = Depends(get_db),
) -> DepartmentResponse:
    """Get department with subtree and employees."""
    return get_department(
        db=db,
        department_id=department_id,
        depth=depth,
        include_employees=include_employees,
    )

@router.patch("/{department_id}", response_model=DepartmentResponse)
def update(
        department_id: int,
        data: DepartmentUpdate,
        db: Session = Depends(get_db),
) -> DepartmentResponse:
    """Update department name or parent."""
    department = update_department(db, department_id, data)
    return DepartmentResponse.model_validate(department)


@router.delete("/{department_id}")
def delete(
        department_id: int,
        mode: Literal["cascade", "reassign"] = Query(...),
        reassign_to: int | None = Query(None, alias="reassign_to_department_id"),
        db: Session = Depends(get_db),
):
    """Delete department."""
    if mode == "cascade":
        delete_department_cascade(db, department_id)
    else:
        if reassign_to is None:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=422,
                detail="reassign_to_department_id is required when mode=reassign",
            )
        delete_department_reassign(db, department_id, reassign_to)
    return Response(status_code=204)