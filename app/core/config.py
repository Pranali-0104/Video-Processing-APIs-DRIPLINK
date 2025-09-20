# app/core/config.py

import os

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Admin@localhost:5432/fastapi_db")

settings = Settings()