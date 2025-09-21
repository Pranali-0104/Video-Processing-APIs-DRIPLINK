🎥 Video Processing APIs (FastAPI)
This project is a FastAPI microservice for a video editing platform. It handles video uploads, performs various processing tasks (trimming, overlays, quality exports) asynchronously using FFmpeg, and manages metadata with a PostgreSQL database.

✨ Features
Level 1: Upload & Metadata

POST /videos/upload: Uploads a video file.

GET /videos/: Lists all uploaded videos with their metadata.

Level 2: Trimming

POST /videos/{video_id}/trim: Creates an asynchronous job to trim a video to a specific duration.

Level 3: Overlays & Watermarking

POST /overlays/{video_id}: Adds text, image, or video overlays with configurable position and timing.

Supports adding a watermark (a type of image overlay).

Level 4: Async Job Queue

All processing jobs (upload, trim, overlay) are handled asynchronously using FastAPI's BackgroundTasks.

GET /jobs/{job_id}: Retrieves the current status of a job.

GET /jobs/{job_id}/result: Downloads the final processed video file.

Level 5: Multiple Output Qualities

POST /videos/{video_id}/quality-export: Generates a new video version in 1080p, 720p, or 480p.

GET /video-versions/{video_version_id}/download: Fetches and downloads a specific quality version.

🚀 Getting Started
Follow these steps to get the project up and running locally.

Prerequisites
Python 3.10+

PostgreSQL Database

FFmpeg: Installed and added to your system's PATH.

1. Setup
Clone the repository:

git clone [your_repo_link]
cd [your_repo_name]

Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate      # Windows

Install dependencies:

pip install -r requirements.txt

2. Database Configuration
Create a PostgreSQL database named fastapi_db.

Run the create_db.py script to create the necessary tables.

python create_db.py

3. Run the Application
Start the FastAPI server from the project's root directory:

uvicorn app.main:app --reload

The application will be running at http://127.0.0.1:8000.

4. How to Test
You can interact with all the API endpoints using the interactive documentation at:
http://127.0.0.1:8000/docs

Note: Due to the asynchronous nature of the app, after submitting a job (e.g., trim or overlay), you must use the GET /jobs/{job_id} endpoint to check its status before attempting to download the result.

Example Workflow:

Upload: POST /videos/upload (Save the returned job_id).

Process: POST /videos/{video_id}/trim (Save the returned job_id).

Check Status: GET /jobs/{job_id} (Wait for status to be "done").

Download: GET /jobs/{job_id}/result.

🎬 Demo Video & Documentation
Demo Video: [https://drive.google.com/drive/folders/1xV_nsoJszw6hV_NWUyVwsEmMKr9OvKJv]

OpenAPI Docs: [http://127.0.0.1:8000/openapi.json]
