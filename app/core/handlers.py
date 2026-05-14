from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException, NotFoundException, ConflictException


async def not_found_exception_handler(
        request: Request,
        exc: NotFoundException,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc) if str(exc) else "Not Found"},
    )

async def conflict_exception_handler(
        request: Request,
        exc: ConflictException,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc) if str(exc) else "Conflict"},
    )

async def app_exception_handler(
        request: Request,
        exc: AppException,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) if str(exc) else "Internal Error"},
    )