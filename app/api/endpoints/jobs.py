# app/api/endpoints/jobs.py

import os
from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.models import Video, Job, JobType,JobStatus 
from app.schemas.job import TrimJobCreate, JobResponse
from app.crud.job import create_trim_job
from app.utils.ffmpeg import trim_video_in_background
from fastapi.responses import FileResponse

router = APIRouter(
    tags=["jobs"]
)

@router.post(
    "/videos/{video_id}/trim",
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if trim_data.start_time >= trim_data.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be less than end_time."
        )

    # We only need to pass the job ID and the full file path to the background task
    # The background task will fetch the job details (start/end time) itself
    db_job = create_trim_job(db=db, video_id=video_id, trim_data=trim_data)
    
    input_path = os.path.join("uploads", video.filename)

    background_tasks.add_task(
        trim_video_in_background,
        job_id=db_job.id,
        input_path=input_path
    )

    return db_job

@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get the status of a specific job"
)
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves the details and current status of a video processing job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job

@router.get(
    "/jobs/{job_id}/result",
    summary="Get the result of a completed job"
)
def get_job_result(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns the processed video file for a completed job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found."
        )

    if job.status != JobStatus.done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job status is '{job.status.value}', not 'done'."
        )

    if not job.output_file or not os.path.exists(job.output_file):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed file not found."
        )

    return FileResponse(path=job.output_file, media_type="video/mp4", filename=os.path.basename(job.output_file))