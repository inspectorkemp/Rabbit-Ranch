from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/breedings", tags=["breedings"])


@router.post("/", response_model=schemas.BreedingOut)
def create_breeding(payload: schemas.BreedingCreate, db: Session = Depends(get_db)):
    doe = db.get(models.Animal, payload.doe_id)
    buck = db.get(models.Animal, payload.buck_id)

    if not doe or doe.sex != "F":
        raise HTTPException(400, "Invalid doe")
    if not buck or buck.sex != "M":
        raise HTTPException(400, "Invalid buck")

    breeding = models.Breeding(
        doe_id=payload.doe_id,
        buck_id=payload.buck_id,
        bred_date=payload.bred_date,
        expected_kindling=payload.bred_date + timedelta(days=31),
        result="pending",
    )

    db.add(breeding)
    db.commit()
    db.refresh(breeding)
    return breeding


@router.get("/", response_model=list[schemas.BreedingOut])
def list_breedings(db: Session = Depends(get_db)):
    return db.query(models.Breeding).order_by(models.Breeding.bred_date.desc()).all()


@router.patch("/{breeding_id}", response_model=schemas.BreedingOut)
def update_breeding(breeding_id: int, payload: schemas.BreedingUpdate, db: Session = Depends(get_db)):
    breeding = db.get(models.Breeding, breeding_id)
    if not breeding:
        raise HTTPException(404, "Breeding not found")

    # Only update fields that were actually provided
    if payload.result is not None:
        allowed = {"pending", "successful", "missed"}
        if payload.result not in allowed:
            raise HTTPException(400, f"result must be one of: {', '.join(sorted(allowed))}")
        breeding.result = payload.result

    if payload.notes is not None:
        breeding.notes = payload.notes

    db.commit()
    db.refresh(breeding)
    return breeding
