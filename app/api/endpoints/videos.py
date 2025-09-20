import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.job import TrimJobCreate

from app.models.models import Video
from app.schemas.video import VideoCreate, VideoResponse
from app.dependencies import get_db
from app.utils.ffmpeg import get_video_metadata
from app.schemas.job import JobResponse

# Define the directory where videos will be stored
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

router = APIRouter(
    prefix="/videos",
    tags=["videos"]
)

@router.post("/upload", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile,
    db: Session = Depends(get_db)
):
    """
    Uploads a video, saves it to disk, and stores its metadata in the database.
    """
    if not file.filename.endswith(('.mp4', '.mov', '.avi', '.mkv')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only video formats are supported."
        )

    # 1. Save the video file to disk
    file_path = UPLOAD_FOLDER / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save video file: {e}"
        )

    # 2. Get video metadata using FFmpeg
    try:
        metadata = get_video_metadata(file_path)
    except RuntimeError as e:
        os.remove(file_path) # Clean up file if metadata extraction fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    # 3. Save metadata to the database
    db_video = Video(
        filename=file.filename,
        size=metadata['size'],
        duration=metadata['duration'],
        upload_time=datetime.now()
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)

    return db_video

# ... (existing imports) ...
from app.tasks import trim_video_task # <-- New import

@router.post(
    "/{video_id}/trim",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trimming job for a video"
)
def create_trim_job_api(
    video_id: int,
    trim_data: TrimJobCreate,
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    if trim_data.start_time >= trim_data.end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_time must be less than end_time.")

    db_job = create_trim_job(db=db, video_id=video_id, trim_data=trim_data)
    
    input_path = os.path.join("uploads", video.filename)

    # Call the Celery task instead of BackgroundTasks
    trim_video_task.delay(db_job.id, input_path)

    return db_job

# app/api/endpoints/videos.py

import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

# ... (existing imports) ...
from app.models.models import Video, Job, JobType, JobStatus
from app.schemas.video import VideoCreate, VideoResponse
from app.schemas.job import JobResponse
from app.tasks import upload_video_task # <-- New import
from app.crud.job import create_trim_job
from app.utils.ffmpeg import get_video_metadata, trim_video_in_background

# ... (existing router and other endpoints) ...

@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile,
    db: Session = Depends(get_db)
):
    if file.filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is missing.")
    
    # 1. Create a new upload job
    db_job = Job(job_type=JobType.upload, status=JobStatus.pending)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    # 2. Save the file to a temporary location
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
    
    # 3. Kick off the Celery task
    upload_video_task.delay(db_job.id, str(temp_path))

    return db_job