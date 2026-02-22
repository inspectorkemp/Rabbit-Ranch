from __future__ import annotations

# IMPORTANT:
# Correct command:
#   python -m uvicorn app.main:app --reload

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .routers import animals, breedings
from .routers import litters as litters_router
from .routers import harvests as harvests_router
from .routers import reports as reports_router
from .routers import feed_costs as feed_costs_router
from .routers import sales as sales_router
from . import models, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meat Rabbit Tracker")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


# -----------------------------
# UI PAGES
# -----------------------------
@app.get("/dashboard")
def ui_dashboard():
    return FileResponse("app/static/dashboard.html")


@app.get("/ranch/animals")
def ui_animals():
    return FileResponse("app/static/animals.html")


@app.get("/ranch/breedings")
def ui_breedings():
    return FileResponse("app/static/breedings.html")


@app.get("/ranch/kindlings")
def ui_kindlings():
    return FileResponse("app/static/kindlings.html")


@app.get("/ranch/weanings")
def ui_weanings():
    return FileResponse("app/static/weanings.html")


@app.get("/ranch/harvests")
def ui_harvests():
    return FileResponse("app/static/harvests.html")


@app.get("/ranch/feed-costs")
def ui_feed_costs():
    return FileResponse("app/static/feed_costs.html")


@app.get("/ranch/sales")
def ui_sales():
    return FileResponse("app/static/sales.html")


@app.get("/ranch/reports")
def ui_reports():
    return FileResponse("app/static/reports.html")


# -----------------------------
# API ROUTERS
# -----------------------------
app.include_router(animals.router)
app.include_router(breedings.router)
app.include_router(litters_router.router)
app.include_router(harvests_router.router)
app.include_router(feed_costs_router.router)
app.include_router(sales_router.router)
app.include_router(reports_router.router)


# -----------------------------
# OPTION ENDPOINTS (for dropdowns)
# -----------------------------
@app.get("/options/breedings", response_model=list[schemas.OptionItem])
def options_breedings(
    include_successful: bool = True,
    db: Session = Depends(get_db),
):
    animals = db.query(models.Animal).all()
    tattoo_by_id = {a.animal_id: a.tattoo for a in animals}

    q = db.query(models.Breeding)
    if not include_successful:
        q = q.filter(models.Breeding.result != "successful")

    breedings = q.order_by(models.Breeding.bred_date.desc()).all()

    out: list[schemas.OptionItem] = []
    for b in breedings:
        doe = tattoo_by_id.get(b.doe_id, f"ID {b.doe_id}")
        buck = tattoo_by_id.get(b.buck_id, f"ID {b.buck_id}")
        label = f"#{b.breeding_id} {doe} x {buck} (bred {b.bred_date})"
        out.append(schemas.OptionItem(id=b.breeding_id, label=label))
    return out


