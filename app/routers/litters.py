from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/litters", tags=["litters"])


@router.get("/", response_model=list[schemas.LitterOut])
def list_litters(db: Session = Depends(get_db)):
    return db.query(models.Litter).order_by(models.Litter.kindling_date.desc()).all()


@router.post("/", response_model=schemas.LitterOut)
def create_litter(payload: schemas.LitterCreate, db: Session = Depends(get_db)):
    breeding = db.get(models.Breeding, payload.breeding_id)
    if not breeding:
        raise HTTPException(404, "Breeding not found")

    try:
        litter = models.Litter(**payload.model_dump())
        breeding.result = "successful"
        db.add(litter)
        db.commit()
        db.refresh(litter)
        return litter
    except Exception:
        db.rollback()
        raise


@router.patch("/{litter_id}", response_model=schemas.LitterOut)
def update_litter(litter_id: int, payload: schemas.LitterUpdate, db: Session = Depends(get_db)):
    litter = db.get(models.Litter, litter_id)
    if not litter:
        raise HTTPException(404, "Litter not found")

    if payload.kindling_date is not None:
        litter.kindling_date = payload.kindling_date
    if payload.born_alive is not None:
        litter.born_alive = payload.born_alive
    if payload.born_dead is not None:
        litter.born_dead = payload.born_dead
    if payload.weaned_count is not None:
        litter.weaned_count = payload.weaned_count
    if payload.notes is not None:
        litter.notes = payload.notes

    db.commit()
    db.refresh(litter)
    return litter


@router.get("/{litter_id}/kits", response_model=list[schemas.AnimalOut])
def list_kits_for_litter(litter_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Animal)
        .filter(models.Animal.litter_id == litter_id)
        .order_by(models.Animal.animal_id.asc())
        .all()
    )


@router.post("/{litter_id}/generate-kits", response_model=schemas.GenerateKitsResponse)
def generate_kits(litter_id: int, payload: schemas.GenerateKitsRequest, db: Session = Depends(get_db)):
    litter = db.get(models.Litter, litter_id)
    if not litter:
        raise HTTPException(404, "Litter not found")

    litter.weaned_count = payload.weaned_count

    prefix = payload.tattoo_prefix or f"L{litter_id}-"

    m = payload.male_count or 0
    f = payload.female_count or 0
    u = payload.weaned_count - (m + f)
    sexes = ("M" * m) + ("F" * f) + ("U" * u)

    existing = (
        db.query(models.Animal)
        .filter(models.Animal.litter_id == litter_id)
        .count()
    )
    start_index = existing + 1

    created_ids: list[int] = []
    created_tattoos: list[str] = []

    try:
        for i in range(payload.weaned_count):
            n = start_index + i
            tattoo = f"{prefix}K{n:02d}"

            animal = models.Animal(
                tattoo=tattoo,
                sex=sexes[i],
                status=payload.status,
                birth_date=litter.kindling_date,
                litter_id=litter_id,
                source="generated",
                notes=f"Generated from litter {litter_id} at weaning",
            )

            db.add(animal)
            db.flush()
            created_ids.append(animal.animal_id)
            created_tattoos.append(tattoo)

        db.commit()
        return schemas.GenerateKitsResponse(
            litter_id=litter_id,
            created=payload.weaned_count,
            animal_ids=created_ids,
            tattoos=created_tattoos,
        )
    except Exception:
        db.rollback()
        raise
