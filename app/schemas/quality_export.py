from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.models.models import VideoQuality

class QualityExportCreate(BaseModel):
    quality: VideoQuality

class VideoVersionResponse(BaseModel):
    id: int
    video_id: int
    quality: VideoQuality # This should correctly handle the enum to string conversion
    file_path: str

    model_config = ConfigDict(from_attributes=True)