from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException, NotFoundException, ConflictException

import logging

logger = logging.getLogger(__name__)


async def not_found_exception_handler(
        request: Request,
        exc: NotFoundException,
) -> JSONResponse:
    logger.error("%s: %s", type(exc).__name__, str(exc))
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc) if str(exc) else "Not Found"},
    )

async def conflict_exception_handler(
        request: Request,
        exc: ConflictException,
) -> JSONResponse:
    logger.error("%s: %s", type(exc).__name__, str(exc))
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc) if str(exc) else "Conflict"},
    )

async def app_exception_handler(
        request: Request,
        exc: AppException,
) -> JSONResponse:
    logger.error("%s: %s", type(exc).__name__, str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) if str(exc) else "Internal Error"},
    )