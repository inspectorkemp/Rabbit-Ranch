from __future__ import annotations

from datetime import date
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator


class AnimalCreate(BaseModel):
    tattoo: str
    sex: str = Field(pattern=r"^(M|F|U)$")
    status: str
    breed: Optional[str] = None
    color: Optional[str] = None
    birth_date: Optional[date] = None
    source: Optional[str] = None
    litter_id: Optional[int] = None
    death_date: Optional[date] = None
    death_reason: Optional[str] = None
    notes: Optional[str] = None


class AnimalOut(AnimalCreate):
    animal_id: int

    class Config:
        from_attributes = True


class AnimalStatusUpdate(BaseModel):
    status: str
    death_date: Optional[date] = None
    death_reason: Optional[str] = None


class BreedingCreate(BaseModel):
    doe_id: int
    buck_id: int
    bred_date: date


class BreedingUpdate(BaseModel):
    result: Optional[str] = None   # pending / successful / missed
    notes: Optional[str] = None


class BreedingOut(BaseModel):
    breeding_id: int
    doe_id: int
    buck_id: int
    bred_date: date
    expected_kindling: Optional[date]
    result: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class LitterCreate(BaseModel):
    breeding_id: int
    kindling_date: date
    born_alive: int
    born_dead: int = 0
    weaned_count: Optional[int] = None
    notes: Optional[str] = None


class LitterUpdate(BaseModel):
    kindling_date: Optional[date] = None
    born_alive: Optional[int] = Field(default=None, ge=0)
    born_dead: Optional[int] = Field(default=None, ge=0)
    weaned_count: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class LitterOut(LitterCreate):
    litter_id: int

    class Config:
        from_attributes = True


class HarvestCreate(BaseModel):
    animal_id: int
    harvest_date: date
    live_weight_grams: Optional[int] = None
    carcass_weight_grams: Optional[int] = None
    notes: Optional[str] = None


class HarvestUpdate(BaseModel):
    harvest_date: Optional[date] = None
    live_weight_grams: Optional[int] = Field(default=None, ge=0)
    carcass_weight_grams: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class HarvestOut(HarvestCreate):
    harvest_id: int

    class Config:
        from_attributes = True


class OptionItem(BaseModel):
    id: int
    label: str


class GenerateKitsRequest(BaseModel):
    weaned_count: int = Field(ge=1, le=50)
    male_count: Optional[int] = Field(default=None, ge=0)
    female_count: Optional[int] = Field(default=None, ge=0)
    status: str = "growout"
    tattoo_prefix: Optional[str] = None

    @model_validator(mode="after")
    def validate_counts(self):
        m = self.male_count or 0
        f = self.female_count or 0
        if m + f > self.weaned_count:
            raise ValueError("male_count + female_count cannot exceed weaned_count")
        return self


class GenerateKitsResponse(BaseModel):
    litter_id: int
    created: int
    animal_ids: List[int]
    tattoos: List[str]


# -----------------------------
# Feed Costs
# -----------------------------

class FeedCostCreate(BaseModel):
    date: date
    description: Optional[str] = None
    cost_per_unit: Optional[float] = Field(default=None, ge=0)
    total_cost: float = Field(ge=0)


class FeedCostOut(FeedCostCreate):
    feed_cost_id: int

    class Config:
        from_attributes = True


# -----------------------------
# Sales
# -----------------------------

class SaleCreate(BaseModel):
    sale_date: date
    sale_price: float = Field(ge=0)
    buyer_name: Optional[str] = None
    buyer_contact: Optional[str] = None
    notes: Optional[str] = None
    # Exactly one of these must be provided
    animal_id: Optional[int] = None
    litter_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_subject(self):
        has_animal = self.animal_id is not None
        has_litter = self.litter_id is not None
        if has_animal and has_litter:
            raise ValueError("Provide animal_id or litter_id, not both")
        if not has_animal and not has_litter:
            raise ValueError("One of animal_id or litter_id is required")
        return self


class SaleOut(BaseModel):
    sale_id: int
    sale_date: date
    sale_price: float
    buyer_name: Optional[str] = None
    buyer_contact: Optional[str] = None
    notes: Optional[str] = None
    animal_id: Optional[int] = None
    litter_id: Optional[int] = None

    class Config:
        from_attributes = True
