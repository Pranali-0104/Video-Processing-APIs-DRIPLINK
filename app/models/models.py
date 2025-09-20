# app/models/models.py

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum, Float, Text
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Float

from app.database import Base

# --- Enums for specific fields ---
class JobType(enum.Enum):
    upload = "upload"
    trim = "trim"
    overlay = "overlay"
    watermark = "watermark"
    quality_export = "quality_export"

class JobStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"

class OverlayType(enum.Enum):
    text = "text"
    image = "image"
    video = "video"
    watermark = "watermark"

class VideoQuality(enum.Enum):
    p1080 = "1080p"
    p720 = "720p"
    p480 = "480p"

# --- Models ---
class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    filename = Column(String, index=True)
    duration = Column(Float)
    size = Column(Integer)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    original_video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)

    # Relationships
    jobs = relationship("Job", back_populates="video")
    overlays = relationship("Overlay", back_populates="video")
    video_versions = relationship("VideoVersion", back_populates="video")
    # For trimmed videos linking back to the original
    original_video = relationship("Video", remote_side=[id])

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    job_type = Column(Enum(JobType), default=JobType.upload)
    status = Column(Enum(JobStatus), default=JobStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    output_file = Column(String, nullable=True)
    start_time = Column(Float, nullable=True)  # <-- NEW
    end_time = Column(Float, nullable=True)    # <-- NEW

    video = relationship("Video", back_populates="jobs")

class Overlay(Base):
    __tablename__ = "overlays"

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    type = Column(Enum(OverlayType))
    content = Column(Text)
    position = Column(String)  # You can use a specific type for x,y if needed
    start_time = Column(Float)
    end_time = Column(Float)

    # Relationship
    video = relationship("Video", back_populates="overlays")

class VideoVersion(Base):
    __tablename__ = "video_versions"

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    quality = Column(Enum(VideoQuality))
    file_path = Column(String)

    # Relationship
    video = relationship("Video", back_populates="video_versions")