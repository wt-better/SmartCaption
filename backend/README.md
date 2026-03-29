# SmartCaption 后端服务

智能字幕生成后端，支持多种ASR模型（Qwen3-ASR、Whisper）和可配置的字幕样式。

## 功能特性

- 🎯 **多模型支持**: Qwen3-ASR-1.7B、Qwen3-ASR-0.6B、Whisper Large V3
- 🎨 **可配置字幕样式**: 位置、字体、大小、颜色、描边等
- 🎬 **视频处理**: 音频提取、字幕烧录、软字幕支持
- 📊 **智能分段**: 自动合并短片段，生成可读性更好的字幕
- 🚀 **Gradio界面**: 直观的Web验证界面

## 项目结构

```
backend/
├── app/
│   ├── core/           # 核心配置
│   │   ├── config.py   # 配置类和模型定义
│   │   └── __init__.py
│   ├── models/         # ASR模型适配器
│   │   ├── base_asr.py       # 基础ASR接口
│   │   ├── qwen_asr.py       # Qwen3-ASR适配器（使用qwen-asr包）
│   │   ├── whisper_asr.py    # Whisper适配器（使用transformers）
│   │   ├── asr_factory.py    # 模型工厂
│   │   └── __init__.py
│   ├── services/       # 业务服务
│   │   ├── caption_service.py  # 字幕生成服务
│   │   └── __init__.py
│   ├── utils/          # 工具函数
│   │   ├── audio_extractor.py    # 音频提取
│   │   ├── subtitle_renderer.py  # 字幕渲染（含分段合并）
│   │   └── __init__.py
│   ├── gradio_app.py   # Gradio界面
│   └── __init__.py
├── requirements.txt    # 依赖列表
├── run_gradio.py       # Gradio启动脚本
└── README.md          # 本文档
```

## 快速开始

### 1. 环境准备

确保已安装 Python 3.10+ 和 FFmpeg：

```bash
# Windows (使用 chocolatey)
choco install ffmpeg

# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 启动 Gradio 界面

```bash
python run_gradio.py
```

访问 http://localhost:7860 使用界面。


## 支持的模型

| 模型 | 参数量 | 特点 | 适用场景 |
|------|--------|------|----------|
| Qwen/Qwen3-ASR-1.7B | 1.7B | 中文效果优秀，带强制对齐器 | 中文视频 |
| Qwen/Qwen3-ASR-0.6B | 0.6B | 轻量级，速度快 | 快速预览 |
| openai/whisper-large-v3 | 1.5B | 多语言支持好 | 多语言视频 |

## 注意事项

1. **首次运行**: 首次使用需要下载模型，根据网络情况可能需要几分钟
2. **GPU加速**: 如果有NVIDIA GPU，会自动使用CUDA加速
3. **内存需求**: 
   - Qwen3-ASR-1.7B + ForcedAligner: 建议 10GB+ 显存
   - Qwen3-ASR-0.6B: 建议 4GB+ 显存
   - Whisper Large V3: 建议 8GB+ 显存
4. **强制对齐器**: Qwen3-ASR 默认启用 Qwen3-ForcedAligner-0.6B 获取更精确的时间戳

## 许可证

MIT License
