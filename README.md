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
2. **Splits (before deployment):** Training uses **time-based** train / validation / test — no random shuffle across fight dates. Defaults: validation = fights on/after `2022-01-01`, holdout test = on/after `2024-01-01` (configurable). Use `--auto-split` for chronological **70% / 15% / 15%** if cutoffs leave empty val/test.
3. **Hyperparameters (Optuna):** Tune on the **validation** slice only (test stays untouched), then train the final calibrated model:

   ```bash
   python -m ml.hyperparameter_tune --trials 100   # writes ml/models/best_hyperparams.json
   python -m ml.train --hyperparams-json ml/models/best_hyperparams.json
   ```

   Or with auto split: `python -m ml.hyperparameter_tune --auto-split --trials 80`

   In production, `POST /api/v1/admin/retrain?use_tuned_hyperparams=true` applies `ml/models/best_hyperparams.json` when that file exists (run HPO in CI or a worker first).

4. Train without HPO: `python -m ml.train` (same split defaults).
5. Predictions on `/api/v1/fights/{fight_id}` use the bundle when present; otherwise a small heuristic fallback.

### Data fidelity & fighter age

- **UFCStats:** Each fight page’s stat tables are merged into per-fighter `totals`; the full dict is stored in `fight_participations.stats_json` (audit + future features). Numeric columns are still populated for the current model. Control time strings like `4:32` are converted to seconds.
- **Age at fight time (training):** Features use each fighter’s **DOB vs that bout’s event date** (not “age today”).
- **Age for upcoming predictions:** Uses the **event date** when set; if the card has no date yet, uses **today** so ages stay current until UFCStats lists the date.

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
