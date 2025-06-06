#!/usr/bin/env python3
"""
Gradio服务器
提供音频/视频转文本和字幕生成的Web界面
"""

import os
# 设置环境变量以解决 OpenMP 冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# 清除可能干扰 Gradio 启动的代理环境变量
proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
for var in proxy_vars:
    if var in os.environ:
        print(f"🧹 清除代理环境变量: {var}={os.environ[var]}")
        del os.environ[var]

import gradio as gr
from logger import LOG
from media_processor import process_media_file, get_media_formats_info
from file_detector import FileType, get_file_type, validate_file

def create_main_interface():
    """创建主界面"""
    
    # 获取支持的格式信息
    formats_info = get_media_formats_info()
    supported_formats_text = formats_info['description']
    
    # Markdown介绍
    description = f"""
# 🎵 音频/视频转文本和字幕生成器

## 功能特点
- **音频转录**: 支持 {', '.join(formats_info['audio_formats']).upper().replace('.', '')} 格式
- **视频转录**: 支持 {', '.join(formats_info['video_formats']).upper().replace('.', '')} 格式
- **字幕生成**: 支持 LRC 和 SRT 格式
- **双语字幕**: 支持英中双语字幕生成
- **高质量**: 基于 OpenAI Whisper 和翻译 API
"""

    with gr.Blocks(title="音频/视频转文本生成器", theme=gr.themes.Soft()) as interface:
        # gr.Markdown(description)
        
        with gr.Row():
            with gr.Column(scale=2):
                # 文件上传
                file_input = gr.File(
                    label="📁 上传音频或视频文件",
                    file_types=formats_info['all_formats'],
                    type="file"
                )
                
                # 动态选项区域
                format_dropdown = gr.Dropdown(
                    choices=["SRT", "LRC"],
                    value="SRT",
                    label="📝 字幕格式",
                    info="SRT: 标准字幕格式 | LRC: 歌词格式 (视频文件仅支持SRT)"
                )
                
                translation_checkbox = gr.Checkbox(
                    label="🌐 启用中文翻译",
                    value=False,
                    info="生成英中双语字幕"
                )
                
                process_button = gr.Button(
                    "🚀 开始处理",
                    variant="primary",
                    size="lg"
                )
            
            with gr.Column(scale=1):
                # 文件信息显示
                file_info = gr.Markdown("## 📋 文件信息\n暂未选择文件")
        
        # 结果显示区域
        with gr.Row():
            with gr.Column():
                result_text = gr.Textbox(
                    label="📄 识别结果",
                    lines=8,
                    placeholder="处理完成后这里将显示识别的文本内容..."
                )
            
            with gr.Column():
                translation_text = gr.Textbox(
                    label="🌐 翻译结果",
                    lines=8,
                    placeholder="启用翻译后这里将显示中文翻译..."
                )
        
        # 字幕内容预览
        subtitle_preview = gr.Textbox(
            label="🎬 字幕预览",
            lines=12,
            placeholder="生成的字幕内容将在这里预览..."
        )
        
        # 下载区域
        with gr.Row():
            download_file = gr.File(
                label="📥 下载字幕文件",
                interactive=False
            )
            
            processing_info = gr.Markdown("## ℹ️ 处理状态\n等待处理...")

        def update_file_info(file_path):
            """更新文件信息显示"""
            if not file_path:
                return "## 📋 文件信息\n暂未选择文件", gr.update(choices=["SRT", "LRC"])
            
            # 在新版Gradio中，file_path是一个文件对象，需要获取其name属性
            actual_file_path = file_path.name if hasattr(file_path, 'name') else file_path
            
            # 验证文件
            is_valid, file_type, error_msg = validate_file(actual_file_path)
            
            if not is_valid:
                return f"## 📋 文件信息\n❌ {error_msg}", gr.update(choices=["SRT"])
            
            # 获取文件信息
            file_size = os.path.getsize(actual_file_path) / (1024 * 1024)  # MB
            file_name = os.path.basename(actual_file_path)
            file_ext = os.path.splitext(file_name)[1].upper()
            
            info_text = f"""## 📋 文件信息
- **文件名**: {file_name}
- **类型**: {file_type.upper()} 文件
- **格式**: {file_ext}
- **大小**: {file_size:.1f} MB
- **状态**: ✅ 格式支持
"""
            
            # 根据文件类型更新格式选项
            if file_type == FileType.VIDEO:
                # 视频文件仅支持SRT
                format_choices = ["SRT"]
                info_text += "\n> **注意**: 视频文件仅支持 SRT 字幕格式"
            else:
                # 音频文件支持LRC和SRT
                format_choices = ["SRT", "LRC"]
            
            return info_text, gr.update(choices=format_choices, value=format_choices[0])

        def process_media(file_path, subtitle_format, enable_translation):
            """处理多媒体文件"""
            if not file_path:
                return (
                    "请先上传文件", 
                    "", 
                    "", 
                    None, 
                    "## ℹ️ 处理状态\n❌ 未选择文件"
                )
            
            try:
                # 更新处理状态
                yield (
                    "处理中，请稍候...",
                    "",
                    "",
                    None,
                    "## ℹ️ 处理状态\n🔄 正在处理文件..."
                )
                
                # 在新版Gradio中，file_path是一个文件对象，需要获取其name属性
                actual_file_path = file_path.name if hasattr(file_path, 'name') else file_path
                
                # 调用统一处理器
                result = process_media_file(
                    file_path=actual_file_path,
                    output_format=subtitle_format,
                    enable_translation=enable_translation
                )
                
                if result['success']:
                    # 处理成功
                    recognized_text = result.get('text', '')
                    translated_text = result.get('chinese_text', '') if enable_translation else ''
                    subtitle_content = result.get('subtitle_content', '')
                    subtitle_file = result.get('subtitle_file', None)
                    
                    # 生成处理信息
                    processing_info_text = f"""## ℹ️ 处理状态
✅ **处理完成**
- **文件类型**: {result.get('file_type', '').upper()}
- **字幕格式**: {result.get('subtitle_format', '')}
- **分段数量**: {result.get('chunks_count', 0)}
- **处理时间**: {result.get('processing_time', 0):.1f} 秒
- **双语模式**: {'是' if result.get('is_bilingual') else '否'}
"""
                    
                    yield (
                        recognized_text,
                        translated_text,
                        subtitle_content,
                        subtitle_file,
                        processing_info_text
                    )
                
                else:
                    # 处理失败
                    error_msg = result.get('error', '未知错误')
                    yield (
                        f"处理失败: {error_msg}",
                        "",
                        "",
                        None,
                        f"## ℹ️ 处理状态\n❌ 处理失败\n{error_msg}"
                    )
            
            except Exception as e:
                LOG.error(f"处理过程中发生错误: {str(e)}")
                yield (
                    f"处理过程中发生错误: {str(e)}",
                    "",
                    "",
                    None,
                    f"## ℹ️ 处理状态\n❌ 发生错误\n{str(e)}"
                )

        # 绑定事件 (必须在 gr.Blocks 上下文内部)
        file_input.change(
            update_file_info,
            inputs=[file_input],
            outputs=[file_info, format_dropdown]
        )
        
        process_button.click(
            process_media,
            inputs=[file_input, format_dropdown, translation_checkbox],
            outputs=[result_text, translation_text, subtitle_preview, download_file, processing_info]
        )
    
    return interface

if __name__ == "__main__":
    LOG.info("🚀 启动音频/视频转文本服务器...")
    
    # 检查必要组件
    try:
        from video_processor import check_ffmpeg_availability
        if not check_ffmpeg_availability():
            LOG.warning("⚠️ 未检测到 ffmpeg，视频处理功能可能不可用")
        else:
            LOG.info("✅ ffmpeg 可用，支持视频处理")
    except Exception as e:
        LOG.warning(f"⚠️ 检查 ffmpeg 时发生错误: {e}")
    
    # 创建并启动界面
    interface = create_main_interface()
    interface.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )