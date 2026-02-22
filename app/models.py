from __future__ import annotations

from sqlalchemy import Column, Integer, String, Date, Float, Text, ForeignKey
from .database import Base


class Animal(Base):
    __tablename__ = "animals"

    animal_id = Column(Integer, primary_key=True, index=True)
    tattoo = Column(String, unique=True, nullable=False)
    sex = Column(String, nullable=False)
    breed = Column(String)
    color = Column(String)
    birth_date = Column(Date)
    source = Column(String)
    status = Column(String, nullable=False)
    litter_id = Column(Integer, ForeignKey("litters.litter_id"), nullable=True)
    death_date = Column(Date)
    death_reason = Column(Text)
    notes = Column(Text)


class Breeding(Base):
    __tablename__ = "breedings"

    breeding_id = Column(Integer, primary_key=True, index=True)
    doe_id = Column(Integer, ForeignKey("animals.animal_id"), nullable=False)
    buck_id = Column(Integer, ForeignKey("animals.animal_id"), nullable=False)
    bred_date = Column(Date, nullable=False)
    expected_kindling = Column(Date)
    result = Column(String, default="pending")  # pending/successful/missed
    notes = Column(Text)


class Litter(Base):
    __tablename__ = "litters"

    litter_id = Column(Integer, primary_key=True, index=True)
    breeding_id = Column(Integer, ForeignKey("breedings.breeding_id"), nullable=False)
    kindling_date = Column(Date, nullable=False)
    born_alive = Column(Integer, nullable=False)
    born_dead = Column(Integer, default=0)
    weaned_count = Column(Integer)
    notes = Column(Text)


class Harvest(Base):
    __tablename__ = "harvests"

    harvest_id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.animal_id"), nullable=False)
    harvest_date = Column(Date, nullable=False)
    live_weight_grams = Column(Integer)
    carcass_weight_grams = Column(Integer)
    notes = Column(Text)


class FeedCost(Base):
    __tablename__ = "feed_costs"

    feed_cost_id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=True)
    cost_per_unit = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=False)


class Sale(Base):
    __tablename__ = "sales"

    sale_id = Column(Integer, primary_key=True, index=True)

    # Exactly one of animal_id or litter_id must be set
    animal_id = Column(Integer, ForeignKey("animals.animal_id"), nullable=True)
    litter_id = Column(Integer, ForeignKey("litters.litter_id"), nullable=True)

    sale_date = Column(Date, nullable=False)
    sale_price = Column(Float, nullable=False)
    buyer_name = Column(String, nullable=True)
    buyer_contact = Column(String, nullable=True)  # phone, email, address, etc.
    notes = Column(Text, nullable=True)
