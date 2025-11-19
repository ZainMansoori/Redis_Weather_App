import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.configuration import get_settings
from app.routes.page_routes import router as page_router
from app.routes.weather_routes import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "app" / "static"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

# Create FastAPI app
app = FastAPI(
    title="Weather API",
    description="Redis-backed weather data pipeline with scheduling & worker",
    version="1.0.0",
)

# Configure CORS
allow_origins = ALLOWED_ORIGINS or ["*"]
allow_credentials = False if "*" in allow_origins else True
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets & routers
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(page_router)
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Weather API service...")
    db_target = settings.DATABASE_URL.rsplit("@", maxsplit=1)[-1]
    redis_target = settings.REDIS_URL.rsplit("@", maxsplit=1)[-1]
    logger.info("Starting Weather API service...")
    logger.info("Database: %s", db_target)
    logger.info("Redis: %s", redis_target)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Weather API service...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )