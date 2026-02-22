"""
app/seed_db.py
--------------
Populates the database with realistic-looking demo data covering
all entity types: animals, breedings, litters, harvests, feed costs, sales.

Run from the project root:
    python -m app.seed_db

Pass --reset to wipe the database first:
    python -m app.seed_db --reset
"""
from __future__ import annotations

import sys
import random
from datetime import date, timedelta
from urllib.parse import urlparse

from .database import Base, engine, SessionLocal, DATABASE_URL
from . import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_ago(n: int) -> date:
    return date.today() - timedelta(days=n)


def _remove_sqlite_file_if_local() -> None:
    """Delete the SQLite file so we start completely fresh."""
    parsed = urlparse(DATABASE_URL)
    # urlparse turns  sqlite:///./foo.db  into  path=./foo.db
    path = parsed.path.lstrip("/")
    if path and path != ":memory:":
        import os
        if os.path.exists(path):
            os.remove(path)
            print(f"  Removed existing database: {path}")


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

BREEDS  = ["New Zealand White", "California", "Rex", "Flemish Giant", "Satin"]
COLORS  = ["White", "Black", "Grey", "Broken", "Chinchilla"]
BUYERS  = [
    ("Oakridge Farm",    "555-0101"),
    ("Green Pastures",   "555-0182"),
    ("River Bend Ranch", "555-0234"),
    ("Local Feed Store", "555-0311"),
    None,   # anonymous buyer
]

FEED_DESCRIPTIONS = [
    ("50 lb pellets",        2.80,  14.00),
    ("50 lb pellets",        2.80,  14.00),
    ("Timothy hay bale",     None,   8.50),
    ("50 lb pellets",        2.80,  14.00),
    ("Oat hay bale",         None,   9.00),
    ("100 lb pellets",       2.75,  27.50),
    ("50 lb pellets",        2.80,  14.00),
    ("Timothy hay bale",     None,   8.50),
    ("50 lb pellets",        2.80,  14.00),
    ("Mineral supplement",   None,  12.00),
    ("100 lb pellets",       2.75,  27.50),
    ("Timothy hay bale",     None,   8.50),
]


def seed(db) -> None:
    random.seed(42)      # reproducible

    # ------------------------------------------------------------------
    # 1. Breeders: 3 does, 2 bucks
    # ------------------------------------------------------------------
    print("  Creating breeders...")

    does = [
        models.Animal(tattoo="DOE-A", sex="F", status="breeder",
                      breed=BREEDS[0], color=COLORS[0],
                      birth_date=_days_ago(540), source="purchased"),
        models.Animal(tattoo="DOE-B", sex="F", status="breeder",
                      breed=BREEDS[1], color=COLORS[2],
                      birth_date=_days_ago(480), source="purchased"),
        models.Animal(tattoo="DOE-C", sex="F", status="breeder",
                      breed=BREEDS[0], color=COLORS[1],
                      birth_date=_days_ago(420), source="homebred"),
    ]
    bucks = [
        models.Animal(tattoo="BUCK-A", sex="M", status="breeder",
                      breed=BREEDS[0], color=COLORS[0],
                      birth_date=_days_ago(520), source="purchased"),
        models.Animal(tattoo="BUCK-B", sex="M", status="breeder",
                      breed=BREEDS[1], color=COLORS[3],
                      birth_date=_days_ago(460), source="purchased"),
    ]

    for a in does + bucks:
        db.add(a)
    db.flush()

    # ------------------------------------------------------------------
    # 2. Breedings — 6 completed, 1 pending
    # ------------------------------------------------------------------
    print("  Creating breedings...")

    breeding_plan = [
        # (doe_idx, buck_idx, days_ago_bred, result)
        (0, 0, 210, "successful"),
        (1, 1, 190, "successful"),
        (0, 1, 170, "successful"),
        (2, 0, 150, "successful"),
        (1, 0, 130, "successful"),
        (2, 1, 110, "successful"),
        (0, 0,  14, "pending"),    # upcoming kindling
    ]

    breedings = []
    for doe_i, buck_i, days_ago, result in breeding_plan:
        bred = _days_ago(days_ago)
        b = models.Breeding(
            doe_id=does[doe_i].animal_id,
            buck_id=bucks[buck_i].animal_id,
            bred_date=bred,
            expected_kindling=bred + timedelta(days=31),
            result=result,
        )
        db.add(b)
        db.flush()
        breedings.append(b)

    # ------------------------------------------------------------------
    # 3. Litters (one per successful breeding)
    # ------------------------------------------------------------------
    print("  Creating litters and kits...")

    completed_breedings = [b for b in breedings if b.result == "successful"]
    litters = []

    for b in completed_breedings:
        born_alive = random.randint(6, 10)
        born_dead  = random.randint(0, 1)
        weaned     = max(0, born_alive - random.randint(0, 1))

        kindling_date = b.bred_date + timedelta(days=31)
        litter = models.Litter(
            breeding_id=b.breeding_id,
            kindling_date=kindling_date,
            born_alive=born_alive,
            born_dead=born_dead,
            weaned_count=weaned,
        )
        db.add(litter)
        db.flush()
        litters.append(litter)

        # Generate kit animals for this litter
        males   = weaned // 2
        females = weaned - males
        sexes   = ["M"] * males + ["F"] * females
        random.shuffle(sexes)

        for i, sex in enumerate(sexes, start=1):
            kit = models.Animal(
                tattoo=f"L{litter.litter_id}-K{i:02d}",
                sex=sex,
                status="growout",
                birth_date=kindling_date,
                litter_id=litter.litter_id,
                source="homebred",
            )
            db.add(kit)

    db.flush()

    # ------------------------------------------------------------------
    # 4. Harvests — take some kits from older litters
    # ------------------------------------------------------------------
    print("  Creating harvests...")

    # Harvest kits from the 3 oldest litters that are old enough (~84 days)
    harvestable_litters = [l for l in litters if (date.today() - l.kindling_date).days >= 84]

    for litter in harvestable_litters:
        kits = (
            db.query(models.Animal)
            .filter(models.Animal.litter_id == litter.litter_id,
                    models.Animal.status == "growout")
            .all()
        )
        # Harvest roughly half the litter, leave some as growouts/sold
        harvest_count = max(1, len(kits) // 2)
        to_harvest = kits[:harvest_count]

        for kit in to_harvest:
            live_weight    = random.randint(2200, 2800)
            carcass_weight = int(live_weight * random.uniform(0.52, 0.58))
            harvest_date   = litter.kindling_date + timedelta(days=random.randint(80, 90))

            h = models.Harvest(
                animal_id=kit.animal_id,
                harvest_date=harvest_date,
                live_weight_grams=live_weight,
                carcass_weight_grams=carcass_weight,
            )
            kit.status = "harvested"
            db.add(h)

    db.flush()

    # ------------------------------------------------------------------
    # 5. Feed costs — roughly monthly for the past year
    # ------------------------------------------------------------------
    print("  Creating feed costs...")

    for i, (desc, cpu, total) in enumerate(FEED_DESCRIPTIONS):
        fc = models.FeedCost(
            date=_days_ago(360 - i * 28),   # spread ~monthly over the year
            description=desc,
            cost_per_unit=cpu,
            total_cost=total,
        )
        db.add(fc)

    db.flush()

    # ------------------------------------------------------------------
    # 6. Sales — sell some kits from the middle litters
    # ------------------------------------------------------------------
    print("  Creating sales...")

    # Pick kits that are still growouts (not harvested yet)
    growout_kits = (
        db.query(models.Animal)
        .filter(models.Animal.status == "growout",
                models.Animal.litter_id.isnot(None))
        .order_by(models.Animal.animal_id)
        .all()
    )

    # Sell a handful individually at varying prices
    individual_sales = growout_kits[:4]
    for kit in individual_sales:
        buyer = random.choice([b for b in BUYERS if b is not None])
        sale_price = round(random.uniform(18.0, 35.0), 2)
        sale_date = kit.birth_date + timedelta(days=random.randint(56, 75))

        s = models.Sale(
            animal_id=kit.animal_id,
            sale_date=sale_date,
            sale_price=sale_price,
            buyer_name=buyer[0],
            buyer_contact=buyer[1],
            notes="Live sale",
        )
        kit.status = "sold"
        db.add(s)

    # Sell one whole litter if there's a litter with remaining growouts
    if len(litters) >= 4:
        litter_to_sell = litters[3]
        remaining_kits = (
            db.query(models.Animal)
            .filter(models.Animal.litter_id == litter_to_sell.litter_id,
                    models.Animal.status == "growout")
            .all()
        )
        if remaining_kits:
            buyer = BUYERS[1]   # Green Pastures
            litter_sale = models.Sale(
                litter_id=litter_to_sell.litter_id,
                sale_date=litter_to_sell.kindling_date + timedelta(days=63),
                sale_price=round(len(remaining_kits) * 22.50, 2),
                buyer_name=buyer[0],
                buyer_contact=buyer[1],
                notes=f"Whole litter sale ({len(remaining_kits)} kits)",
            )
            for kit in remaining_kits:
                kit.status = "sold"
            db.add(litter_sale)

    db.commit()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    animal_count  = db.query(models.Animal).count()
    litter_count  = db.query(models.Litter).count()
    harvest_count = db.query(models.Harvest).count()
    feed_count    = db.query(models.FeedCost).count()
    sale_count    = db.query(models.Sale).count()

    print(f"\n  ✓ Animals:     {animal_count}")
    print(f"  ✓ Breedings:   {len(breedings)}")
    print(f"  ✓ Litters:     {litter_count}")
    print(f"  ✓ Harvests:    {harvest_count}")
    print(f"  ✓ Feed costs:  {feed_count}")
    print(f"  ✓ Sales:       {sale_count}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    reset = "--reset" in sys.argv

    if reset:
        print("Resetting database...")
        _remove_sqlite_file_if_local()

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    print("Seeding data...")
    db = SessionLocal()
    try:
        seed(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("\nDone. Run the app with:")
    print("  python -m uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
