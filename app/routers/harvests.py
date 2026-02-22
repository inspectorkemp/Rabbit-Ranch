from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/harvests", tags=["harvests"])


@router.get("/", response_model=list[schemas.HarvestOut])
def list_harvests(db: Session = Depends(get_db)):
    return db.query(models.Harvest).order_by(models.Harvest.harvest_date.desc()).all()


@router.post("/", response_model=schemas.HarvestOut)
def record_harvest(payload: schemas.HarvestCreate, db: Session = Depends(get_db)):
    animal = db.get(models.Animal, payload.animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")

    harvest = models.Harvest(**payload.model_dump())
    animal.status = "harvested"

    db.add(harvest)
    db.commit()
    db.refresh(harvest)
    return harvest


@router.patch("/{harvest_id}", response_model=schemas.HarvestOut)
def update_harvest(harvest_id: int, payload: schemas.HarvestUpdate, db: Session = Depends(get_db)):
    harvest = db.get(models.Harvest, harvest_id)
    if not harvest:
        raise HTTPException(404, "Harvest not found")

    if payload.harvest_date is not None:
        harvest.harvest_date = payload.harvest_date
    if payload.live_weight_grams is not None:
        harvest.live_weight_grams = payload.live_weight_grams
    if payload.carcass_weight_grams is not None:
        harvest.carcass_weight_grams = payload.carcass_weight_grams
    if payload.notes is not None:
        harvest.notes = payload.notes

    db.commit()
    db.refresh(harvest)
    return harvest
