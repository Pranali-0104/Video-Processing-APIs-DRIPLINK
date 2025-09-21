from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.models import OverlayType
import enum

class OverlayPosition(str, enum.Enum):
    top_left = "top-left"
    top_right = "top-right"
    bottom_left = "bottom-left"
    bottom_right = "bottom-right"
    center = "center"

class OverlayCreate(BaseModel):
    type: OverlayType
    content: str
    position: OverlayPosition
    start_time: float
    end_time: float
    font_name: Optional[str] = None

class OverlayResponse(BaseModel):
    id: int
    video_id: int
    type: OverlayType
    content: str
    position: OverlayPosition
    start_time: float
    end_time: float
    font_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
