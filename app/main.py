from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.exceptions import AppException, NotFoundException, ConflictException
from app.core.handlers import (
    not_found_exception_handler,
    conflict_exception_handler,
    app_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield
    # Shutdown
    engine.dispose()

app = FastAPI(title="Organization Structure API", lifespan=lifespan)


app.add_exception_handler(NotFoundException, not_found_exception_handler)
app.add_exception_handler(ConflictException, conflict_exception_handler)
app.add_exception_handler(AppException, app_exception_handler)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/health/db/")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
