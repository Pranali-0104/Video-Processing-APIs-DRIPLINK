# app/tasks.py

import os
import subprocess
from pathlib import Path
from sqlalchemy.orm import Session
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.models import Job, JobStatus, Video, Overlay, JobType, VideoQuality
from app.utils.ffmpeg import get_video_metadata

# --- Celery tasks for processing jobs ---

@celery_app.task
def trim_video_task(job_id: int, input_path: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job: return

        job.status = JobStatus.processing
        db.commit()

        original_video = job.video
        if not original_video:
            job.status = JobStatus.failed
            db.commit()
            return
            
        output_dir = "processed"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"trimmed_{job.id}_{original_video.filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        command = [
            "ffmpeg",
            "-ss", str(job.start_time),
            "-i", input_path,
            "-to", str(job.end_time),
            "-c", "copy",
            output_path
        ]
        
        subprocess.run(command, check=True)

        new_video = Video(
            filename=output_filename,
            size=os.path.getsize(output_path),
            duration=job.end_time - job.start_time,
            original_video_id=original_video.id
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

        job.status = JobStatus.done
        job.output_file = output_path
        db.commit()

    except subprocess.CalledProcessError as e:
        db.rollback()
        job.status = JobStatus.failed
        db.commit()
        print(f"FFmpeg command failed: {e}")
    finally:
        db.close()

@celery_app.task
def add_overlay_task(job_id: int, input_path: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.job_type != JobType.overlay:
            return

        job.status = JobStatus.processing
        db.commit()

        overlay_data = db.query(Overlay).filter(Overlay.video_id == job.video_id).first()
        original_video = job.video
        if not original_video or not overlay_data:
            job.status = JobStatus.failed
            db.commit()
            return

        output_dir = "processed"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"overlay_{job.id}_{original_video.filename}"
        output_path = os.path.join(output_dir, output_filename)

        if overlay_data.position == "top-left":
            x_pos, y_pos = "10", "10"
        elif overlay_data.position == "top-right":
            x_pos, y_pos = "w-tw-10", "10"
        elif overlay_data.position == "bottom-left":
            x_pos, y_pos = "10", "h-th-10"
        elif overlay_data.position == "bottom-right":
            x_pos, y_pos = "w-tw-10", "h-th-10"
        else: # Default to center
            x_pos, y_pos = "(w-tw)/2", "(h-th)/2"
        
        drawtext_filter = (
            f"drawtext=text='{overlay_data.content}':"
            f"x={x_pos}:y={y_pos}:"
            f"fontsize=36:fontcolor=white:borderw=2:bordercolor=black:"
            f"enable='between(t,{overlay_data.start_time},{overlay_data.end_time})'"
        )

        command = [
            "ffmpeg",
            "-i", input_path,
            "-vf", drawtext_filter,
            "-c:a", "copy",
            output_path
        ]
        
        subprocess.run(command, check=True)

        new_video = Video(
            filename=output_filename,
            size=os.path.getsize(output_path),
            duration=original_video.duration,
            original_video_id=original_video.id
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

        job.status = JobStatus.done
        job.output_file = output_path
        db.commit()

    except subprocess.CalledProcessError as e:
        db.rollback()
        job.status = JobStatus.failed
        db.commit()
        print(f"FFmpeg command failed: {e}")
    finally:
        db.close()

# ... (existing imports) ...
from app.utils.ffmpeg import get_video_metadata

@celery_app.task
def upload_video_task(job_id: int, file_path: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.processing
        db.commit()

        # Get video metadata using FFmpeg
        try:
            metadata = get_video_metadata(Path(file_path))
        except RuntimeError as e:
            os.remove(file_path)
            job.status = JobStatus.failed
            db.commit()
            print(f"Metadata extraction failed: {e}")
            return

        # Insert new row in videos table
        new_video = Video(
            filename=os.path.basename(file_path),
            size=metadata['size'],
            duration=metadata['duration'],
            original_video_id=None
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

        # Update the job with the new video's ID
        job.video_id = new_video.id
        job.status = JobStatus.done
        job.output_file = file_path
        db.commit()

    except Exception as e:
        db.rollback()
        job.status = JobStatus.failed
        db.commit()
        print(f"Upload task failed: {e}")
    finally:
        db.close()