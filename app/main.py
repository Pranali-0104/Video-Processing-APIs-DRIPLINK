from fastapi import FastAPI
from app.api.api import api_router

app = FastAPI(
    title="Video Processing API",
    description="A microservice for handling and processing videos."
)

app.include_router(api_router, prefix="/api/v1")