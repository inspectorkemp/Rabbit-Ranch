# Meat Rabbit Tracker (FastAPI + SQLite)

A lightweight ranch management app for tracking breedings, litters, growouts, and harvests.

---

## Local (venv)

### Install

```bash
python -m venv venv
# Windows:       venv\Scripts\activate
# macOS/Linux:   source venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
python -m uvicorn app.main:app --reload
```

| URL | Description |
|---|---|
| http://127.0.0.1:8000/dashboard | Main dashboard |
| http://127.0.0.1:8000/docs | Interactive API docs (Swagger) |

### Seed sample data

Stop uvicorn first, then:

```bash
python -m app.seed_db
```

This deletes and recreates the database with sample animals, breedings, litters, kits, and harvests.

### Run tests

```bash
pytest -q
```

Tests use an isolated in-memory SQLite database — no files created, no ordering dependencies.

---

## Docker

### Build + run

```bash
docker compose up --build
```

Open: http://127.0.0.1:8000/dashboard

The compose file mounts a named volume at `/data` for persistence across restarts.

### Seed data in Docker

```bash
docker compose run --rm rabbit_tracker python -m app.seed_db
docker compose up
```

---

## Data model

```
Animal ──< Harvest
Animal ──< Breeding (as doe or buck)
Breeding ──< Litter
Litter ──< Animal (kits, via litter_id)
```

### Animal statuses

| Status | Set by |
|---|---|
| `breeder` | Create form / PATCH |
| `growout` | Create form / generate-kits |
| `sold` | PATCH |
| `harvested` | `POST /harvests` only |
| `deceased` | `PATCH /animals/{id}` only |

### Key workflows

1. **Breeding** → `POST /breedings/`
2. **Kindling** → `POST /litters` (auto-marks breeding successful)
3. **Weaning** → `POST /litters/{id}/generate-kits` (creates kit Animal rows, one-time per litter)
4. **Harvest** → `POST /harvests` (marks animal harvested)
5. **Mortality** → `PATCH /animals/{id}` with `status: deceased`

---

## API summary

| Method | Path | Description |
|---|---|---|
| GET/POST | `/animals/` | List (with `?status=` filter, `?skip=`, `?limit=`) / Create |
| GET/PATCH/DELETE | `/animals/{id}` | Get / Update status / Delete |
| GET/POST | `/breedings/` | List / Create |
| GET/PUT/DELETE | `/breedings/{id}` | Get / Update (bred_date, result, notes) / Delete |
| GET/POST | `/litters` | List / Create |
| GET/DELETE | `/litters/{id}` | Get / Delete (cascades kits, resets breeding) |
| GET | `/litters/{id}/kits` | List kits for a litter |
| POST | `/litters/{id}/generate-kits` | Generate kit rows at weaning (once per litter) |
| GET/POST | `/harvests` | List / Create |
| DELETE | `/harvests/{id}` | Delete (reinstates animal to growout) |
| GET | `/reports/summary` | JSON KPIs + monthly time series |
| GET | `/reports/breedings.csv` | CSV export |
| GET | `/reports/litters.csv` | CSV export |
| GET | `/reports/harvests.csv` | CSV export |
| GET | `/metrics` | Aggregate KPIs |
| GET | `/dashboard/todo` | Operational to-do lists |
| GET | `/options/animals` | Dropdown options |
| GET | `/options/breedings` | Dropdown options |
| GET | `/options/litters` | Dropdown options |

---

## Common issues

**`NameError: name 'fastapi' is not defined`**

Wrong run command. Use:
```bash
# Correct
python -m uvicorn app.main:app --reload

# Wrong
uvicorn fastapi:app --reload
```

**Static files not found**

Always run from the project root (the directory containing `app/`). The app uses `pathlib` to resolve static paths relative to `app/main.py` so it works regardless, but the DB default path `./rabbit_tracker.db` is relative to cwd.

**Tests polluting each other**

Tests use `conftest.py` with an isolated in-memory DB per test. If you add new tests, use the `c` fixture (or `client` fixture) — never import a module-level `TestClient(app)`.
