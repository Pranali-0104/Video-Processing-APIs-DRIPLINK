from sqlalchemy.orm import Session
from app.models.models import Video

def get_videos(db: Session):
    return db.query(Video).all()

