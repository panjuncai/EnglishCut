import os
# 设置环境变量以解决 OpenMP 冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import gradio as gr
from openai_whisper import asr, save_lrc_file, save_srt_file
from logger import LOG

def process_audio_with_subtitles(audio_file, bilingual_mode, subtitle_format):
    """处理音频文件并生成文本和字幕文件"""
    try:
        if not audio_file or not os.path.exists(audio_file):
            return "请上传音频文件", None, ""
        
        # 检查音频文件格式
        file_ext = os.path.splitext(audio_file)[1].lower()
        if file_ext not in ['.wav', '.flac', '.mp3']:
            return "不支持的文件格式！请上传 WAV、FLAC 或 MP3 文件。", None, ""
        
        LOG.info(f"🎵 开始处理音频文件: {audio_file}")
        LOG.info(f"🌏 双语模式: {'开启' if bilingual_mode else '关闭'}")
        LOG.info(f"📝 字幕格式: {subtitle_format.upper()}")
        
        # 使用 OpenAI Whisper 模型进行语音识别
        result_data = asr(audio_file, return_bilingual=bilingual_mode)
        
        if isinstance(result_data, dict):
            english_text = result_data.get("english_text", "")
            chinese_text = result_data.get("chinese_text", "")
            
            # 显示文本（双语模式显示双语，单语模式显示英文）
            if bilingual_mode and chinese_text:
                display_text = f"🇬🇧 英文原文：\n{english_text}\n\n🇨🇳 中文翻译：\n{chinese_text}"
            else:
                display_text = english_text
            
            # 根据选择的格式生成字幕文件
            subtitle_file_path = None
            if subtitle_format.lower() == "lrc":
                subtitle_file_path = save_lrc_file(result_data, audio_file)
            elif subtitle_format.lower() == "srt":
                subtitle_file_path = save_srt_file(result_data, audio_file)
            
            # 生成处理信息
            processing_time = result_data.get("processing_time", 0)
            chunks_count = len(result_data.get("chunks", []))
            
            info_text = f"""
📊 处理完成！
⏱️ 处理时间: {processing_time:.1f} 秒
📝 英文长度: {len(english_text)} 字符
🌏 双语模式: {'✅ 已生成中文翻译' if bilingual_mode else '❌ 仅英文'}
📄 字幕格式: {subtitle_format.upper()}
🕐 时间戳段数: {chunks_count}
"""
            
            return display_text, subtitle_file_path, info_text
        else:
            # 兼容旧版本返回格式
            return str(result_data), None, "⚠️ 未生成时间戳信息"
            
    except Exception as e:
        LOG.error(f"❌ 音频处理错误: {e}")
        return f"处理出错：{str(e)}", None, ""

# 创建 Gradio 界面
with gr.Blocks(
    title="音频转文字 & 字幕生成器",
    css="""
    body { animation: fadeIn 2s; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    .info-box { 
        background: #f0f8ff; 
        padding: 10px; 
        border-radius: 5px; 
        border-left: 4px solid #007acc; 
    }
    """
) as demo:
    # 添加标题和说明
    gr.Markdown("""
    # 🎵 音频转文字 & 字幕生成器
    
    支持将音频文件转换为文字，并自动生成带时间戳的字幕文件。
    
    **支持格式**: WAV、FLAC、MP3  
    **字幕格式**: LRC、SRT（支持双语）  
    **特色功能**: Mac M4 GPU 加速、GPT-4o-mini 高质量翻译
    
    **双语翻译**: 使用 OpenAI GPT-4o-mini 提供高质量英中翻译
    """)

    with gr.Row():
        with gr.Column(scale=1):
            # 文件上传
            audio_input = gr.Audio(
                source="upload",
                type="filepath",
                label="📁 上传音频文件",
                show_download_button=False
            )
            
            # 双语模式选择
            bilingual_checkbox = gr.Checkbox(
                label="🌏 生成英中双语字幕",
                value=True,
                info="开启后将生成英文+中文格式的字幕"
            )
            
            # 字幕格式选择
            subtitle_format_select = gr.Dropdown(
                label="📝 选择字幕格式",
                choices=["LRC", "SRT"],
                value="LRC",
                info="LRC: 音乐播放器格式 [时间]文本 | SRT: 视频播放器格式"
            )
            
            # 处理按钮
            process_btn = gr.Button(
                "🚀 开始识别", 
                variant="primary",
                size="lg"
            )
            
            # # 处理信息显示
            # info_output = gr.Markdown(
            #     "💡 请上传音频文件开始处理",
            #     elem_classes=["info-box"]
            # )
        
        with gr.Column(scale=2):
            # 识别结果文本
            text_output = gr.Textbox(
                label="📝 识别结果",
                placeholder="识别结果将在这里显示...",
                lines=15,
                show_copy_button=True
            )
            
            # LRC文件下载
            lrc_download = gr.File(
                label="📄 下载字幕文件",
                visible=False
            )
    
    # 示例文件（如果有的话）
    gr.Markdown("""
    ### 📌 使用说明
    1. **设置API密钥**（首次使用）: 复制 `env.example` 为 `.env` 并填入您的 OpenAI API 密钥
    2. 点击"上传音频文件"选择您的音频文件
    3. 选择是否开启"🌏 生成英中双语字幕"（推荐开启）
    4. 选择字幕格式：**LRC**（音乐播放器）或 **SRT**（视频播放器）
    5. 点击"开始识别"进行处理（Mac M4 用户将享受GPU加速）
    6. 等待处理完成，查看识别结果
    7. 下载生成的字幕文件用于播放器
    
    ### 📝 字幕格式说明
    - **LRC格式**: 适用于音乐播放器，格式为 `[mm:ss.xx]歌词内容`
    - **SRT格式**: 适用于视频播放器，包含序号、时间戳和字幕内容
    - **双语模式**: LRC 显示为 `英文 // 中文`，SRT 显示为两行（英文换行中文）
    
    ### 🔑 双语功能设置
    - 需要OpenAI API密钥才能使用GPT-4o-mini翻译
    - 复制 `env.example` 为 `.env` 
    - 将 `OPENAI_API_KEY=sk-your-openai-api-key-here` 替换为您的真实密钥
    - 重启应用后生效
    """)
    
    # 绑定事件处理
    # def update_interface(audio_file):
    #     """更新界面状态"""
    #     if audio_file:
    #         return gr.update(visible=True), "🔄 点击开始识别按钮处理音频..."
    #     else:
    #         return gr.update(visible=False), "💡 请上传音频文件开始处理"
    
    def process_and_update(audio_file, bilingual_mode, subtitle_format):
        """处理音频并更新界面"""
        text, subtitle_file, info = process_audio_with_subtitles(audio_file, bilingual_mode, subtitle_format)
        
        if subtitle_file and os.path.exists(subtitle_file):
            return (
                text,
                gr.update(value=subtitle_file, visible=True),
                info
            )
        else:
            return (
                text,
                gr.update(visible=False),
                info if info else "❌ 处理失败"
            )
    
    # 事件绑定
    audio_input.change(
        # fn=update_interface,
        inputs=[audio_input],
        outputs=[lrc_download]
    )
    
    process_btn.click(
        fn=process_and_update,
        inputs=[audio_input, bilingual_checkbox, subtitle_format_select],
        outputs=[text_output, lrc_download]
    )

# 主程序入口
if __name__ == "__main__":
    # 启动Gradio应用
    demo.queue().launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True
    )