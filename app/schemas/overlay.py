from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.models import OverlayType

class OverlayBase(BaseModel):
    type: OverlayType
    content: str
    position: str
    start_time: float
    end_time: float

class OverlayCreate(OverlayBase):
    pass

class OverlayResponse(OverlayBase):
    id: int
    video_id: int

    model_config = ConfigDict(from_attributes=True)