# create_db.py

from app.database import engine, Base
from app.models import models  # Import your models to ensure they are registered with the Base

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created.")