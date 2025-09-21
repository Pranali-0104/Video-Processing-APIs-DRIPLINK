import subprocess
import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.models import Job, JobStatus, Video, Overlay, JobType, OverlayType, VideoVersion, VideoQuality
from app.database import SessionLocal
import json

def get_video_metadata(file_path: Path):
    """Retrieves video duration and size using ffprobe."""
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

# This is a temporary function to check for audio stream in a video
def has_audio_stream(file_path: Path) -> bool:
    command = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "json", str(file_path)]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    metadata = json.loads(result.stdout)
    return "streams" in metadata and len(metadata["streams"]) > 0

def trim_video_in_background(job_id: int, input_path: str):
    """Executes the FFmpeg trimming command and updates job status."""
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

def add_overlay_in_background(job_id: int, input_path: str):
    """Executes the FFmpeg overlay command and updates job status."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.job_type != JobType.overlay: return

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

        command = [
            "ffmpeg",
            "-y", # Overwrite output files without asking
            "-i", input_path
        ]
        
        # Determine the position coordinates
        x_pos, y_pos = "", ""
        if overlay_data.position == "top-left":
            x_pos, y_pos = "10", "10"
        elif overlay_data.position == "top-right":
            x_pos, y_pos = "W-w-10", "10"
        elif overlay_data.position == "bottom-left":
            x_pos, y_pos = "10", "H-h-10"
        elif overlay_data.position == "bottom-right":
            x_pos, y_pos = "W-w-10", "H-h-10"
        else: # Default to center
            x_pos, y_pos = "(W-w)/2", "(H-h)/2"

        if overlay_data.type == OverlayType.text:
            font_filter = ""
            if overlay_data.font_name:
                font_path = os.path.join("fonts", overlay_data.font_name)
                if os.path.exists(font_path):
                    font_filter = f":fontfile='{font_path}'"
                else:
                    print(f"Warning: Font file not found at {font_path}. Using default font.")

            filter_cmd = (
                f"drawtext=text='{overlay_data.content}':"
                f"x={x_pos}:y={y_pos}:"
                f"fontsize=72:fontcolor=white:borderw=4:bordercolor=black:"
                f"enable='between(t,{overlay_data.start_time},{overlay_data.end_time})'{font_filter}"
            )
            command.extend(["-vf", filter_cmd, "-c:a", "copy"])

        elif overlay_data.type in [OverlayType.image, OverlayType.watermark, OverlayType.video]:
            overlay_file_path = os.path.join("overlays_media", overlay_data.content)
            if not os.path.exists(overlay_file_path):
                raise FileNotFoundError(f"Overlay image/video file not found at {overlay_file_path}")

            is_video_overlay = overlay_file_path.endswith(('.mp4', '.mov', '.avi', '.mkv'))
            
            command.extend(["-i", overlay_file_path])
            
            if is_video_overlay:
                overlay_has_audio = has_audio_stream(Path(overlay_file_path))

                filter_complex = f"[0:v][1:v]overlay={x_pos}:{y_pos}:enable='between(t,{overlay_data.start_time},{overlay_data.end_time})'[outv]"
                command.extend(["-filter_complex", filter_complex, "-map", "[outv]", "-map", "0:a"])

                if overlay_has_audio:
                    command.extend(["-map", "1:a"])
                else:
                    print("Overlay video has no audio stream, skipping audio map for it.")

                command.extend(["-shortest", "-c:a", "copy"])
            else: # Image overlay
                filter_complex = f"[0:v][1:v]overlay={x_pos}:{y_pos}:enable='between(t,{overlay_data.start_time},{overlay_data.end_time})'[outv]"
                command.extend(["-filter_complex", filter_complex, "-map", "[outv]", "-map", "0:a", "-c:a", "copy"])

        else:
            job.status = JobStatus.failed
            db.commit()
            raise ValueError(f"Unsupported overlay type: {overlay_data.type}")

        command.extend([output_path])
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
    except Exception as e:
        db.rollback()
        job.status = JobStatus.failed
        db.commit()
        print(f"An error occurred: {e}")
    finally:
        db.close()

def upload_video_task(job_id: int, file_path: str):
    """Handles metadata extraction and initial database entry after file is saved."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.processing
        db.commit()

        metadata = get_video_metadata(Path(file_path))

        new_video = Video(
            filename=os.path.basename(file_path),
            size=metadata['size'],
            duration=metadata['duration'],
            original_video_id=None
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

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

def quality_export_in_background(job_id: int, input_video_id: int, quality: VideoQuality):
    """Generates a new video version with specified quality and updates job status."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job: return

        job.status = JobStatus.processing
        db.commit()

        input_video = db.query(Video).filter(Video.id == input_video_id).first()
        if not input_video:
            job.status = JobStatus.failed
            db.commit()
            return
            
        input_file_path = ""
        if input_video.original_video_id is None:
            input_file_path = os.path.join("uploads", input_video.filename)
        else:
            input_file_path = os.path.join("processed", input_video.filename)

        if not os.path.exists(input_file_path):
            raise FileNotFoundError(f"Input video file not found at {input_file_path}")

        output_dir = "processed"
        os.makedirs(output_dir, exist_ok=True)
        quality_res = ""
        if quality == VideoQuality.p1080: quality_res = "1920:-1"
        elif quality == VideoQuality.p720: quality_res = "1280:-1"
        elif quality == VideoQuality.p480: quality_res = "854:-1"
        
        output_filename = f"{quality.value}_{input_video.filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        command = [
            "ffmpeg",
            "-i", input_file_path,
            "-vf", f"scale={quality_res}",
            "-c:a", "copy",
            output_path
        ]
        
        subprocess.run(command, check=True)

        new_version = VideoVersion(
            video_id=input_video.id,
            quality=quality,
            file_path=output_path
        )
        db.add(new_version)
        db.commit()
        db.refresh(new_version)

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