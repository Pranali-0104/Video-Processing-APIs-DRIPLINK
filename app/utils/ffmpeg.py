import subprocess
import json
import os

from pathlib import Path
from typing import Dict, Any
from app.database import SessionLocal
from app.models.models import Job, JobStatus,Video


from app.models.models import Overlay, JobType
from sqlalchemy.orm import Session
from app.core.config import settings



def get_video_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Retrieves video duration and size using ffprobe.
    """
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size",
        "-of", "json",
        str(file_path)
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        
        duration = float(metadata['format']['duration'])
        size = int(metadata['format']['size'])
        
        return {"duration": duration, "size": size}
    except (subprocess.CalledProcessError, FileNotFoundError, KeyError) as e:
        raise RuntimeError(f"Failed to get video metadata for {file_path}: {e}")
    
def trim_video_in_background(job_id: int, input_path: str):
    """
    Executes the FFmpeg trimming command and updates job status.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.processing
        db.commit()

        # Get the original video details
        original_video = job.video
        if not original_video:
            job.status = JobStatus.failed
            db.commit()
            return
            
        # Define output paths and filenames
        output_dir = "processed"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"trimmed_{job.id}_{original_video.filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        # FFmpeg command
        command = [
            "ffmpeg",
            "-ss", str(job.start_time),
            "-i", input_path,
            "-to", str(job.end_time),
            "-c", "copy",
            output_path
        ]
        
        subprocess.run(command, check=True)

        # 1. Insert new row in videos table
        new_video = Video(
            filename=output_filename,
            size=os.path.getsize(output_path),
            duration=job.end_time - job.start_time,
            original_video_id=original_video.id
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

        # 2. Update jobs table
        job.status = JobStatus.done
        job.output_file = output_path
        db.commit()

    except subprocess.CalledProcessError as e:
        db.rollback()
        job.status = JobStatus.failed
        db.commit()
        print(f"FFmpeg command failed with error: {e}")
    finally:
        db.close()

def add_overlay_in_background(job_id: int, input_path: str):
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

        # --- Corrected logic for position ---
        # Using more reliable FFmpeg expressions to avoid misplacement on portrait videos.
        # 'w' and 'h' refer to the input video dimensions
        # 'tw' and 'th' refer to the text width and height
        # Expressions can be used directly in the filter string
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
        
        # Build the drawtext filter string
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