import os
from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.models import Video, Job, JobType,JobStatus
from app.schemas.overlay import OverlayCreate, OverlayResponse
from app.schemas.job import JobResponse
from app.crud.overlay import create_overlay
from app.utils.ffmpeg import add_overlay_in_background

router = APIRouter(
    tags=["overlays"]
)

@router.post(
    "/videos/{video_id}/overlay",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an overlay job for a video"
)
def create_overlay_job(
    video_id: int,
    overlay_data: OverlayCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found."
        )

    db_job = Job(video_id=video_id, job_type=JobType.overlay, status=JobStatus.pending)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    # Store overlay configuration
    create_overlay(db, video_id=video_id, overlay_data=overlay_data)

    input_path = os.path.join("uploads", video.filename)
    
    background_tasks.add_task(
        add_overlay_in_background,
        job_id=db_job.id,
        input_path=input_path
    )
    
    return db_job

# ... (existing imports) ...
from app.tasks import add_overlay_task # <-- New import

@router.post(
    "/{video_id}",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an overlay job for a video"
)
def create_overlay_job(
    video_id: int,
    overlay_data: OverlayCreate,
    db: Session = Depends(get_db) # Removed BackgroundTasks
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found."
        )

    db_job = Job(video_id=video_id, job_type=JobType.overlay, status=JobStatus.pending)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    create_overlay(db, video_id=video_id, overlay_data=overlay_data)

    input_path = os.path.join("uploads", video.filename)
    
    # Call the Celery task instead of BackgroundTasks
    add_overlay_task.delay(db_job.id, input_path)
    
    return db_job

# app/api/endpoints/overlays.py

# ... (existing imports) ...
from app.tasks import add_overlay_task # <-- New import

@router.post(
    "/{video_id}",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an overlay job for a video"
)
def create_overlay_job(
    video_id: int,
    overlay_data: OverlayCreate,
    db: Session = Depends(get_db) # Removed BackgroundTasks
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found."
        )

    db_job = Job(video_id=video_id, job_type=JobType.overlay, status=JobStatus.pending)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    create_overlay(db, video_id=video_id, overlay_data=overlay_data)

    input_path = os.path.join("uploads", video.filename)
    
    # Call the Celery task instead of BackgroundTasks
    add_overlay_task.delay(db_job.id, input_path)
    
    return db_job