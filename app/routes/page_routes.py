from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.configuration import get_settings
from app.database import get_db
from app.models import JobHistory, WeatherData

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Render the dashboard with manual trigger button and job history."""
    jobs: List[JobHistory] = (
        db.query(JobHistory)
        .order_by(JobHistory.created_at.desc())
        .limit(20)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "jobs": jobs,
        },
    )


@router.get("/weather", response_class=HTMLResponse)
async def weather_page(request: Request, db: Session = Depends(get_db)):
    """Render the weather data table for the standard cities."""
    weather_records: List[WeatherData] = (
        db.query(WeatherData)
        .order_by(WeatherData.city.asc())
        .all()
    )
    last_sync: datetime | None = db.query(
        func.max(WeatherData.last_updated)
    ).scalar()

    data_by_city = {record.city: record for record in weather_records}
    ordered_cities = [
        {
            "name": city,
            "record": data_by_city.get(city),
        }
        for city in settings.CITIES.keys()
    ]

    return templates.TemplateResponse(
        "weather.html",
        {
            "request": request,
            "cities": ordered_cities,
            "last_sync": last_sync,
        },
    )

