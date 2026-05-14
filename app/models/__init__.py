from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

from app.models.department import Department  # noqa: E402, F401
from app.models.employee import Employee  # noqa: E402, F401