from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routes.weather_routes import router as api_router
from app.configuration import get_settings

from app.models.sql_models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()



# Create FastAPI app
app = FastAPI(
    title="Weather API",
    description="Background job-based weather data fetching system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Weather API service...")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1]}")  # Log without credentials
    logger.info(f"Redis: {settings.REDIS_URL.split('@')[-1]}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Weather API service...")


@app.get("/")
async def root():
    return {
        "message": "Weather API Service",
        "version": "1.0.0",
        "endpoints": {
            "api_docs": "/docs",
            "health": "/api/health",
            "create_job": "POST /api/job",
            "get_weather": "GET /api/weather",
            "get_jobs": "GET /api/jobs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )