# app/schemas/job.py

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.models import JobType, JobStatus
from typing import Optional

class JobBase(BaseModel):
    video_id: int
    job_type: JobType
    status: JobStatus

class TrimJobCreate(BaseModel):
    start_time: float
    end_time: float

class JobResponse(JobBase):
    id: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    output_file: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)