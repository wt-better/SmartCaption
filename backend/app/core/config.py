"""
Configuration module for SmartCaption
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ASRModelType(str, Enum):
    """Supported ASR model types"""
    QWEN3_ASR_1_7B = "Qwen/Qwen3-ASR-1.7B"
    QWEN3_ASR_0_6B = "Qwen/Qwen3-ASR-0.6B"
    WHISPER_LARGE_V3 = "openai/whisper-large-v3"


class SubtitlePosition(str, Enum):
    """Subtitle position options"""
    BOTTOM = "bottom"
    TOP = "top"
    CENTER = "center"
    CUSTOM = "custom"


@dataclass
class SubtitleStyle:
    """Subtitle style configuration"""
    position: SubtitlePosition = SubtitlePosition.BOTTOM
    font_name: str = "Arial"
    font_size: int = 24
    font_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: int = 2
    background_color: Optional[str] = None
    background_alpha: float = 0.0
    margin_v: int = 30
    margin_h: int = 30
    alignment: int = 2  # 1=left, 2=center, 3=right, 4=top-left, 5=top-center, 6=top-right, 7=mid-left, 8=mid-center, 9=mid-right
    custom_x: Optional[int] = None
    custom_y: Optional[int] = None


@dataclass
class ASRConfig:
    """ASR model configuration"""
    model_type: ASRModelType = ASRModelType.QWEN3_ASR_1_7B
    device: str = "auto"  # auto, cpu, cuda
    language: Optional[str] = None  # auto-detect if None
    batch_size: int = 1
    use_vllm: bool = False
    return_timestamps: bool = True
    timestamp_format: str = "sentence"  # sentence or word


@dataclass
class VideoConfig:
    """Video processing configuration"""
    output_format: str = "mp4"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5000k"
    audio_bitrate: str = "192k"
    preserve_original: bool = True


@dataclass
class AppConfig:
    """Application configuration"""
    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    upload_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "uploads")
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "outputs")
    temp_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "temp")
    
    # Processing
    max_file_size: int = 1024 * 1024 * 1024  # 1GB
    chunk_duration: int = 300  # 5 minutes in seconds
    max_workers: int = 4
    
    # ASR
    asr: ASRConfig = field(default_factory=ASRConfig)
    
    # Subtitle
    subtitle: SubtitleStyle = field(default_factory=SubtitleStyle)
    
    # Video
    video: VideoConfig = field(default_factory=VideoConfig)
    
    def __post_init__(self):
        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = AppConfig()


# Model metadata
ASR_MODELS_INFO: Dict[ASRModelType, Dict] = {
    ASRModelType.QWEN3_ASR_1_7B: {
        "name": "Qwen3-ASR-1.7B",
        "description": "中文效果优秀，速度快",
        "parameters": "1.7B",
        "languages": ["zh", "en", "yue", "ar", "de", "fr", "es", "pt", "id", "it", "ko", "ru", "th", "vi", "ja", "tr", "hi", "ms", "nl", "sv", "da", "fi", "pl", "cs", "fil", "fa", "el", "hu", "mk", "ro"],
        "dialects": ["Anhui", "Dongbei", "Fujian", "Gansu", "Guizhou", "Hebei", "Henan", "Hubei", "Hunan", "Jiangxi", "Ningxia", "Shandong", "Shaanxi", "Shanxi", "Sichuan", "Tianjin", "Yunnan", "Zhejiang", "Cantonese (HK)", "Cantonese (GD)", "Wu", "Minnan"],
        "supports_streaming": True,
        "requires_vllm": False,
    },
    ASRModelType.QWEN3_ASR_0_6B: {
        "name": "Qwen3-ASR-0.6B",
        "description": "轻量级，资源占用低",
        "parameters": "0.6B",
        "languages": ["zh", "en", "yue", "ar", "de", "fr", "es", "pt", "id", "it", "ko", "ru", "th", "vi", "ja", "tr", "hi", "ms", "nl", "sv", "da", "fi", "pl", "cs", "fil", "fa", "el", "hu", "mk", "ro"],
        "dialects": ["Anhui", "Dongbei", "Fujian", "Gansu", "Guizhou", "Hebei", "Henan", "Hubei", "Hunan", "Jiangxi", "Ningxia", "Shandong", "Shaanxi", "Shanxi", "Sichuan", "Tianjin", "Yunnan", "Zhejiang", "Cantonese (HK)", "Cantonese (GD)", "Wu", "Minnan"],
        "supports_streaming": True,
        "requires_vllm": False,
    },
    ASRModelType.WHISPER_LARGE_V3: {
        "name": "Whisper Large V3",
        "description": "多语言支持好，精度高",
        "parameters": "1.5B",
        "languages": ["en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr", "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi", "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no", "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk", "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk", "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw", "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc", "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo", "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl", "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su"],
        "dialects": [],
        "supports_streaming": False,
        "requires_vllm": False,
    },
}


def get_model_info(model_type: ASRModelType) -> Dict:
    """Get information about an ASR model"""
    return ASR_MODELS_INFO.get(model_type, {})


def list_supported_models() -> List[Dict]:
    """List all supported ASR models"""
    return [
        {
            "type": model_type.value,
            **info
        }
        for model_type, info in ASR_MODELS_INFO.items()
    ]
