/**
 * SmartCaption Frontend Application
 * 简约科技风前端交互逻辑
 */

// ============================================
// 全局状态管理
// ============================================
const AppState = {
    currentFile: null,
    isProcessing: false,
    taskId: null,
    eventSource: null,
    config: {
        model: 'Qwen/Qwen3-ASR-1.7B',
        language: '',
        subtitleFormat: 'srt',
        position: 'bottom',
        font: 'Arial',
        fontSize: 62,
        fontColor: '#FFFFFF',
        outlineColor: '#000000',
        outlineWidth: 0,
        marginV: 30,
        softSubtitle: false,
        language: ''
    }
};

// 模型信息配置
const MODEL_INFO = {
    'Qwen/Qwen3-ASR-1.7B': {
        name: 'Qwen3-ASR-1.7B',
        params: '1.7B 参数',
        badge2: '中文优化',
        description: '中文语音识别效果优秀，速度快，适合中文视频内容。',
        languages: 29,
        dialects: 22
    },
    'Qwen/Qwen3-ASR-0.6B': {
        name: 'Qwen3-ASR-0.6B',
        params: '0.6B 参数',
        badge2: '轻量级',
        description: '轻量级模型，资源占用低，适合快速预览。',
        languages: 29,
        dialects: 22
    },
    'openai/whisper-large-v3': {
        name: 'Whisper Large V3',
        params: '1.5B 参数',
        badge2: '多语言',
        description: '多语言支持好，精度高，适合英文或多语言视频。',
        languages: 99,
        dialects: 0
    }
};



// ============================================
// DOM 元素引用
// ============================================
const Elements = {
    // 上传相关
    uploadZone: document.getElementById('upload-zone'),
    fileInput: document.getElementById('file-input'),
    uploadPlaceholder: document.getElementById('upload-placeholder'),
    uploadPreview: document.getElementById('upload-preview'),
    fileName: document.getElementById('file-name'),
    fileSize: document.getElementById('file-size'),
    fileRemove: document.getElementById('file-remove'),
    fileProgress: document.getElementById('file-progress'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),

    // 配置相关
    modelSelect: document.getElementById('model-select'),
    modelInfo: document.getElementById('model-info'),
    subtitleFormatRadios: document.querySelectorAll('input[name="subtitle-format"]'),
    positionSelect: document.getElementById('position-select'),
    fontSelect: document.getElementById('font-select'),
    fontSize: document.getElementById('font-size'),
    fontSizeValue: document.getElementById('font-size-value'),
    fontColor: document.getElementById('font-color'),
    outlineColor: document.getElementById('outline-color'),
    outlineWidth: document.getElementById('outline-width'),
    outlineWidthValue: document.getElementById('outline-width-value'),
    marginV: document.getElementById('margin-v'),
    marginVValue: document.getElementById('margin-v-value'),
    softSubtitle: document.getElementById('soft-subtitle'),
    styleOptions: document.getElementById('style-options'),

    // 按钮
    startBtn: document.getElementById('start-btn'),

    // 预览相关
    previewVideo: document.getElementById('preview-video'),
    videoContainer: document.getElementById('video-container'),

    // 处理状态
    processingSection: document.getElementById('processing-section'),

    // 结果相关
    resultSection: document.getElementById('result-section'),
    resultVideo: document.getElementById('result-video'),
    downloadVideo: document.getElementById('download-video'),
    downloadSubtitle: document.getElementById('download-subtitle'),
    transcriptionContent: document.getElementById('transcription-content'),
    toggleTranscription: document.getElementById('toggle-transcription'),
    softSubtitleHint: document.getElementById('soft-subtitle-hint'),

    // 提示
    toastContainer: document.getElementById('toast-container')
};

