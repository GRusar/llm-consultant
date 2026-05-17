from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME}
