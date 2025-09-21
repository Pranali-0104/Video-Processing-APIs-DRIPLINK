import os
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.models import VideoVersion
from app.schemas.quality_export import VideoVersionResponse
from typing import List

router = APIRouter(
    prefix="/video-versions",
    tags=["video-versions"]
)

@router.get("/{video_version_id}", response_model=VideoVersionResponse, summary="Get a specific video version")
def get_video_version(
    video_version_id: int,
    db: Session = Depends(get_db)
):
    version = db.query(VideoVersion).filter(VideoVersion.id == video_version_id).first()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video version not found.")
    return version

@router.get("/{video_version_id}/download", summary="Download a specific quality version")
def download_video_version(
    video_version_id: int,
    db: Session = Depends(get_db)
):
    version = db.query(VideoVersion).filter(VideoVersion.id == video_version_id).first()
    if not version or not os.path.exists(version.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    return FileResponse(path=version.file_path, media_type="video/mp4", filename=os.path.basename(version.file_path))