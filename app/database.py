# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Create a database engine
engine = create_engine(settings.DATABASE_URL)

# Create a base class for declarative models
Base = declarative_base()

# Create a SessionLocal class to be used as a dependency in FastAPI
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)