# Weather Job Queue System

Redis-backed FastAPI stack that periodically fetches weather data for four standard cities (London, New York, Tokyo, Cairo), stores the latest readings in PostgreSQL, and exposes a minimal dashboard plus JSON APIs.

## Architecture

- **FastAPI app (`main.py`)**
  - Routes:
    - `GET /` dashboard: HTML button to enqueue a job + recent job table.
    - `GET /weather` page: shows latest readings + “last sync” timestamp.
    - `POST /api/job`: manual job creation.
    - `GET /api/weather`: JSON weather data for the frontend table.
    - `GET /api/jobs`: recent job history.
    - `GET /api/health`: health probe.
  - Uses Jinja templates in `app/templates/` and styles in `app/static/`.

- **Background scheduler (`app/producer/schedule.py`)**
  - Runs as its own container; every `SCHEDULER_INTERVAL_SECONDS` enqueues the worker task with all default cities and records a job history entry flagged as `SCHEDULED`.

- **Worker (`app/worker/rq_worker.py`)**
  - RQ consumer that fetches jobs from Redis, calls Open-Meteo via `WeatherService`, upserts each city’s record, and tracks `JobHistory` state transitions.

- **Redis**
  - Shared queue for manual jobs and scheduler-triggered jobs.

- **PostgreSQL (cloud)**
  - Holds two tables (`weather_data`, `job_history`). Schema migrations live in `alembic/`.

## Requirements

- Docker + Docker Compose
- Python 3.11 if running locally without containers
- Access to Redis and PostgreSQL (cloud-hosted DB supported)

Key Python dependencies are pinned in `requirements.txt` (FastAPI, SQLAlchemy, psycopg2-binary, redis, rq, openmeteo-requests, etc.).

## Environment Variables

Create an `.env` at the project root with containing following values:

```
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DB_NAME
REDIS_URL=redis://HOST:6379/0
WEATHER_API_URL=https://api.open-meteo.com/v1/forecast
```

Adjust values to point at your managed Postgres instance and Redis deployment.

## Running with Docker Compose

```bash
docker compose up --build
```

Services started:

| Service   | Purpose                         | Command                                  |
|-----------|---------------------------------|------------------------------------------|
| app       | FastAPI + HTML frontend         | `uvicorn main:app --host 0.0.0.0 --reload` |
| worker    | RQ consumer                     | `python -m app.worker.run_worker`        |
| producer  | Background scheduler            | `python -m app.producer.schedule`        |
| redis     | Redis 7.x queue broker          | Official image                           |

Visit:

- `http://localhost:8000/` — dashboard (manual trigger + job table)
- `http://localhost:8000/weather` — weather table
- `http://localhost:8000/docs` — interactive API docs


1. Create a virtualenv & install deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
2. Ensure Redis & Postgres credentials resolve (`DATABASE_URL`, `REDIS_URL`).
3. Run services:
   - API: `uvicorn main:app --reload`
   - Worker: `python -m app.worker.run_worker`
   - Scheduler: `python -m app.producer.schedule`

## Data Flow

1. **Manual trigger** (Dashboard button) → `POST /api/job` → enqueues job in Redis → RQ worker executes `fetch_and_store_weather`.
2. **Scheduler** automatically enqueues the same job every 60s (configurable).
3. **Worker** fetches Open-Meteo data for each city, upserts rows into PostgreSQL, and updates job history.
4. **Frontend/API** reads from PostgreSQL to render tables or serve JSON.

## Database Schema

- `weather_data`
  - `city` (unique), `latitude`, `longitude`, `temperature`, `wind_speed`, `last_updated`.
- `job_history`
  - `job_id`, `status` (`pending`, `processing`, `completed`, `failed`), `trigger` (`manual`, `scheduled`), timestamps, optional `error_message`.

Migrations are under `alembic/versions`. Update the DB by running:

```bash
alembic upgrade head
```

## Testing Manual Flow

1. Start the stack (`docker compose up --build`).
2. Visit the dashboard and click **Fetch Weather Now**.
3. Observe new row in Job History (status transitions via worker).
4. Open `/weather` and confirm values update after the worker completes.
5. Wait for the scheduler to append jobs automatically (every minute by default).

## Troubleshooting

- Verify `.env` values match reachable Redis/Postgres endpoints.
- Check container logs (`docker compose logs app|worker|producer`) for stack traces.
- RQ jobs failing? Inspect `job_history.error_message` or Redis job logs.
- Stale weather data? Ensure the worker container is running and Redis queue names match (`weather-jobs` by default).

## Extending the System

- Add more cities by editing `CITIES` in `app/configuration/config.py`.
- Adjust scheduler frequency via `SCHEDULER_INTERVAL_SECONDS`.
- Enhance UI templates in `app/templates/` and styles in `app/static/styles.css`.
- Add authentication, analytics, or alerting layers as needed.

