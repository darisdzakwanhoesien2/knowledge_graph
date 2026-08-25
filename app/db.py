"""Shared SQLModel engine and session dependency.

The database URL defaults to the local knowledge.db and can be overridden with
KG_DATABASE_URL (used by tests to isolate from real data).
"""
import os

from sqlmodel import Session, create_engine

DATABASE_URL = os.environ.get("KG_DATABASE_URL", "sqlite:///database/knowledge.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def get_session():
    with Session(engine) as session:
        yield session