// ============================================
// 工具函数
// ============================================
const Utils = {
    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // 格式化时间
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
    },

    // 获取当前时间
    getCurrentTime() {
        const now = new Date();
        return now.toTimeString().split(' ')[0];
    },

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// ============================================
// UI 更新函数
// ============================================
const UI = {
    // 显示提示消息
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
            error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type]}</div>
            <span class="toast-message">${message}</span>
        `;

        Elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    // 更新模型信息展示
    updateModelInfo(modelType) {
        const info = MODEL_INFO[modelType];
        if (!info) return;

        Elements.modelInfo.innerHTML = `
            <div class="info-card">
                <div class="info-header">
                    <span class="info-badge">${info.params}</span>
                    <span class="info-badge">${info.badge2}</span>
                </div>
                <p class="info-desc">${info.description}</p>
                <div class="info-stats">
                    <div class="stat">
                        <span class="stat-value">${info.languages}</span>
                        <span class="stat-label">支持语言</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">${info.dialects}</span>
                        <span class="stat-label">方言支持</span>
                    </div>
                </div>
            </div>
        `;
    },

    // 更新文件上传UI
    updateFileUI(file) {
        if (file) {
            Elements.uploadPlaceholder.hidden = true;
            Elements.uploadPreview.hidden = false;
            Elements.fileName.textContent = file.name;
            Elements.fileSize.textContent = Utils.formatFileSize(file.size);
            Elements.startBtn.disabled = false;

            // 显示视频预览
            const url = URL.createObjectURL(file);
            Elements.previewVideo.src = url;
            Elements.previewVideo.hidden = false;
            Elements.videoContainer.querySelector('.video-placeholder').hidden = true;
        } else {
            Elements.uploadPlaceholder.hidden = false;
            Elements.uploadPreview.hidden = true;
            Elements.fileProgress.hidden = true;
            Elements.startBtn.disabled = true;

            // 清除视频预览
            Elements.previewVideo.src = '';
            Elements.previewVideo.hidden = true;
            Elements.videoContainer.querySelector('.video-placeholder').hidden = false;
        }
    },

    // 更新上传进度
    updateUploadProgress(percentage) {
        Elements.fileProgress.hidden = false;
        Elements.progressFill.style.width = percentage + '%';
        Elements.progressText.textContent = percentage + '%';
    },

    // 显示处理状态
    showProcessing() {
        Elements.processingSection.hidden = false;
        Elements.resultSection.hidden = true;
    },

    // 隐藏处理状态
    hideProcessing() {
        Elements.processingSection.hidden = true;
    },

    // 显示结果
    showResult(result) {
        UI.hideProcessing();
        Elements.resultSection.hidden = false;

        // 显示软字幕提示
        if (Elements.softSubtitleHint) {
            Elements.softSubtitleHint.hidden = !AppState.config.softSubtitle;
        }

        // 设置视频源
        if (result.output_path) {
            Elements.resultVideo.src = `/api/output/${encodeURIComponent(result.output_path)}`;
            Elements.downloadVideo.href = `/api/download?path=${encodeURIComponent(result.output_path)}`;
        }

        // 设置字幕下载
        if (result.subtitle_path) {
            Elements.downloadSubtitle.href = `/api/download?path=${encodeURIComponent(result.subtitle_path)}`;
        }

        // 显示转录文本
        if (result.transcription && result.transcription.segments) {
            const content = result.transcription.segments.map(seg => `
                <div class="transcription-segment">
                    <div class="segment-time">[${Utils.formatTime(seg.start)} - ${Utils.formatTime(seg.end)}]</div>
                    <div class="segment-text">${seg.text}</div>
                </div>
            `).join('');
            Elements.transcriptionContent.innerHTML = content;
        }
    },

    // 重置UI
    resetUI() {
        AppState.currentFile = null;
        AppState.isProcessing = false;
        AppState.taskId = null;

        UI.updateFileUI(null);
        UI.hideProcessing();

        Elements.resultSection.hidden = true;
        Elements.startBtn.disabled = true;
    }
};

// ============================================
// 事件处理
// ============================================
const EventHandlers = {
    // 文件上传
    handleFileSelect(file) {
        if (!file) return;

        // 验证文件类型
        const validTypes = [
            'video/mp4', 'video/x-matroska', 'video/avi', 'video/quicktime', 'video/webm',
            'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac', 'audio/ogg'
        ];
        const validExtensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'];

        const isValidType = validTypes.includes(file.type);
        const isValidExt = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));

        if (!isValidType && !isValidExt) {
            UI.showToast('不支持的文件格式', 'error');
            return;
        }

        AppState.currentFile = file;
        UI.updateFileUI(file);
        UI.showToast('文件上传成功', 'success');
    },

    // 拖拽上传
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        Elements.uploadZone.classList.add('drag-over');
    },

    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        Elements.uploadZone.classList.remove('drag-over');
    },

    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        Elements.uploadZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            EventHandlers.handleFileSelect(files[0]);
        }
    },

    // 模型选择变化
    handleModelChange(e) {
        const model = e.target.value;
        AppState.config.model = model;
        UI.updateModelInfo(model);
    },

    // 字幕格式变化
    handleFormatChange(e) {
        const format = e.target.value;
        AppState.config.subtitleFormat = format;

        // 更新 radio 样式
        Elements.subtitleFormatRadios.forEach(radio => {
            radio.parentElement.classList.toggle('active', radio.checked);
        });

        // ASS格式显示样式选项
        Elements.styleOptions.style.display = format === 'ass' ? 'block' : 'none';
    },

    // 滑块变化
    handleFontSizeChange(e) {
        const value = e.target.value;
        AppState.config.fontSize = parseInt(value);
        Elements.fontSizeValue.textContent = value;
    },

    handleOutlineWidthChange(e) {
        const value = e.target.value;
        AppState.config.outlineWidth = parseInt(value);
        Elements.outlineWidthValue.textContent = value;
    },

    handleMarginVChange(e) {
        const value = e.target.value;
        AppState.config.marginV = parseInt(value);
        Elements.marginVValue.textContent = value;
    },

    // 颜色变化
    handleColorChange(e, type) {
        const value = e.target.value;
        AppState.config[type] = value;
        e.target.nextElementSibling.textContent = value.toUpperCase();
    },

    // 复选框变化
    handleSoftSubtitleChange(e) {
        AppState.config.softSubtitle = e.target.checked;
    },

    // 输入框变化
    handleInputChange(e, key) {
        AppState.config[key] = e.target.value;
    },

    // 开始处理
    async handleStart() {
        if (!AppState.currentFile || AppState.isProcessing) return;

        AppState.isProcessing = true;
        Elements.startBtn.disabled = true;
        UI.showProcessing();

        try {
            // 创建表单数据
            const formData = new FormData();
            formData.append('file', AppState.currentFile);
            formData.append('model_type', AppState.config.model);
            formData.append('subtitle_format', AppState.config.subtitleFormat);
            formData.append('position', AppState.config.position);
            formData.append('font_name', AppState.config.font);
            formData.append('font_size', AppState.config.fontSize);
            formData.append('font_color', AppState.config.fontColor);
            formData.append('outline_color', AppState.config.outlineColor);
            formData.append('outline_width', AppState.config.outlineWidth);
            formData.append('margin_v', AppState.config.marginV);
            formData.append('soft_subtitle', AppState.config.softSubtitle);

            // 发送请求
            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('处理请求失败');
            }

            const result = await response.json();

            if (result.success) {
                UI.showResult(result);
                UI.showToast('字幕生成成功！', 'success');
            } else {
                throw new Error(result.error || '处理失败');
            }

        } catch (error) {
            console.error('处理错误:', error);
            UI.showToast(error.message, 'error');
            UI.hideProcessing();
        } finally {
            AppState.isProcessing = false;
            Elements.startBtn.disabled = false;
        }
    }
};

// ============================================
// 初始化
// ============================================
function init() {
    // 绑定文件上传事件
    Elements.uploadZone.addEventListener('click', () => Elements.fileInput.click());
    Elements.fileInput.addEventListener('change', (e) => EventHandlers.handleFileSelect(e.target.files[0]));
    Elements.fileRemove.addEventListener('click', (e) => {
        e.stopPropagation();
        Elements.fileInput.value = '';
        UI.resetUI();
    });

    // 拖拽事件
    Elements.uploadZone.addEventListener('dragover', EventHandlers.handleDragOver);
    Elements.uploadZone.addEventListener('dragleave', EventHandlers.handleDragLeave);
    Elements.uploadZone.addEventListener('drop', EventHandlers.handleDrop);

    // 模型选择
    Elements.modelSelect.addEventListener('change', EventHandlers.handleModelChange);

    // 字幕格式
    Elements.subtitleFormatRadios.forEach(radio => {
        radio.addEventListener('change', EventHandlers.handleFormatChange);
    });

    // 滑块
    Elements.fontSize.addEventListener('input', EventHandlers.handleFontSizeChange);
    Elements.outlineWidth.addEventListener('input', EventHandlers.handleOutlineWidthChange);
    Elements.marginV.addEventListener('input', EventHandlers.handleMarginVChange);

    // 颜色选择
    Elements.fontColor.addEventListener('input', (e) => EventHandlers.handleColorChange(e, 'fontColor'));
    Elements.outlineColor.addEventListener('input', (e) => EventHandlers.handleColorChange(e, 'outlineColor'));

    // 复选框
    Elements.softSubtitle.addEventListener('change', EventHandlers.handleSoftSubtitleChange);

    // 下拉选择
    Elements.positionSelect.addEventListener('change', (e) => EventHandlers.handleInputChange(e, 'position'));
    Elements.fontSelect.addEventListener('change', (e) => EventHandlers.handleInputChange(e, 'font'));

    // 开始按钮
    Elements.startBtn.addEventListener('click', EventHandlers.handleStart);

    // 转录面板折叠
    Elements.toggleTranscription.addEventListener('click', () => {
        Elements.toggleTranscription.classList.toggle('collapsed');
        Elements.transcriptionContent.classList.toggle('collapsed');
    });

    // 初始化模型信息
    UI.updateModelInfo(AppState.config.model);

    // 初始化样式选项显示
    Elements.styleOptions.style.display = 'none';

    console.log('SmartCaption App Initialized');
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
