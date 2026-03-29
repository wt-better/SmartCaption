"""
Gradio Web Interface for SmartCaption
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Tuple

# Disable analytics before importing gradio
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'

import gradio as gr

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import from app package
from app.core.config import (
    ASRModelType, 
    SubtitlePosition, 
    SubtitleStyle, 
    ASRConfig,
    list_supported_models,
    get_model_info
)
from app.services.caption_service import caption_service


class SmartCaptionGradioApp:
    """Gradio interface for SmartCaption"""

    def __init__(self):
        self.supported_models = list_supported_models()
        self.positions = ["bottom", "top", "center"]
        self.fonts = ["Arial", "Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC"]

    def get_model_choices(self):
        """Get model choices for dropdown"""
        return [model["type"] for model in self.supported_models]

    def get_model_description(self, model_type: str) -> str:
        """Get model description"""
        try:
            asr_type = ASRModelType(model_type)
            info = get_model_info(asr_type)
            return f"""
**{info['name']}** ({info['parameters']})

{info['description']}

**支持语言:** {len(info['languages'])} 种
**支持方言:** {len(info['dialects'])} 种
"""
        except:
            return "选择模型查看详情"

    def process_video(
        self,
        video_file: str,
        model_type: str,
        subtitle_format: str,
        position: str,
        font_name: str,
        font_size: int,
        font_color: str,
        outline_color: str,
        outline_width: int,
        margin_v: int,
        soft_subtitle: bool,
        progress=gr.Progress()
    ) -> Tuple[str, str, str]:
        """
        Process video and generate captions
        
        Returns:
            Tuple of (output_video_path, subtitle_text, status_message)
        """
        if video_file is None:
            return None, "", "请先上传视频文件"
        
        try:
            # Create progress callback
            def progress_callback(p: float, message: str):
                progress(p, desc=message)
            
            # Build ASR config
            asr_config = ASRConfig(
                model_type=ASRModelType(model_type),
                return_timestamps=True
            )
            
            # Build subtitle style
            subtitle_style = SubtitleStyle(
                position=SubtitlePosition(position),
                font_name=font_name,
                font_size=font_size,
                font_color=font_color,
                outline_color=outline_color,
                outline_width=outline_width,
                margin_v=margin_v
            )
            
            # Process video
            progress(0, desc="开始处理...")
            
            result = caption_service.generate_caption(
                video_path=video_file,
                asr_config=asr_config,
                subtitle_style=subtitle_style,
                subtitle_format=subtitle_format,
                progress_callback=progress_callback,
                soft_subtitle=soft_subtitle
            )
            
            if result["success"]:
                # Format transcription text
                transcription_text = result["transcription"]["text"]
                segments_text = "\n\n".join([
                    f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}"
                    for seg in result["transcription"]["segments"]
                ])
                
                full_text = f"**完整文本:**\n{transcription_text}\n\n**分段详情:**\n{segments_text}"
                
                return (
                    result["output_path"],
                    full_text,
                    f"✅ 字幕生成成功！\n输出文件: {result['output_path']}"
                )
            else:
                return None, "", f"❌ 处理失败: {result.get('error', '未知错误')}"
                
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return None, "", f"❌ 处理失败: {str(e)}"
    
    def create_interface(self) -> gr.Blocks:
        """Create Gradio interface"""
        
        with gr.Blocks(title="SmartCaption - 智能字幕生成") as app:
            gr.Markdown("""
            # 🎬 SmartCaption - 智能字幕生成器
            
            上传视频，自动生成字幕。支持多种ASR模型和自定义字幕样式。
            """)
            
            with gr.Row():
                # Left column - Input
                with gr.Column(scale=1):
                    gr.Markdown("### 📁 输入设置")
                    
                    video_input = gr.Video(
                        label="上传视频",
                        format="mp4"
                    )
                    
                    with gr.Accordion("🤖 ASR模型设置", open=True):
                        model_dropdown = gr.Dropdown(
                            choices=self.get_model_choices(),
                            value=self.get_model_choices()[0],
                            label="选择ASR模型"
                        )
                        
                        model_info = gr.Markdown(
                            self.get_model_description(self.get_model_choices()[0])
                        )
                        
                        model_dropdown.change(
                            fn=self.get_model_description,
                            inputs=[model_dropdown],
                            outputs=[model_info]
                        )
                    
                    with gr.Accordion("🎨 字幕样式设置", open=True):
                        subtitle_format_dropdown = gr.Dropdown(
                            choices=["srt", "ass"],
                            value="srt",
                            label="字幕格式",
                            info="ASS格式支持更多样式设置（如字体、颜色、位置等）"
                        )

                        with gr.Column(visible=False) as ass_style_container:
                            position_dropdown = gr.Dropdown(
                                choices=self.positions,
                                value="bottom",
                                label="字幕位置"
                            )

                            font_dropdown = gr.Dropdown(
                                choices=self.fonts,
                                value="Arial",
                                label="字体"
                            )

                            font_size_slider = gr.Slider(
                                minimum=8,
                                maximum=72,
                                value=24,
                                step=1,
                                label="字体大小"
                            )

                            font_color_picker = gr.ColorPicker(
                                value="#FFFFFF",
                                label="字体颜色"
                            )

                            outline_color_picker = gr.ColorPicker(
                                value="#000000",
                                label="描边颜色"
                            )

                            outline_width_slider = gr.Slider(
                                minimum=0,
                                maximum=5,
                                value=2,
                                step=1,
                                label="描边宽度"
                            )

                            margin_v_slider = gr.Slider(
                                minimum=0,
                                maximum=100,
                                value=30,
                                step=5,
                                label="垂直边距"
                            )

                        soft_subtitle_checkbox = gr.Checkbox(
                            label="软字幕 (可开关)",
                            value=False,
                            info="勾选则添加可开关的软字幕，不勾选则烧录硬字幕"
                        )

                        subtitle_format_dropdown.change(
                            fn=lambda fmt: gr.update(visible=(fmt == "ass")),
                            inputs=[subtitle_format_dropdown],
                            outputs=[ass_style_container]
                        )
                    
                    process_btn = gr.Button(
                        "🚀 开始生成字幕",
                        variant="primary",
                        size="lg"
                    )
                
                # Right column - Output
                with gr.Column(scale=1):
                    gr.Markdown("### 📤 输出结果")
                    
                    video_output = gr.Video(
                        label="带字幕的视频"
                    )
                    
                    status_text = gr.Textbox(
                        label="处理状态",
                        value="等待开始...",
                        interactive=False
                    )
                    
                    with gr.Accordion("📝 转录文本", open=False):
                        transcription_output = gr.Markdown(
                            label="转录内容"
                        )
            
            # Event handlers
            process_btn.click(
                fn=self.process_video,
                inputs=[
                    video_input,
                    model_dropdown,
                    subtitle_format_dropdown,
                    position_dropdown,
                    font_dropdown,
                    font_size_slider,
                    font_color_picker,
                    outline_color_picker,
                    outline_width_slider,
                    margin_v_slider,
                    soft_subtitle_checkbox
                ],
                outputs=[
                    video_output,
                    transcription_output,
                    status_text
                ]
            )
            
            # Examples
            gr.Markdown("### 💡 使用提示")
            gr.Markdown("""
            1. **模型选择**:
               - Qwen3-ASR-1.7B: 中文效果最佳，推荐用于中文视频
               - Qwen3-ASR-0.6B: 轻量级，速度更快
               - Whisper Large V3: 多语言支持好，适合英文或多语言视频
            
            2. **语言设置**:
               - 留空让模型自动检测语言
               - 指定语言代码可提高识别准确率 (如: zh, en, ja)
            
            3. **字幕样式**:
               - 调整字体大小、颜色、描边以获得最佳视觉效果
               - 垂直边距控制字幕距离视频边缘的距离
            
            4. **处理时间**:
               - 取决于视频长度和选择的模型
               - 首次使用需要下载模型，可能需要几分钟
            """)
            
        
        return app


def main():
    """Main entry point"""
    # Ensure required directories exist before launching
    from app.core.config import config
    config.upload_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.temp_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting SmartCaption Gradio App...")
    logger.info(f"Upload directory: {config.upload_dir}")
    logger.info(f"Output directory: {config.output_dir}")
    logger.info(f"Temp directory: {config.temp_dir}")
    
    app = SmartCaptionGradioApp()
    interface = app.create_interface()
    
    # Launch the app with monitoring disabled to avoid health check issues in conda environments
    # Use allowed_paths to prevent path validation errors
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        quiet=False,  # Show more logs for debugging
        enable_monitoring=False,
        prevent_thread_lock=False,
        allowed_paths=["."]
    )


if __name__ == "__main__":
    main()
