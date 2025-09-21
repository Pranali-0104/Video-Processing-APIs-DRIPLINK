from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.models import JobType, JobStatus

class JobBase(BaseModel):
    video_id: Optional[int]
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