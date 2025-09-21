# 🎥 Video Processing APIs (FastAPI)

This project is a FastAPI microservice for a video editing platform. It handles video uploads, performs various processing tasks (trimming, overlays, quality exports) asynchronously using FFmpeg, and manages metadata with a PostgreSQL database.

## ✨ Features

- **Level 1: Upload & Metadata**
  - `POST /videos/upload`: Uploads a video file.
  - `GET /videos/`: Lists all uploaded videos with their metadata.

- **Level 2: Trimming**
  - `POST /videos/{video_id}/trim`: Creates an asynchronous job to trim a video to a specific duration.

- **Level 3: Overlays & Watermarking**
  - `POST /overlays/{video_id}`: Adds text, image, or video overlays with configurable position and timing.
  - Supports adding a watermark (a type of image overlay).

- **Level 4: Async Job Queue**
  - All processing jobs (upload, trim, overlay) are handled asynchronously using FastAPI's `BackgroundTasks`.
  - `GET /jobs/{job_id}`: Retrieves the current status of a job.
  - `GET /jobs/{job_id}/result`: Downloads the final processed video file.

- **Level 5: Multiple Output Qualities**
  - `POST /videos/{video_id}/quality-export`: Generates a new video version in 1080p, 720p, or 480p.
  - `GET /video-versions/{video_version_id}/download`: Fetches and downloads a specific quality version.

## 🚀 Getting Started

Follow these steps to get the project up and running locally.

### Prerequisites

- **Python 3.10+**
- **PostgreSQL Database**
- **FFmpeg:** Installed and added to your system's PATH.

### 1. Setup

1.  **Clone the repository:**
    ```bash
    git clone [your_repo_link]
    cd [your_repo_name]
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    venv\Scripts\activate      # Windows
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Database Configuration

1.  Create a PostgreSQL database named `fastapi_db`.
2.  Run the `create_db.py` script to create the necessary tables.
    ```bash
    python create_db.py
    ```

### 3. Run the Application

Start the FastAPI server from the project's root directory:
```bash
uvicorn app.main:app --reload
