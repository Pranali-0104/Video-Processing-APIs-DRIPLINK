# app/api/endpoints/overlays.py

import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException, UploadFile, Form
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.models import Video, Job, JobType, JobStatus, OverlayType
from app.schemas.overlay import OverlayCreate, OverlayResponse, OverlayPosition
from app.schemas.job import JobResponse
from app.crud.overlay import create_overlay
from app.utils.ffmpeg import add_overlay_in_background

# This folder is for the raw overlay files (images, videos)
OVERLAY_MEDIA_FOLDER = Path("overlays_media")
OVERLAY_MEDIA_FOLDER.mkdir(exist_ok=True)

router = APIRouter(
    prefix="/overlays",
    tags=["overlays"]
)

@router.post(
    "/{video_id}",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an overlay job for a video"
)
def create_overlay_job(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    overlay_type: OverlayType = Form(...),
    position: OverlayPosition = Form(...),
    start_time: float = Form(...),
    end_time: float = Form(...),
    content: str | None = Form(None),
    font_name: str | None = Form(None), # <-- NEW PARAMETER
    overlay_file: UploadFile | None = None
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")

    overlay_content = None
    if overlay_type == OverlayType.text:
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content is required for text overlay.")
        overlay_content = content
    elif overlay_type in [OverlayType.image, OverlayType.watermark, OverlayType.video]:
        if not overlay_file:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An overlay file is required.")
        
        file_extension = os.path.splitext(overlay_file.filename)[1]
        overlay_filename = f"overlay_{video_id}_{overlay_type.value}{file_extension}"
        overlay_path = OVERLAY_MEDIA_FOLDER / overlay_filename
        
        with open(overlay_path, "wb") as buffer:
            shutil.copyfileobj(overlay_file.file, buffer)
        
        overlay_content = overlay_filename
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported overlay type.")

    db_job = Job(video_id=video_id, job_type=JobType.overlay, status=JobStatus.pending)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    overlay_data = OverlayCreate(
        type=overlay_type,
        content=overlay_content,
        position=position,
        start_time=start_time,
        end_time=end_time,
        font_name=font_name # <-- PASS NEW PARAMETER
    )
    
    create_overlay(db, video_id=video_id, overlay_data=overlay_data)

    input_path = os.path.join("uploads", video.filename)
    
    background_tasks.add_task(add_overlay_in_background, db_job.id, input_path)
    
    return db_job