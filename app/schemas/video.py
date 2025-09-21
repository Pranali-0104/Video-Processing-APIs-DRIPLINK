from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class VideoBase(BaseModel):
    filename: str
    size: int
    duration: float

class VideoCreate(VideoBase):
    pass

class VideoResponse(VideoBase):
    id: int
    upload_time: datetime
    original_video_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)