@app.get("/options/litters", response_model=list[schemas.OptionItem])
def options_litters(
    only_not_weaned: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(models.Litter)
    if only_not_weaned:
        q = q.filter(models.Litter.weaned_count.is_(None))

    litters = q.order_by(models.Litter.kindling_date.desc()).all()

    out: list[schemas.OptionItem] = []
    for l in litters:
        w = "—" if l.weaned_count is None else l.weaned_count
        label = f"L{l.litter_id} (breeding #{l.breeding_id}) kindled {l.kindling_date} alive {l.born_alive} weaned {w}"
        out.append(schemas.OptionItem(id=l.litter_id, label=label))
    return out


@app.get("/options/animals", response_model=list[schemas.OptionItem])
def options_animals(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Animal)
    if status:
        q = q.filter(models.Animal.status == status)

    animals = q.order_by(models.Animal.tattoo.asc()).all()

    out: list[schemas.OptionItem] = []
    for a in animals:
        label = f"{a.tattoo} (ID {a.animal_id}, {a.sex}, {a.status})"
        out.append(schemas.OptionItem(id=a.animal_id, label=label))
    return out


# -----------------------------
# DERIVED METRICS
# -----------------------------
@app.get("/metrics", response_model=dict)
def metrics(db: Session = Depends(get_db)):
    litters = db.query(models.Litter).all()
    harvests = db.query(models.Harvest).all()

    total_litters = len(litters)
    avg_litter_size = (
        sum(l.born_alive for l in litters) / total_litters
        if total_litters else None
    )

    kit_survival_rate = None
    if litters and all(l.weaned_count is not None for l in litters) and sum(l.born_alive for l in litters) > 0:
        kit_survival_rate = sum(l.weaned_count for l in litters) / sum(l.born_alive for l in litters)

    avg_days_to_harvest = None
    if harvests:
        days = []
        for h in harvests:
            a = db.get(models.Animal, h.animal_id)
            if a and a.birth_date:
                days.append((h.harvest_date - a.birth_date).days)
        if days:
            avg_days_to_harvest = sum(days) / len(days)

    return {
        "total_litters": total_litters,
        "average_litter_size": avg_litter_size,
        "kit_survival_rate": kit_survival_rate,
        "average_days_to_harvest": avg_days_to_harvest,
        "harvested_rabbits": len(harvests),
    }


# -----------------------------
# DASHBOARD TODO
# -----------------------------
@app.get("/dashboard/todo", response_model=dict)
def dashboard_todo(
    kindling_window_days: int = Query(default=7, ge=1, le=60),
    wean_age_days: int = Query(default=42, ge=1, le=120),
    harvest_age_days: int = Query(default=84, ge=1, le=200),
    limit: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
):
    from datetime import date, timedelta

    today = date.today()

    animals = db.query(models.Animal).all()
    tattoo_by_id = {a.animal_id: a.tattoo for a in animals}

    # 1) Kindlings due soon
    end = today + timedelta(days=kindling_window_days)
    due_breedings = (
        db.query(models.Breeding)
        .filter(models.Breeding.result == "pending")
        .filter(models.Breeding.expected_kindling.isnot(None))
        .filter(models.Breeding.expected_kindling >= today)
        .filter(models.Breeding.expected_kindling <= end)
        .order_by(models.Breeding.expected_kindling.asc())
        .limit(limit)
        .all()
    )

    kindlings_due = []
    for b in due_breedings:
        doe = tattoo_by_id.get(b.doe_id, f"ID {b.doe_id}")
        buck = tattoo_by_id.get(b.buck_id, f"ID {b.buck_id}")
        kindlings_due.append({
            "breeding_id": b.breeding_id,
            "doe_tattoo": doe,
            "buck_tattoo": buck,
            "bred_date": b.bred_date,
            "expected_kindling": b.expected_kindling,
            "label": f"{doe} x {buck} — expected {b.expected_kindling}",
            "link": "/ranch/kindlings",
        })

    # 2) Weanings due
    wean_cutoff = today - timedelta(days=wean_age_days)
    candidate_litters = (
        db.query(models.Litter)
        .filter(models.Litter.kindling_date <= wean_cutoff)
        .order_by(models.Litter.kindling_date.asc())
        .limit(limit)
        .all()
    )

    kit_count_by_litter: dict[int, int] = {}
    for a in animals:
        if a.litter_id is not None:
            kit_count_by_litter[a.litter_id] = kit_count_by_litter.get(a.litter_id, 0) + 1

    weanings_due = []
    for l in candidate_litters:
        kits = kit_count_by_litter.get(l.litter_id, 0)
        if kits > 0:
            continue
        age_days = (today - l.kindling_date).days
        weanings_due.append({
            "litter_id": l.litter_id,
            "breeding_id": l.breeding_id,
            "kindling_date": l.kindling_date,
            "age_days": age_days,
            "born_alive": l.born_alive,
            "weaned_count": l.weaned_count,
            "kits_generated": kits,
            "label": f"L{l.litter_id} — {age_days}d old (kindled {l.kindling_date})",
            "link": "/ranch/weanings",
        })

    # 3) Harvest-ready growouts
    harvest_cutoff = today - timedelta(days=harvest_age_days)
    harvest_ready_rows = (
        db.query(models.Animal)
        .filter(models.Animal.status == "growout")
        .filter(models.Animal.birth_date.isnot(None))
        .filter(models.Animal.birth_date <= harvest_cutoff)
        .order_by(models.Animal.birth_date.asc())
        .limit(limit)
        .all()
    )

    harvest_ready = []
    for a in harvest_ready_rows:
        age_days = (today - a.birth_date).days if a.birth_date else None
        harvest_ready.append({
            "animal_id": a.animal_id,
            "tattoo": a.tattoo,
            "birth_date": a.birth_date,
            "age_days": age_days,
            "label": f"{a.tattoo} — {age_days}d old",
            "link": "/ranch/harvests",
        })

    return {
        "as_of": today,
        "params": {
            "kindling_window_days": kindling_window_days,
            "wean_age_days": wean_age_days,
            "harvest_age_days": harvest_age_days,
            "limit": limit,
        },
        "kindlings_due": kindlings_due,
        "weanings_due": weanings_due,
        "harvest_ready": harvest_ready,
    }


@app.get("/")
def root():
    return {"status": "ok", "dashboard": "/dashboard"}
