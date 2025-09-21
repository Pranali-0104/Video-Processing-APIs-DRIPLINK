# app/api/api.py

from fastapi import APIRouter
from app.api.endpoints import videos, jobs, overlays, video_versions

api_router = APIRouter()
api_router.include_router(videos.router)
api_router.include_router(jobs.router)
api_router.include_router(overlays.router)
api_router.include_router(video_versions.router)