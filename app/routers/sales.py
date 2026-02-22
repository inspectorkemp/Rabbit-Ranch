from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/", response_model=list[schemas.SaleOut])
def list_sales(db: Session = Depends(get_db)):
    return (
        db.query(models.Sale)
        .order_by(models.Sale.sale_date.desc())
        .all()
    )


@router.post("/", response_model=schemas.SaleOut)
def create_sale(payload: schemas.SaleCreate, db: Session = Depends(get_db)):
    # --- Individual animal sale ---
    if payload.animal_id is not None:
        animal = db.get(models.Animal, payload.animal_id)
        if not animal:
            raise HTTPException(404, "Animal not found")
        if animal.status in ("harvested", "deceased"):
            raise HTTPException(
                400,
                f"Cannot sell an animal with status '{animal.status}'"
            )

        sale = models.Sale(**payload.model_dump())
        animal.status = "sold"
        db.add(sale)
        db.commit()
        db.refresh(sale)
        return sale

    # --- Whole litter sale ---
    litter = db.get(models.Litter, payload.litter_id)
    if not litter:
        raise HTTPException(404, "Litter not found")

    kits = (
        db.query(models.Animal)
        .filter(models.Animal.litter_id == payload.litter_id)
        .all()
    )
    if not kits:
        raise HTTPException(
            400,
            "No animals found for this litter. Generate kits first."
        )

    ineligible = [a for a in kits if a.status in ("harvested", "deceased")]
    if ineligible:
        tattoos = ", ".join(a.tattoo for a in ineligible)
        raise HTTPException(
            400,
            f"Cannot sell litter — some animals are already harvested or deceased: {tattoos}"
        )

    sale = models.Sale(**payload.model_dump())
    for kit in kits:
        kit.status = "sold"

    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


@router.delete("/{sale_id}", status_code=204)
def delete_sale(sale_id: int, db: Session = Depends(get_db)):
    sale = db.get(models.Sale, sale_id)
    if not sale:
        raise HTTPException(404, "Sale not found")

    # Revert animal status back to appropriate value
    if sale.animal_id is not None:
        animal = db.get(models.Animal, sale.animal_id)
        if animal and animal.status == "sold":
            # Best guess: breeders go back to breeder, others to growout
            animal.status = "breeder" if animal.sex in ("F", "M") and animal.litter_id is None else "growout"

    if sale.litter_id is not None:
        kits = (
            db.query(models.Animal)
            .filter(models.Animal.litter_id == sale.litter_id)
            .all()
        )
        for kit in kits:
            if kit.status == "sold":
                kit.status = "growout"

    db.delete(sale)
    db.commit()
