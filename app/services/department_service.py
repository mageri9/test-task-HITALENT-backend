from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.models.department import Department
from app.models import Employee
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.core.exceptions import ConflictException, NotFoundException

import logging

logger = logging.getLogger(__name__)

def _check_name_unique(
        db: Session,
        name: str,
        parent_id: int | None,
        exclude_id: int | None = None
) -> bool:
    """Check if department name is unique within the same parent.

    For root departments (parent_id=None), NULL != NULL in PostgreSQL,
    so we need explicit check.
    """
    query = db.query(Department).filter(Department.name == name)

    if parent_id is None:
        query = query.filter(Department.parent_id.is_(None))
    else:
        query = query.filter(Department.parent_id == parent_id)

    if exclude_id is not None:
        query = query.filter(Department.id != exclude_id)

    return query.first() is None


def create_department(db: Session, data: DepartmentCreate) -> Department:
    """Create a new department.

    Args:
        db: Database session.
        data: Department creation data (name and optional parent_id).

    Returns:
        Newly created Department instance.

    Raises:
        NotFoundException: If parent_id provided but parent does not exist.
        ConflictException: If department with same name already exists in this parent.
    """
    # Check parent exists if parent_id provided
    if data.parent_id is not None:
        parent = db.query(Department).filter(Department.id == data.parent_id).first()

        if parent is None:
            raise NotFoundException(f"Parent department with id {data.parent_id} not found.")

    # Check name uniqueness within parent
    if not _check_name_unique(db, data.name, data.parent_id):
        raise ConflictException(
            f"Department with name {data.name} already exists in this parent."
        )

    department = Department(
        name=data.name,
        parent_id=data.parent_id,
    )
    logger.info("Creating department '%s' (parent_id=%s)", data.name, data.parent_id)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def _get_descendant_ids(db: Session, department_id: int) -> set[int]:
    """Get IDs of all descendants (children, grandchildren, etc.) of a department.

    Uses iterative approach to avoid recursion limits and N+1 queries.

    Args:
        db: Database session.
        department_id: Root department ID.

    Returns:
        Set of all descendant department IDs (excluding the root itself).
    """
    descendants = set()
    to_process = {department_id}

    while to_process:
        current_ids = to_process
        to_process = set()

        children = (
            db.query(Department.id)
            .filter(Department.parent_id.in_(current_ids))
            .all()
        )
        for (child_id,) in children:
            if child_id not in descendants:
                descendants.add(child_id)
                to_process.add(child_id)

    return descendants


def _build_tree(
        departments: list[Department],
        root_id: int,
        depth: int,
        include_employees: bool,
) -> dict[str, object]:
    """Build a nested tree structure from a flat list of departments.

    Uses plain dicts instead of ORM objects to avoid accidental state changes.
    """
    by_id: dict[int, Department] = {d.id: d for d in departments}
    children_map: dict[int | None, list[int]] = {}

    for d in departments:
        children_map.setdefault(d.parent_id, []).append(d.id)

    def build_node(node_id: int, current_depth: int) -> dict[str, object]:
        node = by_id[node_id]
        result: dict[str, object] = {
            "id": node.id,
            "name": node.name,
            "parent_id": node.parent_id,
            "created_at": node.created_at,
        }

        if include_employees:
            result["employees"] = [
                {
                    "id": e.id,
                    "department_id": e.department_id,
                    "full_name": e.full_name,
                    "position": e.position,
                    "hired_at": e.hired_at,
                    "created_at": e.created_at,
                }
                for e in node.employees
            ]
        else:
            result["employees"] = []

        if current_depth < depth:
            child_ids = children_map.get(node_id, [])
            result["children"] = [
                build_node(child_id, current_depth + 1) for child_id in child_ids
            ]
        else:
            result["children"] = []

        return result

    return build_node(root_id, 1)

