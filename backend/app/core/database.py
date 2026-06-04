# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

# For local development, we use SQLite. In production, this should be a PostgreSQL URL.
SQLALCHEMY_DATABASE_URL = "sqlite:///./insightx.db"

# connect_args={"check_same_thread": False} is required ONLY for SQLite in FastAPI
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All database models will inherit from this Base class
Base = declarative_base()

def get_db() -> Generator:
    """
    Dependency to yield a database session for a single request, 
    ensuring it is safely closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()