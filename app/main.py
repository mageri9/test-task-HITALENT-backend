from fastapi import FastAPI

app = FastAPI(title="Organization Structure API")


@app.get("/health")
async def health_check():
    return {"status": "ok"}