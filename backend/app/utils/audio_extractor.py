"""
Audio extraction utilities for video processing
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AudioExtractor:
    """Extract audio from video files using FFmpeg"""
    
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg'}
    SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
    
    def __init__(self, temp_dir: Optional[Path] = None):
        if temp_dir is None:
            # Use project temp directory
            from ..core.config import config
            self.temp_dir = config.temp_dir
        else:
            self.temp_dir = temp_dir
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Check if FFmpeg is installed"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("FFmpeg is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg is not installed or not in PATH. Please install FFmpeg first.")
    
    def is_video_file(self, file_path: str) -> bool:
        """Check if file is a video file"""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_VIDEO_FORMATS
    
    def is_audio_file(self, file_path: str) -> bool:
        """Check if file is an audio file"""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_AUDIO_FORMATS
    
    def get_media_info(self, file_path: str) -> dict:
        """Get media file information using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-show_entries', 'stream=codec_type,codec_name',
                '-of', 'json',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Failed to get media info: {e}")
            return {}
    
    def get_duration(self, file_path: str) -> float:
        """Get media duration in seconds"""
        info = self.get_media_info(file_path)
        try:
            return float(info.get('format', {}).get('duration', 0))
        except (ValueError, TypeError):
            return 0.0
    
    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1
    ) -> str:
        """
        Extract audio from video file
        
        Args:
            video_path: Path to video file
            output_path: Output audio file path (optional)
            format: Output audio format (wav, mp3, flac)
            sample_rate: Output sample rate
            channels: Number of audio channels (1=mono, 2=stereo)
        
        Returns:
            Path to extracted audio file
        """
        if not self.is_video_file(video_path) and not self.is_audio_file(video_path):
            raise ValueError(f"Unsupported file format: {video_path}")
        
        # If it's already an audio file, convert it
        if output_path is None:
            output_path = str(self.temp_dir / f"{Path(video_path).stem}.{format}")
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-i', video_path,
            '-vn',  # No video
            '-acodec', self._get_audio_codec(format),
            '-ar', str(sample_rate),
            '-ac', str(channels),
        ]
        
        # Add format-specific options
        if format == "mp3":
            cmd.extend(['-q:a', '2'])  # High quality
        elif format == "wav":
            cmd.extend(['-acodec', 'pcm_s16le'])  # 16-bit PCM
        
        cmd.append(output_path)
        
        logger.info(f"Extracting audio from {video_path} to {output_path}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Audio extraction completed: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to extract audio: {e.stderr}")
    
    def _get_audio_codec(self, format: str) -> str:
        """Get FFmpeg audio codec for format"""
        codecs = {
            "wav": "pcm_s16le",
            "mp3": "libmp3lame",
            "flac": "flac",
            "aac": "aac",
            "ogg": "libvorbis",
            "m4a": "aac",
        }
        return codecs.get(format, "pcm_s16le")
    
    def split_audio(
        self,
        audio_path: str,
        segment_duration: float = 300.0,  # 5 minutes
        output_dir: Optional[Path] = None
    ) -> list:
        """
        Split audio into segments
        
        Args:
            audio_path: Path to audio file
            segment_duration: Duration of each segment in seconds
            output_dir: Directory for output segments
        
        Returns:
            List of segment file paths
        """
        if output_dir is None:
            output_dir = self.temp_dir / "segments"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        duration = self.get_duration(audio_path)
        if duration <= segment_duration:
            return [audio_path]
        
        segments = []
        num_segments = int(duration / segment_duration) + 1
        
        for i in range(num_segments):
            start_time = i * segment_duration
            segment_path = output_dir / f"segment_{i:04d}.wav"
            
            cmd = [
                'ffmpeg',
                '-y',
                '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(segment_duration),
                '-c', 'copy',
                str(segment_path)
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                segments.append(str(segment_path))
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to split segment {i}: {e.stderr}")
                continue
        
        logger.info(f"Split audio into {len(segments)} segments")
        return segments
    
    def detect_silence(
        self,
        audio_path: str,
        silence_threshold: int = -50,  # dB
        min_silence_duration: float = 0.5  # seconds
    ) -> list:
        """
        Detect silence periods in audio for smart splitting
        
        Args:
            audio_path: Path to audio file
            silence_threshold: Silence threshold in dB
            min_silence_duration: Minimum silence duration
        
        Returns:
            List of silence periods (start, end)
        """
        cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-af', f'silencedetect=noise={silence_threshold}dB:d={min_silence_duration}',
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse silence detection output
            silences = []
            lines = result.stderr.split('\n')
            silence_start = None
            
            for line in lines:
                if 'silence_start:' in line:
                    silence_start = float(line.split('silence_start:')[1].strip())
                elif 'silence_end:' in line and silence_start is not None:
                    silence_end = float(line.split('silence_end:')[1].split('|')[0].strip())
                    silences.append((silence_start, silence_end))
                    silence_start = None
            
            return silences
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to detect silence: {e.stderr}")
            return []


# Global instance
audio_extractor = AudioExtractor()
