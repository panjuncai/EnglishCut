import os
# 设置环境变量以解决 OpenMP 冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import gradio as gr
from openai_whisper import asr, transcribe
from logger import LOG

def process_audio(message, history):
    try:
        texts = []
        
        # 获取上传的文件列表，处理音频文件
        for uploaded_file in message:
            if isinstance(uploaded_file, str) and os.path.exists(uploaded_file):
                file_ext = os.path.splitext(uploaded_file)[1].lower()
                if file_ext in ('.wav', '.flac', '.mp3'):
                    LOG.debug(f"[音频文件]: {uploaded_file}")
                    # 使用 OpenAI Whisper 模型进行语音识别
                    audio_text = asr(uploaded_file)
                    texts.append(audio_text)
                else:
                    LOG.debug(f"[格式不支持]: {uploaded_file}")

        # 如果有识别结果，返回文本
        if texts:
            return "\n".join(texts)
        else:
            return "请上传音频文件（支持 .wav、.flac、.mp3 格式）"
            
    except Exception as e:
        LOG.error(f"[音频处理错误]: {e}")
        raise gr.Error(f"处理出错，请重试")

# 创建 Gradio 界面
with gr.Blocks(
    title="音频转文字",
    css="""
    body { animation: fadeIn 2s; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    """
) as demo:
    # 添加标题
    gr.Markdown("## 音频转文字工具")

    with gr.Row():
        # 创建文件上传组件
        audio_input = gr.Audio(
            source="upload",
            type="filepath",
            label="上传音频文件"
        )
        
        # 创建文本输出组件
        text_output = gr.Textbox(
            label="识别结果",
            placeholder="这里将显示识别结果...",
            lines=5
        )
    
    # 创建提交按钮
    submit_btn = gr.Button("开始识别")
    
    # 绑定事件处理
    submit_btn.click(
        fn=lambda x: process_audio([x] if x else [], []),
        inputs=[audio_input],
        outputs=[text_output]
    )

# 主程序入口
if __name__ == "__main__":
    # 启动Gradio应用
    demo.queue().launch(
        share=False,
        server_name="127.0.0.1"
    )