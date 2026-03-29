"""
Subtitle rendering utilities for generating subtitle files and burning subtitles into video
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from datetime import timedelta
import logging

from ..core.config import SubtitleStyle, SubtitlePosition
from ..models.base_asr import TranscriptionSegment

logger = logging.getLogger(__name__)


@dataclass
class SubtitleEntry:
    index: int
    start: float
    end: float
    text: str


def format_timestamp_srt(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def split_text_by_punctuation(text: str, max_chars: int = 40) -> List[str]:
    sentence_end = {'。', '！', '？', '.', '!', '?', '…', '；', ';'}
    clause_end = {'，', ',', '、', '：', ':'}
    min_segment_chars = 4
    
    raw_segments = []
    current = ""
    
    for char in text:
        current += char
        
        if char in sentence_end or char in clause_end:
            if current.strip():
                raw_segments.append(current.strip())
            current = ""
    
    if current.strip():
        raw_segments.append(current.strip())
    
    result = []
    for seg in raw_segments:
        seg_chars = len([c for c in seg if c.strip()])
        
        if result and seg_chars < min_segment_chars:
            result[-1] += seg
        else:
            result.append(seg)
    
    return result


def group_segments_by_text(
    full_text: str,
    segments: List[TranscriptionSegment],
    max_chars: int = 40,
    max_duration: float = 5.0
) -> List[SubtitleEntry]:
    if not segments or not full_text:
        return []
    
    sentences = split_text_by_punctuation(full_text, max_chars)
    
    text_no_punct = [c for c in full_text if c.strip() and c not in '，。！？、：；,.!?;:']
    seg_text_all = ''.join(seg.text.strip() for seg in segments)
    
    if len(text_no_punct) != len(seg_text_all):
        logger.warning(f"Text length mismatch: full_text={len(text_no_punct)}, segments={len(seg_text_all)}")
    
    seg_idx = 0
    text_idx = 0
    seg_time_map = []
    
    for seg in segments:
        seg_chars = [c for c in seg.text.strip() if c.strip()]
        for _ in seg_chars:
            seg_time_map.append((seg.start, seg.end))
    
    entries = []
    entry_index = 1
    char_offset = 0
    
    for sentence in sentences:
        sentence_no_punct = [c for c in sentence if c.strip() and c not in '，。！？、：；,.!?;:']
        char_count = len(sentence_no_punct)
        
        if char_offset + char_count > len(seg_time_map):
            break
        
        start_time = seg_time_map[char_offset][0]
        end_time = seg_time_map[char_offset + char_count - 1][1]
        
        entries.append(SubtitleEntry(
            index=entry_index,
            start=start_time,
            end=end_time,
            text=sentence
        ))
        
        char_offset += char_count
        entry_index += 1
    
    return entries


def group_segments_simple(
    segments: List[TranscriptionSegment],
    max_chars: int = 40,
    max_duration: float = 5.0,
    max_gap: float = 1.0
) -> List[SubtitleEntry]:
    if not segments:
        return []

    grouped = []
    current_text = ""
    current_start = -1.0
    current_end = -1.0
    entry_index = 1

    for segment in segments:
        text = segment.text
        start = segment.start
        end = segment.end

        if current_start < 0:
            current_start = start
            current_text = text
            current_end = end
            continue

        duration = end - current_start
        gap = start - current_end

        exceeds_char_limit = len(current_text) + len(text) > max_chars
        exceeds_duration = duration > max_duration
        exceeds_gap = gap > max_gap

        if exceeds_char_limit or exceeds_duration or exceeds_gap:
            grouped.append(SubtitleEntry(
                index=entry_index,
                start=current_start,
                end=current_end,
                text=current_text.strip()
            ))
            entry_index += 1
            current_text = text
            current_start = start
            current_end = end
        else:
            is_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
            if is_chinese:
                current_text += text
            else:
                current_text += " " + text
            current_end = end

    if current_text:
        grouped.append(SubtitleEntry(
            index=entry_index,
            start=current_start,
            end=current_end,
            text=current_text.strip()
        ))

    return grouped


def group_segments(
    segments: List[TranscriptionSegment],
    max_chars: int = 40,
    max_duration: float = 5.0,
    max_gap: float = 1.0,
    full_text: Optional[str] = None,
    use_native_segmentation: bool = False
) -> List[SubtitleEntry]:
    if use_native_segmentation:
        return [
            SubtitleEntry(
                index=i,
                start=seg.start,
                end=seg.end,
                text=seg.text.strip()
            )
            for i, seg in enumerate(segments, 1)
        ]
    
    if full_text:
        return group_segments_by_text(full_text, segments, max_chars, max_duration)
    return group_segments_simple(segments, max_chars, max_duration, max_gap)


class SubtitleRenderer:
    
    def __init__(self, temp_dir: Optional[Path] = None):
        if temp_dir is None:
            from ..core.config import config
            self.temp_dir = config.temp_dir
        else:
            self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def seconds_to_srt_time(self, seconds: float) -> str:
        return format_timestamp_srt(seconds)
    
    def seconds_to_ass_time(self, seconds: float) -> str:
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        centiseconds = int(td.microseconds / 10000)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
    
    def generate_srt(
        self,
        segments: List[TranscriptionSegment],
        output_path: str,
        max_chars_per_line: int = 40,
        max_lines: int = 2,
        group: bool = True,
        split_by_punct: bool = True,
        full_text: Optional[str] = None,
        use_native_segmentation: bool = False
    ) -> str:
        if group:
            entries = group_segments(
                segments,
                max_chars=max_chars_per_line * max_lines,
                max_duration=5.0,
                max_gap=0.5,
                full_text=full_text,
                use_native_segmentation=use_native_segmentation
            )
        else:
            entries = [
                SubtitleEntry(
                    index=i,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip()
                )
                for i, seg in enumerate(segments, 1)
            ]
        
        lines = []
        for entry in entries:
            start_time = self.seconds_to_srt_time(entry.start)
            end_time = self.seconds_to_srt_time(entry.end)
            lines.append(f"{entry.index}")
            lines.append(f"{start_time} --> {end_time}")
            lines.append(entry.text)
            lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        logger.info(f"Generated SRT file: {output_path} with {len(entries)} entries")
        return output_path
    
    def generate_ass(
        self,
        segments: List[TranscriptionSegment],
        output_path: str,
        style: SubtitleStyle,
        video_width: int = 1920,
        video_height: int = 1080,
        max_chars_per_line: int = 40,
        max_lines: int = 2,
        full_text: Optional[str] = None,
        use_native_segmentation: bool = False
    ) -> str:
        entries = group_segments(
            segments,
            max_chars=max_chars_per_line * max_lines,
            max_duration=5.0,
            max_gap=0.5,
            full_text=full_text,
            use_native_segmentation=use_native_segmentation
        )
        
        alignment = style.alignment
        margin_v = style.margin_v
        margin_h = style.margin_h
        
        ass_header = self._generate_ass_header(style, video_width, video_height)
        
        dialogue_events = []
        for entry in entries:
            text = entry.text
            
            if style.position == SubtitlePosition.CUSTOM and style.custom_x is not None and style.custom_y is not None:
                text = f"{{\\pos({style.custom_x},{style.custom_y})}}{text}"
            
            event = f"Dialogue: 0,{self.seconds_to_ass_time(entry.start)},{self.seconds_to_ass_time(entry.end)},Default,,0,0,0,,{text}"
            dialogue_events.append(event)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_header)
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for event in dialogue_events:
                f.write(event + "\n")
        
        logger.info(f"Generated ASS file: {output_path} with {len(entries)} entries")
        logger.debug(f"ASS header:\n{ass_header}")
        return output_path
    
    def _generate_ass_header(self, style: SubtitleStyle, video_width: int, video_height: int) -> str:
        logger.info(f"Generating ASS header with style: font_name={style.font_name}, font_size={style.font_size}, font_color={style.font_color}, outline_color={style.outline_color}")
        
        alignment_map = {
            "bottom-center": 2,
            "bottom-left": 1,
            "bottom-right": 3,
            "center-center": 5,
            "center-left": 4,
            "center-right": 6,
            "top-center": 8,
            "top-left": 7,
            "top-right": 9,
        }
        
        alignment = alignment_map.get(style.alignment.value if hasattr(style.alignment, 'value') else style.alignment, 2)
        
        if style.position == SubtitlePosition.BOTTOM:
            alignment = 2
        elif style.position == SubtitlePosition.TOP:
            alignment = 8
        elif style.position == SubtitlePosition.CENTER:
            alignment = 5
        
        primary_color = self._color_to_ass(style.font_color)
        outline_color = self._color_to_ass(style.outline_color)
        back_color = self._color_to_ass(style.background_color or "#000000")
        
        logger.info(f"ASS Style - Font color: {style.font_color} -> {primary_color}")
        logger.info(f"ASS Style - Outline color: {style.outline_color} -> {outline_color}")
        
        header = f"""[Script Info]
