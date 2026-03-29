"""
Caption generation service - Main orchestrator for subtitle generation workflow
"""
import os
import logging
from pathlib import Path
from typing import Optional, Callable, List

from ..core.config import config, ASRConfig, SubtitleStyle, ASRModelType
from ..models.base_asr import BaseASRModel, TranscriptionResult
from ..models.asr_factory import create_asr_model
from ..utils.audio_extractor import audio_extractor
from ..utils.subtitle_renderer import subtitle_renderer

logger = logging.getLogger(__name__)


class CaptionService:
    """Service for generating captions from video"""
    
    def __init__(self):
        self.current_model: Optional[BaseASRModel] = None
        self.current_model_type: Optional[ASRModelType] = None
    
    def _get_or_load_model(self, asr_config: ASRConfig) -> BaseASRModel:
        """Get cached model or load new one"""
        if (self.current_model is not None and 
            self.current_model_type == asr_config.model_type and
            self.current_model.is_loaded):
            logger.info(f"Using cached model: {asr_config.model_type.value}")
            return self.current_model
        
        # Unload previous model if different
        if self.current_model is not None:
            self.current_model.unload()
        
        # Load new model
        logger.info(f"Loading model: {asr_config.model_type.value}")
        self.current_model = create_asr_model(asr_config)
        self.current_model.load_model()
        self.current_model_type = asr_config.model_type
        
        return self.current_model
    
    def generate_caption(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        asr_config: Optional[ASRConfig] = None,
        subtitle_style: Optional[SubtitleStyle] = None,
        subtitle_format: str = "srt",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        soft_subtitle: bool = False
    ) -> dict:
        """
        Generate caption for video file

        Args:
            video_path: Path to input video file
            output_path: Path to output video file (optional)
            asr_config: ASR configuration (optional, uses default if not provided)
            subtitle_style: Subtitle style configuration (optional, only used for ASS format)
            subtitle_format: Subtitle format "srt" or "ass" (optional, defaults to "srt")
            progress_callback: Callback function for progress updates
            soft_subtitle: Whether to add soft subtitles instead of burning

        Returns:
            Dictionary with result information
        """
        # Use default configs if not provided
        if asr_config is None:
            asr_config = config.asr
        if subtitle_style is None:
            subtitle_style = config.subtitle
        
        # Generate output path if not provided
        if output_path is None:
            input_path = Path(video_path)
            output_path = str(
                config.output_dir / f"{input_path.stem}_captioned{input_path.suffix}"
            )
        
        try:
            # Step 1: Extract audio from video
            self._update_progress(progress_callback, 0.1, "Extracting audio...")
            audio_path = audio_extractor.extract_audio(
                video_path,
                output_path=str(config.temp_dir / f"{Path(video_path).stem}.wav")
            )
            logger.info(f"Extracted audio: {audio_path}")
            
            # Step 2: Load ASR model
            self._update_progress(progress_callback, 0.2, "Loading ASR model...")
            model = self._get_or_load_model(asr_config)
            
            # Step 3: Transcribe audio
            self._update_progress(progress_callback, 0.3, "Transcribing audio...")
            transcription = model.transcribe(
                audio_path,
                language=asr_config.language,
                return_timestamps=asr_config.return_timestamps
            )
            logger.info(f"Transcription completed: {len(transcription.segments)} segments")
            
            use_native_segmentation = asr_config.model_type == ASRModelType.WHISPER_LARGE_V3
            
            # Step 4: Generate subtitle file
            self._update_progress(progress_callback, 0.6, "Generating subtitle file...")
            if subtitle_format.lower() == "ass":
                subtitle_path = str(config.temp_dir / "subtitles.ass")
                subtitle_renderer.generate_ass(
                    transcription.segments,
                    subtitle_path,
                    style=subtitle_style,
                    video_width=1920,
                    video_height=1080,
                    max_chars_per_line=40,
                    max_lines=2,
                    full_text=transcription.text,
                    use_native_segmentation=use_native_segmentation
                )
            else:
                subtitle_path = str(config.temp_dir / "subtitles.srt")
                subtitle_renderer.generate_srt(
                    transcription.segments,
                    subtitle_path,
                    max_chars_per_line=40,
                    max_lines=2,
                    group=True,
                    split_by_punct=True,
                    full_text=transcription.text,
                    use_native_segmentation=use_native_segmentation
                )
            logger.info(f"Generated subtitle file: {subtitle_path}")
            
            # Step 5: Burn or add subtitles to video
            self._update_progress(progress_callback, 0.8, "Adding subtitles to video...")
            if soft_subtitle:
                final_output = subtitle_renderer.add_soft_subtitles(
                    video_path,
                    subtitle_path,
                    output_path
                )
            else:
                final_output = subtitle_renderer.burn_subtitles(
                    video_path,
                    subtitle_path,
                    output_path
                )
            logger.info(f"Generated captioned video: {final_output}")
            
            # Step 6: Cleanup temp files
            self._update_progress(progress_callback, 0.95, "Cleaning up...")
            self._cleanup_temp_files([audio_path, subtitle_path])
            
            self._update_progress(progress_callback, 1.0, "Completed!")
            
            return {
                "success": True,
                "output_path": final_output,
                "subtitle_path": subtitle_path,
                "transcription": {
                    "text": transcription.text,
                    "segments": [
                        {
                            "text": seg.text,
                            "start": seg.start,
                            "end": seg.end
                        }
                        for seg in transcription.segments
                    ],
                    "language": transcription.language
                }
            }
            
        except Exception as e:
            logger.error(f"Caption generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_progress(
        self,
        callback: Optional[Callable[[float, str], None]],
        progress: float,
        message: str
    ):
        """Update progress via callback"""
        logger.info(f"Progress: {progress:.0%} - {message}")
        if callback:
            try:
                callback(progress, message)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def _cleanup_temp_files(self, files: List[str]):
        """Clean up temporary files"""
        for file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {file_path}: {e}")
    
    def unload_model(self):
        """Unload current model to free memory"""
        if self.current_model is not None:
            self.current_model.unload()
            self.current_model = None
            self.current_model_type = None


# Global service instance
caption_service = CaptionService()
