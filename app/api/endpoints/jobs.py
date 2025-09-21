import os
from pathlib import Path
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.models import Job, JobStatus
from app.schemas.job import JobResponse

# Define the project root to correctly build file paths
PROJECT_ROOT = Path(__file__).parent.parent.parent

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"]
)

@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get the status of a specific job"
)
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job

@router.get(
    "/{job_id}/result",
    summary="Get the result of a completed job"
)
def get_job_result(
    job_id: int,
    db: Session = Depends(get_db)
):
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
    
    # Construct the absolute path
    file_path = PROJECT_ROOT / job.output_file

    if not job.output_file or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed file not found."
        )

    return FileResponse(path=file_path, media_type="video/mp4", filename=os.path.basename(file_path))
