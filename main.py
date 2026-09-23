from fastapi import FastAPI
from app.config.logging import configure_logger
from app.api.routes.upload import router as upload_router
from app.api.routes.status import router as status_router

configure_logger()

app = FastAPI(
    title="Olympiad AI Video Generator",
    version="0.1.0",
)

app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(status_router, prefix="/api", tags=["status"])

@app.get("/")
async def root():
    return {
        "application": "Olympiad AI Video Generator",
        "status": "running",
        "version": "0.1.0",
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }