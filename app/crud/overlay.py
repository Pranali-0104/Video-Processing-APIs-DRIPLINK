from sqlalchemy.orm import Session
from app.models.models import Video, Overlay
from app.schemas.overlay import OverlayCreate
from fastapi import HTTPException, status

def create_overlay(db: Session, video_id: int, overlay_data: OverlayCreate):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found."
        )

    db_overlay = Overlay(**overlay_data.model_dump(), video_id=video_id)
    db.add(db_overlay)
    db.commit()
    db.refresh(db_overlay)
    return db_overlay