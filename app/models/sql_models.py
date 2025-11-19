from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
from app.database.db_config import Base
import enum


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobTrigger(str, enum.Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class WeatherData(Base):
    __tablename__ = "weather_data"
    
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), unique=True, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)  # Celsius
    wind_speed = Column(Float, nullable=False)   # km/h
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobHistory(Base):
    __tablename__ = "job_history"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    trigger = Column(Enum(JobTrigger), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(500), nullable=True)