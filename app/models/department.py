from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Self-referencing
    parent: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="children", remote_side=[id]
    )
    children: Mapped[List["Department"]] = relationship(
        "Department", back_populates="parent"
    )

    # Employees
    employees: Mapped[List["Employee"]] = relationship(
        "Employee", back_populates="department"
    )