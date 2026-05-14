class AppException(Exception):
    """Base exception for application domain errors."""
    pass


class NotFoundException(AppException):
    """Resource Not Found."""
    pass

class ConflictException(AppException):
    """Business rule conflict (cycle, duplicate, etc.)."""
    pass