def get_department(
        db: Session,
        department_id: int,
        depth: int,
        include_employees: bool = True,
) -> "DepartmentResponse":
    """Get department with its subtree and employees.

    Args:
        db: Database session.
        department_id: Department ID.
        depth: Maximum nesting depth (1-5).
        include_employees: Whether to include employee data.

    Returns:
        Nested dict representing the department tree.

    Raises:
        NotFoundException: If department does not exist.
    """
    depth = min(max(depth, 1), 5)

    query = db.query(Department).filter(Department.id == department_id)
    if include_employees:
        query = query.options(selectinload(Department.employees))

    root = query.first()
    if root is None:
        raise NotFoundException(f"Department with id {department_id} not found")

    if depth > 1:
        descendant_ids = _get_descendant_ids(db, department_id)
        if descendant_ids:
            descendants_query = (
                db.query(Department)
                .filter(Department.id.in_(descendant_ids))
            )
            if include_employees:
                descendants_query = descendants_query.options(
                    selectinload(Department.employees)
                )
            all_descendants: list[Department] = descendants_query.all()
        else:
            all_descendants = []
        departments: list[Department] = [root] + all_descendants
    else:
        departments: list[Department] = [root]

    tree_dict = _build_tree(departments, department_id, depth, include_employees)
    return DepartmentResponse.model_validate(tree_dict)


def update_department(
        db: Session,
        department_id: int,
        data: "DepartmentUpdate",
) -> Department:
    logger.info("Updating department id=%s", department_id)
    department = db.query(Department).filter(Department.id == department_id).first()
    if department is None:
        raise NotFoundException(f"Department with id {department_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle parent change (including setting to None / making root)
    if "parent_id" in update_data:
        new_parent_id = update_data["parent_id"]

        if new_parent_id is not None:
            if new_parent_id == department_id:
                raise ConflictException("Department cannot be its own parent")

            new_parent = db.query(Department).filter(Department.id == new_parent_id).first()
            if new_parent is None:
                raise NotFoundException(f"Parent department with id {new_parent_id} not found")

            descendants = _get_descendant_ids(db, department_id)
            if new_parent_id in descendants:
                logger.warning("Cycle detected: department=%s parent=%s", department_id, new_parent_id)
                raise ConflictException("Cannot move department into its own subtree")

        department.parent_id = new_parent_id

    # Handle name change
    if "name" in update_data:
        new_name = update_data["name"]
        effective_parent_id = department.parent_id
        if not _check_name_unique(db, new_name, effective_parent_id, exclude_id=department_id):
            raise ConflictException(
                f"Department with name '{new_name}' already exists in this parent"
            )
        department.name = new_name

    db.commit()
    db.refresh(department)
    return department

def delete_department_cascade(db: Session, department_id: int) -> None:
    """Delete department and all its descendants and employees (cascade)."""
    department = db.query(Department).filter(Department.id == department_id).first()

    if department is None:
        raise NotFoundException(f"Department with id {department_id} not found.")

    logger.info("Cascade deleting department id=%s", department_id)
    db.delete(department)
    db.commit()

def delete_department_reassign(
        db: Session,
        department_id: int,
        reassign_to_id: int,
) -> None:
    """Delete department, reassign employees and children before removal."""
    logger.info("Reassign-deleting department id=%s to id=%s", department_id, reassign_to_id)
    department = db.query(Department).filter(Department.id == department_id).first()

    if department is None:
        raise NotFoundException(f"Department with id {department_id} not found.")

    reassign_to = db.query(Department).filter(Department.id == reassign_to_id).first()
    if reassign_to is None:
        raise NotFoundException(f"Reassignment to id {reassign_to_id} not found.")

    if reassign_to_id == department_id:
        raise ConflictException("Cannot reassign to the same department being deleted")

    descendants = _get_descendant_ids(db, department_id)
    if reassign_to_id in descendants:
        raise ConflictException("Cannot reassign to a descendant of the department being deleted")

    try:
        db.query(Employee).filter(
            Employee.department_id == department_id
        ).update({"department_id": reassign_to_id})

        db.query(Department).filter(
            Department.parent_id == department_id
        ).update({"parent_id": department.parent_id})

        db.delete(department)

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise