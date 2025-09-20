from fastapi import FastAPI
from app.api.api import api_router

# Create the main FastAPI application instance
app = FastAPI(
    title="Video Processing API",
    description="A microservice for handling and processing videos."
)

# Include the main API router
app.include_router(api_router, prefix="/api/v1")