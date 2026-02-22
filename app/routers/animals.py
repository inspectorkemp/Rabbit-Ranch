from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/animals", tags=["animals"])


@router.post("/", response_model=schemas.AnimalOut)
def create_animal(payload: schemas.AnimalCreate, db: Session = Depends(get_db)):
    animal = models.Animal(**payload.model_dump())
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return animal


@router.get("/", response_model=list[schemas.AnimalOut])
def list_animals(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Animal)
    if status:
        q = q.filter(models.Animal.status == status)
    return q.order_by(models.Animal.animal_id.asc()).offset(skip).limit(limit).all()


@router.get("/{animal_id}", response_model=schemas.AnimalOut)
def get_animal(animal_id: int, db: Session = Depends(get_db)):
    animal = db.get(models.Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    return animal


@router.patch("/{animal_id}", response_model=schemas.AnimalOut)
def update_animal_status(
    animal_id: int,
    payload: schemas.AnimalStatusUpdate,
    db: Session = Depends(get_db),
):
    animal = db.get(models.Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")

    # Prevent bypassing harvest workflow
    if payload.status == "harvested":
        raise HTTPException(400, "Use /harvests to mark an animal harvested")

    animal.status = payload.status

    if payload.status == "deceased":
        animal.death_date = payload.death_date or date.today()
        animal.death_reason = payload.death_reason
    else:
        animal.death_date = None
        animal.death_reason = None

    db.commit()
    db.refresh(animal)
    return animal


@router.delete("/{animal_id}", status_code=204)
def delete_animal(animal_id: int, db: Session = Depends(get_db)):
    """
    Hard-delete an animal record.

    Guards:
    - Cannot delete an animal that is the doe or buck on any breeding.
    - Cannot delete an animal that has a harvest record.
    - Cannot delete an animal that is a parent via litter_id kit rows
      (delete the kits first).
    """
    animal = db.get(models.Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")

    # Block if referenced by a breeding
    breeding_ref = (
        db.query(models.Breeding)
        .filter(
            (models.Breeding.doe_id == animal_id)
            | (models.Breeding.buck_id == animal_id)
        )
        .first()
    )
    if breeding_ref:
        raise HTTPException(
            409,
            f"Animal {animal_id} is referenced by breeding {breeding_ref.breeding_id}. "
            "Remove or reassign the breeding first.",
        )

    # Block if referenced by a harvest
    harvest_ref = (
        db.query(models.Harvest)
        .filter(models.Harvest.animal_id == animal_id)
        .first()
    )
    if harvest_ref:
        raise HTTPException(
            409,
            f"Animal {animal_id} has a harvest record ({harvest_ref.harvest_id}). "
            "Delete the harvest first.",
        )

    db.delete(animal)
    db.commit()
