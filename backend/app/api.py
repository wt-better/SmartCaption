"""
FastAPI Web API for SmartCaption Frontend
"""
import os
import logging
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .core.config import (
    ASRModelType,
    SubtitlePosition,
    SubtitleStyle,
    ASRConfig,
    config
)
from .services.caption_service import caption_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SmartCaption API",
    description="智能字幕生成服务 API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
config.upload_dir.mkdir(parents=True, exist_ok=True)
config.output_dir.mkdir(parents=True, exist_ok=True)
config.temp_dir.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/models")
async def list_models():
    """List available ASR models"""
    from .core.config import list_supported_models
    return {"models": list_supported_models()}


@app.post("/api/process")
async def process_video(
    file: UploadFile = File(...),
    model_type: str = Form("Qwen/Qwen3-ASR-1.7B"),
    subtitle_format: str = Form("srt"),
    position: str = Form("bottom"),
    font_name: str = Form("Arial"),
    font_size: int = Form(24),
    font_color: str = Form("#FFFFFF"),
    outline_color: str = Form("#000000"),
    outline_width: int = Form(2),
    soft_subtitle: bool = Form(False),
    language: Optional[str] = Form(None)
):
    """
    Process video and generate captions

    Args:
        file: Video or audio file
        model_type: ASR model type
        subtitle_format: Subtitle format (srt or ass)
        position: Subtitle position
        font_name: Font name
        font_size: Font size
        font_color: Font color (hex)
        outline_color: Outline color (hex)
        outline_width: Outline width
        soft_subtitle: Whether to use soft subtitles
        language: Language code (optional)

    Returns:
        Processing result with output paths
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        upload_path = config.upload_dir / safe_filename

        logger.info(f"Saving uploaded file to {upload_path}")
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Build ASR config
        try:
            asr_type = ASRModelType(model_type)
        except ValueError:
            asr_type = ASRModelType.QWEN3_ASR_1_7B

        asr_config = ASRConfig(
            model_type=asr_type,
            language=language if language else None,
            return_timestamps=True
        )

        # Build subtitle style (only for ASS format)
        subtitle_style = None
        if subtitle_format.lower() == "ass":
            try:
                pos = SubtitlePosition(position)
            except ValueError:
                pos = SubtitlePosition.BOTTOM

            subtitle_style = SubtitleStyle(
                position=pos,
                font_name=font_name,
                font_size=font_size,
                font_color=font_color,
                outline_color=outline_color,
                outline_width=outline_width
            )

        # Generate output path
        output_filename = f"{upload_path.stem}_captioned{upload_path.suffix}"
        output_path = str(config.output_dir / output_filename)

        logger.info(f"Starting caption generation: {upload_path} -> {output_path}")

        # Process video
        result = caption_service.generate_caption(
            video_path=str(upload_path),
            output_path=output_path,
            asr_config=asr_config,
            subtitle_style=subtitle_style,
            subtitle_format=subtitle_format,
            soft_subtitle=soft_subtitle
        )

        if result["success"]:
            # Clean up uploaded file
            try:
                os.remove(upload_path)
            except Exception as e:
                logger.warning(f"Failed to remove upload file: {e}")

            return {
                "success": True,
                "output_path": result["output_path"],
                "subtitle_path": result.get("subtitle_path", ""),
                "transcription": result["transcription"]
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Processing failed")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/output/{filename:path}")
async def get_output_file(filename: str):
    """Get output file for preview"""
    file_path = config.output_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=file_path.name
    )


@app.get("/api/download")
async def download_file(path: str):
    """Download file by path"""
    file_path = Path(path)

    # Security check: ensure file is in allowed directories
    allowed_dirs = [config.output_dir, config.temp_dir]
    is_allowed = any(
        str(file_path.resolve()).startswith(str(d.resolve()))
        for d in allowed_dirs
    )

    if not is_allowed:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )


# Mount static files (frontend)
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


def main():
    """Run the API server"""
    uvicorn.run(
        "app.api:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
