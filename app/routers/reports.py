from __future__ import annotations

from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models

router = APIRouter(prefix="/reports", tags=["reports"])


def _date_range_filters(start_date, end_date, col):
    if start_date is None and end_date is None:
        return
    if start_date is not None:
        yield col >= start_date
    if end_date is not None:
        yield col <= end_date


def _csv_stream(rows, header):
    import csv
    from io import StringIO

    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    yield buf.getvalue()

    for r in rows:
        buf.seek(0)
        buf.truncate(0)
        w.writerow(r)
        yield buf.getvalue()


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


@router.get("/summary")
def report_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # --- Litters ---
    lq = db.query(models.Litter)
    for f in _date_range_filters(start_date, end_date, models.Litter.kindling_date):
        lq = lq.filter(f)
    litters = lq.all()

    total_litters = len(litters)
    total_born_alive = sum(l.born_alive or 0 for l in litters)
    avg_litter_size = (total_born_alive / total_litters) if total_litters else None

    weaned_known = [l for l in litters if l.weaned_count is not None]
    survival_rate = None
    denom = sum(l.born_alive or 0 for l in weaned_known)
    if weaned_known and denom > 0:
        survival_rate = sum(l.weaned_count or 0 for l in weaned_known) / denom

    # --- Harvests ---
    hq = db.query(models.Harvest)
    for f in _date_range_filters(start_date, end_date, models.Harvest.harvest_date):
        hq = hq.filter(f)
    harvests = hq.all()

    harvested_count = len(harvests)

    animals = db.query(models.Animal).all()
    animal_by_id = {a.animal_id: a for a in animals}

    days_to_harvest = []
    yields = []
    for h in harvests:
        a = animal_by_id.get(h.animal_id)
        if a and a.birth_date:
            days_to_harvest.append((h.harvest_date - a.birth_date).days)
        if h.live_weight_grams and h.carcass_weight_grams and h.live_weight_grams > 0:
            yields.append(h.carcass_weight_grams / h.live_weight_grams)

    avg_days_to_harvest = (sum(days_to_harvest) / len(days_to_harvest)) if days_to_harvest else None
    avg_yield = (sum(yields) / len(yields)) if yields else None

    # --- Mortality ---
    aq = db.query(models.Animal).filter(models.Animal.status == "deceased")
    if start_date is not None or end_date is not None:
        if start_date is not None:
            aq = aq.filter(models.Animal.death_date.isnot(None)).filter(models.Animal.death_date >= start_date)
        if end_date is not None:
            aq = aq.filter(models.Animal.death_date.isnot(None)).filter(models.Animal.death_date <= end_date)
    deceased = aq.all()
    mortality_count = len(deceased)

    # --- Feed Costs ---
    fq = db.query(models.FeedCost)
    for f in _date_range_filters(start_date, end_date, models.FeedCost.date):
        fq = fq.filter(f)
    feed_costs = fq.all()

    total_feed_cost = sum(fc.total_cost or 0 for fc in feed_costs)
    avg_feed_cost_per_month = None
    feed_cost_by_month: dict[str, float] = defaultdict(float)
    for fc in feed_costs:
        feed_cost_by_month[_month_key(fc.date)] += float(fc.total_cost or 0)
    if feed_cost_by_month:
        avg_feed_cost_per_month = total_feed_cost / len(feed_cost_by_month)

    # Cost per harvested rabbit (in range)
    cost_per_harvested = None
    if harvested_count > 0 and total_feed_cost > 0:
        cost_per_harvested = total_feed_cost / harvested_count

    # --- Time series ---
    litters_by_month: dict[str, int] = defaultdict(int)
    born_alive_by_month: dict[str, int] = defaultdict(int)
    weaned_by_month: dict[str, int] = defaultdict(int)

    for l in litters:
        mk = _month_key(l.kindling_date)
        litters_by_month[mk] += 1
        born_alive_by_month[mk] += int(l.born_alive or 0)
        if l.weaned_count is not None:
            weaned_by_month[mk] += int(l.weaned_count or 0)

    harvests_by_month: dict[str, int] = defaultdict(int)
    avg_yield_by_month_acc: dict[str, list] = defaultdict(list)

    for h in harvests:
        mk = _month_key(h.harvest_date)
        harvests_by_month[mk] += 1
        if h.live_weight_grams and h.carcass_weight_grams and h.live_weight_grams > 0:
            avg_yield_by_month_acc[mk].append(h.carcass_weight_grams / h.live_weight_grams)

    avg_yield_by_month: dict[str, float | None] = {}
    for mk, vals in avg_yield_by_month_acc.items():
        avg_yield_by_month[mk] = sum(vals) / len(vals) if vals else None

    mortality_by_month: dict[str, int] = defaultdict(int)
    for a in deceased:
        if a.death_date:
            mortality_by_month[_month_key(a.death_date)] += 1

    # Stable month axis across all series
    months = sorted(set(
        list(litters_by_month.keys())
        + list(harvests_by_month.keys())
        + list(mortality_by_month.keys())
        + list(feed_cost_by_month.keys())
    ))

    def series(name: str, mapping, fmt="int"):
        out = []
        for mk in months:
            v = mapping.get(mk, 0)
            if v is None:
                v = 0
            out.append({"month": mk, "value": float(v) if fmt == "float" else int(v)})
        return {"name": name, "points": out}

    payload = {
        "range": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "kpis": {
            "total_litters": total_litters,
            "avg_litter_size": avg_litter_size,
            "survival_to_wean": survival_rate,
            "harvested_count": harvested_count,
            "avg_days_to_harvest": avg_days_to_harvest,
            "avg_yield": avg_yield,
            "mortality_count": mortality_count,
            # Feed cost KPIs
            "total_feed_cost": total_feed_cost,
            "avg_feed_cost_per_month": avg_feed_cost_per_month,
            "cost_per_harvested_rabbit": cost_per_harvested,
        },
        "series": {
            "litters": series("Litters", litters_by_month, "int"),
            "born_alive": series("Born Alive", born_alive_by_month, "int"),
            "weaned": series("Weaned", weaned_by_month, "int"),
            "harvests": series("Harvests", harvests_by_month, "int"),
            "mortality": series("Mortality", mortality_by_month, "int"),
            "avg_yield": {
                "name": "Avg Yield",
                "points": [
                    {"month": mk, "value": float((avg_yield_by_month.get(mk) or 0.0))}
                    for mk in months
                ],
            },
            # Feed cost series
            "feed_cost": {
                "name": "Feed Cost ($)",
                "points": [
                    {"month": mk, "value": round(feed_cost_by_month.get(mk, 0.0), 2)}
                    for mk in months
                ],
            },
        },
    }

    return payload


