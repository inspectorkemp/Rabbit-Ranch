from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/feed-costs", tags=["feed-costs"])


@router.get("/", response_model=list[schemas.FeedCostOut])
def list_feed_costs(db: Session = Depends(get_db)):
    return (
        db.query(models.FeedCost)
        .order_by(models.FeedCost.date.desc())
        .all()
    )


@router.post("/", response_model=schemas.FeedCostOut)
def create_feed_cost(payload: schemas.FeedCostCreate, db: Session = Depends(get_db)):
    entry = models.FeedCost(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{feed_cost_id}", status_code=204)
def delete_feed_cost(feed_cost_id: int, db: Session = Depends(get_db)):
    entry = db.get(models.FeedCost, feed_cost_id)
    if not entry:
        raise HTTPException(404, "Feed cost entry not found")
    db.delete(entry)
    db.commit()
