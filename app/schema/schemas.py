from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models import JobStatus, JobTrigger


# Weather Schemas
class WeatherDataBase(BaseModel):
    city: str
    latitude: float
    longitude: float
    temperature: float
    wind_speed: float


class WeatherDataResponse(WeatherDataBase):
    id: int
    last_updated: datetime
    
    class Config:
        from_attributes = True


class WeatherListResponse(BaseModel):
    data: List[WeatherDataResponse]
    last_sync: Optional[datetime] = None


# Job Schemas
class JobCreate(BaseModel):
    cities: List[str] = Field(
        default=["London", "New York", "Tokyo", "Cairo"],
        description="List of cities to fetch weather data for"
    )


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobHistoryResponse(BaseModel):
    id: int
    job_id: str
    status: JobStatus
    trigger: JobTrigger
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


# City Configuration
class CityConfig(BaseModel):
    name: str
    latitude: float
    longitude: float