from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Production/Docker-ready:
# - Default DB file: ./rabbit_tracker.db (relative to current working directory)
# - Override with env var, e.g.
#     DATABASE_URL=sqlite:////data/rabbit_tracker.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rabbit_tracker.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
