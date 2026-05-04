# UFC Predictor

Full-stack scaffold: Python scrapers + SQLAlchemy DB, ML pipeline (XGBoost/LightGBM + logistic voting, calibrated), FastAPI backend, React (Vite + Tailwind + TanStack Query + Recharts) frontend, Docker Compose.

## Quick start (local)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# optional: alembic upgrade head
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (separate terminal):

```bash
cd frontend && npm install && npm run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env` if the API is not proxied (default Vite proxy targets `http://localhost:8000`).

## Data & model

1. Ingest UFCStats events (network): use `scrapers.scraper_runner.ingest_event_page(db, "<event-url>")` from a Python shell or extend admin routes.
2. Train: `python -m ml.train` (writes `ml/models/production.pkl` and metadata).
3. Predictions on `/api/v1/fights/{fight_id}` use the bundle when present; otherwise a small heuristic fallback.

## Admin

`POST /api/v1/admin/refresh-events` and `POST /api/v1/admin/retrain` require header `Authorization: Bearer <ADMIN_API_KEY>` (see `.env.example`).

## Docker

```bash
docker compose up --build
```

Backend: `8000`, frontend (nginx): `3000`.

## Tests

```bash
pytest tests/ -v
cd frontend && npm run test
```
