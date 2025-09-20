from fastapi import APIRouter
from app.api.endpoints import videos,jobs,overlays

api_router = APIRouter()
api_router.include_router(videos.router)
api_router.include_router(jobs.router)
api_router.include_router(overlays.router)