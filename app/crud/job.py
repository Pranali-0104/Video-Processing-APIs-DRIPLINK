from sqlalchemy.orm import Session
from app.models.models import Job, Video, JobType, JobStatus
from app.schemas.job import TrimJobCreate
from fastapi import HTTPException, status

def create_trim_job(db: Session, video_id: int, trim_data: TrimJobCreate):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    db_job = Job(
        video_id=video_id,
        job_type=JobType.trim,
        status=JobStatus.pending,
        start_time=trim_data.start_time,
        end_time=trim_data.end_time
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job