@router.get("/breedings.csv")
def report_breedings_csv(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    result: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    animals = db.query(models.Animal).all()
    tattoo_by_id = {a.animal_id: a.tattoo for a in animals}

    q = db.query(models.Breeding)
    for f in _date_range_filters(start_date, end_date, models.Breeding.bred_date):
        q = q.filter(f)
    if result:
        q = q.filter(models.Breeding.result == result)

    breedings = q.order_by(models.Breeding.bred_date.desc()).all()

    header = ["breeding_id", "doe_tattoo", "buck_tattoo", "bred_date", "expected_kindling", "result"]
    rows = [
        [
            b.breeding_id,
            tattoo_by_id.get(b.doe_id, b.doe_id),
            tattoo_by_id.get(b.buck_id, b.buck_id),
            b.bred_date,
            b.expected_kindling,
            b.result,
        ]
        for b in breedings
    ]

    return StreamingResponse(
        _csv_stream(rows, header),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=breedings.csv"},
    )


@router.get("/litters.csv")
def report_litters_csv(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    animals = db.query(models.Animal).all()
    tattoo_by_id = {a.animal_id: a.tattoo for a in animals}

    breedings = db.query(models.Breeding).all()
    breeding_map = {
        b.breeding_id: (tattoo_by_id.get(b.doe_id, b.doe_id), tattoo_by_id.get(b.buck_id, b.buck_id))
        for b in breedings
    }

    q = db.query(models.Litter)
    for f in _date_range_filters(start_date, end_date, models.Litter.kindling_date):
        q = q.filter(f)
    litters = q.order_by(models.Litter.kindling_date.desc()).all()

    header = ["litter_id", "breeding_id", "doe_tattoo", "buck_tattoo", "kindling_date", "born_alive", "born_dead", "weaned_count", "survival_pct"]
    rows = []
    for l in litters:
        doe, buck = breeding_map.get(l.breeding_id, ("—", "—"))
        survival = None
        if l.weaned_count is not None and l.born_alive:
            survival = round((l.weaned_count / l.born_alive) * 100, 1)
        rows.append([l.litter_id, l.breeding_id, doe, buck, l.kindling_date, l.born_alive, l.born_dead, l.weaned_count, survival])

    return StreamingResponse(
        _csv_stream(rows, header),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=litters.csv"},
    )


@router.get("/harvests.csv")
def report_harvests_csv(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    animals = db.query(models.Animal).all()
    animal_by_id = {a.animal_id: a for a in animals}

    q = db.query(models.Harvest)
    for f in _date_range_filters(start_date, end_date, models.Harvest.harvest_date):
        q = q.filter(f)
    harvests = q.order_by(models.Harvest.harvest_date.desc()).all()

    header = ["harvest_id", "animal_id", "tattoo", "litter_id", "harvest_date", "age_days", "live_weight_grams", "carcass_weight_grams", "yield_pct"]
    rows = []
    for h in harvests:
        a = animal_by_id.get(h.animal_id)
        tattoo = a.tattoo if a else "—"
        litter_id = a.litter_id if a else None
        age_days = (h.harvest_date - a.birth_date).days if (a and a.birth_date) else None
        yld = None
        if h.live_weight_grams and h.carcass_weight_grams and h.live_weight_grams > 0:
            yld = round((h.carcass_weight_grams / h.live_weight_grams) * 100, 1)
        rows.append([h.harvest_id, h.animal_id, tattoo, litter_id, h.harvest_date, age_days, h.live_weight_grams, h.carcass_weight_grams, yld])

    return StreamingResponse(
        _csv_stream(rows, header),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=harvests.csv"},
    )


@router.get("/feed-costs.csv")
def report_feed_costs_csv(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.FeedCost)
    for f in _date_range_filters(start_date, end_date, models.FeedCost.date):
        q = q.filter(f)
    feed_costs = q.order_by(models.FeedCost.date.desc()).all()

    header = ["feed_cost_id", "date", "description", "cost_per_unit", "total_cost"]
    rows = [
        [fc.feed_cost_id, fc.date, fc.description, fc.cost_per_unit, fc.total_cost]
        for fc in feed_costs
    ]

    return StreamingResponse(
        _csv_stream(rows, header),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=feed_costs.csv"},
    )