Title: Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{primary_color},&H00FFFFFF,{outline_color},{back_color},0,0,0,0,100,100,0,0,1,{style.outline_width},0,{alignment},{style.margin_h},{style.margin_h},{style.margin_v},1

"""
        return header
    
    def _color_to_ass(self, color: str) -> str:
        if not color:
            return "&H00FFFFFF"
        
        color = color.strip()
        
        if color.lower().startswith('rgba('):
            parts = color[5:-1].split(',')
            if len(parts) == 4:
                r = int(float(parts[0].strip()))
                g = int(float(parts[1].strip()))
                b = int(float(parts[2].strip()))
                a = float(parts[3].strip())
                ass_alpha = f"{int(255 * (1 - a)):02X}"
                result = f"&H{ass_alpha}{b:02X}{g:02X}{r:02X}"
                logger.debug(f"RGBA color conversion: input={color}, output={result}")
                return result
        
        if color.lower().startswith('rgb('):
            parts = color[4:-1].split(',')
            if len(parts) == 3:
                r = int(float(parts[0].strip()))
                g = int(float(parts[1].strip()))
                b = int(float(parts[2].strip()))
                result = f"&H00{b:02X}{g:02X}{r:02X}"
                logger.debug(f"RGB color conversion: input={color}, output={result}")
                return result
        
        color = color.upper()
        
        if color.startswith('#'):
            color = color[1:]
        
        if len(color) == 3:
            color = color[0] + color[0] + color[1] + color[1] + color[2] + color[2]
        
        if len(color) == 6:
            r = color[0:2]
            g = color[2:4]
            b = color[4:6]
            result = f"&H00{b}{g}{r}"
            logger.debug(f"Color conversion: input={color}, output={result}")
            return result
        
        if len(color) == 8:
            r = color[0:2]
            g = color[2:4]
            b = color[4:6]
            a = color[6:8]
            ass_alpha = f"{255 - int(a, 16):02X}"
            return f"&H{ass_alpha}{b}{g}{r}"
        
        logger.warning(f"Failed to parse color: {color}, using default white")
        return "&H00FFFFFF"
    
    def _escape_subtitle_path(self, path: str) -> str:
        if sys.platform == "win32":
            return path.replace("\\", "/").replace(":", "\\:")
        return path
    
    def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        video_codec: str = "libx264",
        audio_codec: str = "copy",
        crf: int = 23
    ) -> str:
        subtitle_path_filter = self._escape_subtitle_path(subtitle_path)
        
        # Check if subtitle file is ASS format
        is_ass = subtitle_path.lower().endswith('.ass')
        
        if is_ass:
            # Use 'ass' filter for ASS files to ensure proper style rendering
            vf_filter = f"ass='{subtitle_path_filter}'"
        else:
            # Use 'subtitles' filter for SRT files
            vf_filter = f"subtitles='{subtitle_path_filter}'"
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", vf_filter,
            "-c:v", video_codec,
            "-c:a", audio_codec,
            "-crf", str(crf),
            "-y",
            output_path
        ]
        
        logger.info(f"Burning subtitles: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Failed to burn subtitles: {result.stderr}")
        
        logger.info(f"Successfully burned subtitles to: {output_path}")
        return output_path
    
    def add_soft_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        language: str = "und",
        title: str = "Subtitles"
    ) -> str:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-i", subtitle_path,
            "-c", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", f"language={language}",
            "-metadata:s:s:0", f"title={title}",
            "-y",
            output_path
        ]
        
        logger.info(f"Adding soft subtitles: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Failed to add soft subtitles: {result.stderr}")
        
        logger.info(f"Successfully added soft subtitles to: {output_path}")
        return output_path


subtitle_renderer = SubtitleRenderer()
