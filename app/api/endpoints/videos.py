import os
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.job import JobResponse, TrimJobCreate
from app.schemas.video import VideoResponse
from app.models.models import Video, Job, JobType, JobStatus
from app.utils.ffmpeg import get_video_metadata, trim_video_in_background, upload_video_task
from app.crud.job import create_trim_job
from app.crud.video import get_videos
from app.dependencies import get_db


from app.schemas.quality_export import QualityExportCreate
from app.utils.ffmpeg import quality_export_in_background


UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

router = APIRouter(
    prefix="/videos",
    tags=["videos"]
)

@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if file.filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is missing.")
    
    db_job = Job(job_type=JobType.upload, status=JobStatus.pending)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    temp_filename = f"temp_upload_{db_job.id}_{file.filename}"
    temp_path = UPLOAD_FOLDER / temp_filename
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        db_job.status = JobStatus.failed
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save video file: {e}"
        )
    
    background_tasks.add_task(upload_video_task, db_job.id, str(temp_path))

    return db_job

@router.get("/", response_model=List[VideoResponse], summary="List all uploaded videos")
def list_videos(db: Session = Depends(get_db)):
    """
    Retrieves all video metadata from the database.
    """
    videos = get_videos(db)
    return videos

@router.post(
    "/{video_id}/trim",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trimming job for a video"
)
def create_trim_job_api(
    video_id: int,
    trim_data: TrimJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    if trim_data.start_time >= trim_data.end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_time must be less than end_time.")

    db_job = create_trim_job(db=db, video_id=video_id, trim_data=trim_data)
    
    input_path = os.path.join("uploads", video.filename)

    background_tasks.add_task(trim_video_in_background, db_job.id, input_path)

    return db_job

# app/api/endpoints/videos.py
# ... (existing imports and other endpoints) ...
from app.schemas.quality_export import QualityExportCreate

@router.post(
    "/{video_id}/quality-export",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a quality export job for a video"
)
def create_quality_export_job(
    video_id: int,
    quality_data: QualityExportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    db_job = Job(
        video_id=video_id,
        job_type=JobType.quality_export,
        status=JobStatus.pending
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    background_tasks.add_task(
        quality_export_in_background,
        job_id=db_job.id,
        input_video_id=video_id,
        quality=quality_data.quality
    )

    return db_job

# app/api/endpoints/videos.py
# ... (existing imports and endpoints) ...
from app.models.models import VideoVersion
from app.schemas.quality_export import VideoVersionResponse

@router.get(
    "/{video_id}/versions",
    response_model=List[VideoVersionResponse],
    summary="List all quality versions for a video"
)
def list_video_versions(
    video_id: int,
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        
    versions = db.query(VideoVersion).filter(VideoVersion.video_id == video_id).all()
    return versions