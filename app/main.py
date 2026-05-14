from fastapi import FastAPI

from app.models import Base # noqa: F401

app = FastAPI(title="Organization Structure API")


@app.get("/health")
async def health_check():
    return {"status": "ok"}