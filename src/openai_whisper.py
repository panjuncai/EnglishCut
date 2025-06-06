from transformers import pipeline
import gradio as gr
import torch
import tempfile
import os
import subprocess
import json
from datetime import timedelta
from openai import OpenAI # <-- 这里是原生的 openai 客户端
from dotenv import load_dotenv
from openai_translate import translate_text

from logger import LOG

# 智能设备检测和模型配置
def get_optimal_config():
    """根据可用硬件选择最优配置"""
    if torch.cuda.is_available():
        device = "cuda:0"
        model_name = "openai/whisper-large-v3"
        batch_size = 4
        torch.cuda.empty_cache()
        torch.backends.cudnn.benchmark = True
        LOG.info("🚀 使用 NVIDIA GPU (CUDA) 加速")
    elif torch.backends.mps.is_available():
        device = "mps" 
        model_name = "openai/whisper-base"  # 更快的模型适合 Mac
        batch_size = 8  # Mac M4 可以处理更大批次
        LOG.info("🚀 使用 Mac GPU (MPS) 加速 - 已针对 Mac M4 优化")
    else:
        device = "cpu"
        model_name = "openai/whisper-base"  # CPU 用小模型
        batch_size = 2  # CPU 用小批次
        LOG.warning("⚠️  使用 CPU 处理，速度会较慢")
    
    LOG.info(f"📊 配置: 设备={device}, 模型={model_name}, 批次大小={batch_size}")
    return device, model_name, batch_size

# 获取最优配置
device, MODEL_NAME, BATCH_SIZE = get_optimal_config()
CHUNK_LENGTH = 30  # 每个音频片段的长度（秒）

# 初始化语音识别管道
LOG.info(f"🔄 正在加载模型 {MODEL_NAME}...")
try:
    # 根据设备类型优化模型参数
    if device == "mps":
        # Mac MPS 优化配置
        model_kwargs = {
            "low_cpu_mem_usage": True,
            "use_safetensors": True,
        }
    elif device == "cuda:0":
        # CUDA 优化配置
        model_kwargs = {
            "low_cpu_mem_usage": True,
            "torch_dtype": torch.float16,  # 使用半精度加速
        }
    else:
        # CPU 配置
        model_kwargs = {"low_cpu_mem_usage": True}
    
    pipe = pipeline(
        task="automatic-speech-recognition",
        model=MODEL_NAME,
        chunk_length_s=CHUNK_LENGTH,
        device=device,
        model_kwargs=model_kwargs
    )
    LOG.info(f"✅ 模型加载成功！运行在 {device} 上")
except Exception as e:
    LOG.error(f"❌ 模型加载失败: {e}")
    # 回退到 CPU 和基础模型
    LOG.info("🔄 尝试使用 CPU 和基础模型...")
    device = "cpu"
    MODEL_NAME = "openai/whisper-base"
    BATCH_SIZE = 2
    pipe = pipeline(
        task="automatic-speech-recognition",
        model=MODEL_NAME,
        chunk_length_s=CHUNK_LENGTH,
        device=device,
        model_kwargs={"low_cpu_mem_usage": True}
    )
    LOG.info("✅ 已回退到 CPU 模式")

def convert_to_wav(input_path):
    """
    将音频文件转换为 WAV 格式并返回新文件路径。

    参数:
    - input_path: 输入的音频文件路径

    返回:
    - output_path: 转换后的 WAV 文件路径
    """
    # 创建临时 WAV 文件，用于存储转换结果
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav_file:
        output_path = temp_wav_file.name

    try:
        # 使用 ffmpeg 将音频文件转换为指定格式
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", output_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return output_path
    except subprocess.CalledProcessError as e:
        LOG.error(f"音频文件转换失败: {e}")
        # 如果转换失败，删除临时文件并抛出错误
        if os.path.exists(output_path):
            os.remove(output_path)
        raise gr.Error("音频文件转换失败。请上传有效的音频文件。")
    except FileNotFoundError:
        LOG.error("未找到 ffmpeg 可执行文件。请确保已安装 ffmpeg。")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise gr.Error("服务器配置错误，缺少 ffmpeg。请联系管理员。")

def asr(audio_file, task="transcribe", return_bilingual=False):
    """
    对音频文件进行语音识别或翻译。

    参数:
    - audio_file: 输入的音频文件路径
    - task: 任务类型（"transcribe" 表示转录，"translate" 表示翻译）
    - return_bilingual: 是否返回双语结果（英文+中文翻译）

    返回:
    - 识别或翻译后的结果数据
    """
    import time
    start_time = time.time()
    
    # 获取音频文件信息
    file_size = os.path.getsize(audio_file) / (1024 * 1024)  # MB
    LOG.info(f"🎵 开始处理音频文件: {os.path.basename(audio_file)} ({file_size:.1f}MB)")
    
    # 转换音频文件为 WAV 格式
    LOG.info("🔄 转换音频格式...")
    wav_file = convert_to_wav(audio_file)
    conversion_time = time.time() - start_time
    LOG.info(f"✅ 音频转换完成 ({conversion_time:.1f}秒)")

    try:
        # 使用管道进行转录或翻译
        LOG.info(f"🤖 开始语音识别 (设备: {device}, 批次: {BATCH_SIZE})...")
        inference_start = time.time()
        
        # 首先进行英文转录
        result = pipe(
            wav_file,
            batch_size=BATCH_SIZE,
            generate_kwargs={"task": "transcribe", "language": "en"},
            return_timestamps=True
        )
        
        english_text = result["text"]
        chunks = result.get("chunks", [])
        
        # 如果需要双语，翻译英文为中文
        chinese_chunks = []
        chinese_text = ""
        
        if return_bilingual:
            LOG.info("🌏 开始使用GPT-4o-mini生成中文翻译...")
            
            # 翻译整体文本
            chinese_text = translate_text(english_text)
            
            # 翻译每个时间戳片段
            for chunk in chunks:
                english_chunk_text = chunk.get("text", "").strip()
                if english_chunk_text:
                    chinese_chunk_text = translate_text(english_chunk_text)
                    chinese_chunks.append({
                        "text": chinese_chunk_text,
                        "timestamp": chunk.get("timestamp", [None, None])
                    })
        
        inference_time = time.time() - inference_start
        total_time = time.time() - start_time
        
        # 计算音频时长（估算）
        audio_duration = len(english_text.split()) * 0.6  # 粗略估算：每个单词0.6秒
        speed_ratio = audio_duration / total_time if total_time > 0 else 0
        
        LOG.info(f"✅ 识别完成! 总时长: {total_time:.1f}秒, 推理: {inference_time:.1f}秒")
        LOG.info(f"⚡ 处理速度: {speed_ratio:.1f}x 实时速度")
        LOG.info(f"📝 英文结果 ({len(english_text)} 字符): {english_text[:100]}...")
        if return_bilingual:
            LOG.info(f"🌏 中文翻译 ({len(chinese_text)} 字符): {chinese_text[:100]}...")
        LOG.info(f"🕐 时间戳片段数: {len(chunks)}")

        return {
            "english_text": english_text,
            "chinese_text": chinese_text if return_bilingual else "",
            "english_chunks": chunks,
            "chinese_chunks": chinese_chunks if return_bilingual else [],
            "text": english_text,  # 保持兼容性
            "chunks": chunks,     # 保持兼容性
            "processing_time": total_time,
            "is_bilingual": return_bilingual
        }
    except Exception as e:
        LOG.error(f"❌ 处理音频文件时出错: {e}")
        raise gr.Error(f"处理音频文件时出错：{str(e)}")
    finally:
        # 删除临时转换后的 WAV 文件
        if os.path.exists(wav_file):
            os.remove(wav_file)

def format_time_lrc(seconds):
    """将秒数转换为LRC格式时间戳 [mm:ss.xx]"""
    if seconds is None:
        return "[00:00.00]"
    
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"

def align_bilingual_chunks(english_chunks, chinese_chunks):
    """对齐英文和中文字幕块"""
    aligned_chunks = []
    
    # 直接使用英文时间戳和对应的中文翻译
    for i, eng_chunk in enumerate(english_chunks):
        english_text = eng_chunk.get("text", "").strip()
        timestamp = eng_chunk.get("timestamp", [None, None])
        
        # 获取对应的中文翻译
        if i < len(chinese_chunks):
            chinese_text = chinese_chunks[i].get("text", "").strip()
        else:
            chinese_text = ""
        
        aligned_chunks.append({
            "timestamp": timestamp,
            "english": english_text,
            "chinese": chinese_text
        })
    
    return aligned_chunks

def generate_lrc_content(result_data, audio_filename="audio"):
    """生成LRC格式字幕内容，支持双语"""
    if not isinstance(result_data, dict):
        return ""
    
    is_bilingual = result_data.get("is_bilingual", False)
    processing_time = result_data.get("processing_time", 0)
    
    lrc_lines = []
    
    # LRC文件头部信息
    lrc_lines.append("[ti:Audio Transcription]")
    lrc_lines.append(f"[ar:Generated by EnglishCut]")
    lrc_lines.append(f"[al:{audio_filename}]")
    lrc_lines.append(f"[by:OpenAI Whisper]")
    lrc_lines.append(f"[offset:0]")
    lrc_lines.append("")
    
    if is_bilingual:
        # 双语模式
        english_chunks = result_data.get("english_chunks", [])
        chinese_chunks = result_data.get("chinese_chunks", [])
        
        if english_chunks:
            # 对齐英中字幕
            aligned_chunks = align_bilingual_chunks(english_chunks, chinese_chunks)
            
            for chunk in aligned_chunks:
                timestamp = chunk.get("timestamp", [None, None])
                english_text = chunk.get("english", "")
                chinese_text = chunk.get("chinese", "")
                
                if english_text and timestamp[0] is not None:
                    time_tag = format_time_lrc(timestamp[0])
                    if chinese_text:
                        # 双语格式：英文 // 中文
                        lrc_lines.append(f"{time_tag}{english_text} // {chinese_text}")
                    else:
                        # 只有英文
                        lrc_lines.append(f"{time_tag}{english_text}")
        else:
            # 没有时间戳，使用整段文本
            english_text = result_data.get("english_text", "")
            chinese_text = result_data.get("chinese_text", "")
            if english_text:
                bilingual_text = f"{english_text} // {chinese_text}" if chinese_text else english_text
                lrc_lines.append("[00:00.00]" + bilingual_text)
    else:
        # 单语模式（保持原有逻辑）
        text = result_data.get("text", "")
        chunks = result_data.get("chunks", [])
        
        if chunks:
            for chunk in chunks:
                timestamp = chunk.get("timestamp", [None, None])
                chunk_text = chunk.get("text", "").strip()
                
                if chunk_text and timestamp[0] is not None:
                    time_tag = format_time_lrc(timestamp[0])
                    lrc_lines.append(f"{time_tag}{chunk_text}")
        else:
            # 如果没有时间戳，添加整个文本
            lrc_lines.append("[00:00.00]" + text)
    
    # 添加结束标记
    lrc_lines.append("")
    lrc_lines.append(f"[99:59.99]Generated in {processing_time:.1f} seconds")
    
    return "\n".join(lrc_lines)

def save_lrc_file(result_data, audio_filepath):
    """保存LRC字幕文件并返回文件路径"""
    try:
        # 获取音频文件名（不含扩展名）
        audio_name = os.path.splitext(os.path.basename(audio_filepath))[0]
        
        # 生成LRC内容
        lrc_content = generate_lrc_content(result_data, audio_name)
        
        # 创建LRC文件路径
        lrc_filename = f"{audio_name}_subtitle.lrc"
        lrc_filepath = os.path.join(tempfile.gettempdir(), lrc_filename)
        
        # 写入LRC文件
        with open(lrc_filepath, 'w', encoding='utf-8') as f:
            f.write(lrc_content)
        
        LOG.info(f"📁 LRC字幕文件已生成: {lrc_filepath}")
        return lrc_filepath
        
    except Exception as e:
        LOG.error(f"❌ 生成LRC文件失败: {e}")
        return None

def format_time_srt(seconds):
    """将秒数转换为SRT格式时间戳 [hh:mm:ss,mmm]"""
    if seconds is None:
        return "00:00:00,000"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    milliseconds = int((secs % 1) * 1000)
    secs = int(secs)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def generate_srt_content(result_data, audio_filename="audio"):
    """生成SRT格式字幕内容，支持双语"""
    if not isinstance(result_data, dict):
        return ""
    
    is_bilingual = result_data.get("is_bilingual", False)
    
    srt_lines = []
    subtitle_index = 1
    
    if is_bilingual:
        # 双语模式
        english_chunks = result_data.get("english_chunks", [])
        chinese_chunks = result_data.get("chinese_chunks", [])
        
        if english_chunks:
            # 对齐英中字幕
            aligned_chunks = align_bilingual_chunks(english_chunks, chinese_chunks)
            
            for chunk in aligned_chunks:
                timestamp = chunk.get("timestamp", [None, None])
                english_text = chunk.get("english", "")
                chinese_text = chunk.get("chinese", "")
                
                if english_text and timestamp[0] is not None and timestamp[1] is not None:
                    start_time = format_time_srt(timestamp[0])
                    end_time = format_time_srt(timestamp[1])
                    
                    # SRT 格式：序号、时间戳、字幕内容、空行
                    srt_lines.append(str(subtitle_index))
                    srt_lines.append(f"{start_time} --> {end_time}")
                    
                    if chinese_text:
                        # 双语格式：英文换行中文
                        srt_lines.append(english_text)
                        srt_lines.append(chinese_text)
                    else:
                        # 只有英文
                        srt_lines.append(english_text)
                    
                    srt_lines.append("")  # 空行分隔
                    subtitle_index += 1
        else:
            # 没有时间戳，使用整段文本
            english_text = result_data.get("english_text", "")
            chinese_text = result_data.get("chinese_text", "")
            if english_text:
                srt_lines.append("1")
                srt_lines.append("00:00:00,000 --> 00:00:10,000")
                srt_lines.append(english_text)
                if chinese_text:
                    srt_lines.append(chinese_text)
                srt_lines.append("")
    else:
        # 单语模式（保持原有逻辑）
        text = result_data.get("text", "")
        chunks = result_data.get("chunks", [])
        
        if chunks:
            for chunk in chunks:
                timestamp = chunk.get("timestamp", [None, None])
                chunk_text = chunk.get("text", "").strip()
                
                if chunk_text and timestamp[0] is not None and timestamp[1] is not None:
                    start_time = format_time_srt(timestamp[0])
                    end_time = format_time_srt(timestamp[1])
                    
                    srt_lines.append(str(subtitle_index))
                    srt_lines.append(f"{start_time} --> {end_time}")
                    srt_lines.append(chunk_text)
                    srt_lines.append("")  # 空行分隔
                    subtitle_index += 1
        else:
            # 如果没有时间戳，添加整个文本
            srt_lines.append("1")
            srt_lines.append("00:00:00,000 --> 00:00:10,000")
            srt_lines.append(text)
            srt_lines.append("")
    
    return "\n".join(srt_lines)

def save_srt_file(result_data, audio_filepath):
    """保存SRT字幕文件并返回文件路径"""
    try:
        # 获取音频文件名（不含扩展名）
        audio_name = os.path.splitext(os.path.basename(audio_filepath))[0]
        
        # 生成SRT内容
        srt_content = generate_srt_content(result_data, audio_name)
        
        # 创建SRT文件路径
        srt_filename = f"{audio_name}_subtitle.srt"
        srt_filepath = os.path.join(tempfile.gettempdir(), srt_filename)
        
        # 写入SRT文件
        with open(srt_filepath, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        LOG.info(f"📁 SRT字幕文件已生成: {srt_filepath}")
        return srt_filepath
        
    except Exception as e:
        LOG.error(f"❌ 生成SRT文件失败: {e}")
        return None

def transcribe(inputs, task):
    """
    将音频文件转录或翻译为文本。

    参数:
    - inputs: 上传的音频文件路径
    - task: 任务类型（"transcribe" 表示转录，"translate" 表示翻译）

    返回:
    - 识别的文本内容
    """
    LOG.info(f"[上传的音频文件]: {inputs}")

    # 检查是否提供了音频文件
    if not inputs or not os.path.exists(inputs):
        raise gr.Error("未提交音频文件！请在提交请求前上传或录制音频文件。")

    # 检查音频文件格式
    file_ext = os.path.splitext(inputs)[1].lower()
    if file_ext not in ['.wav', '.flac', '.mp3']:
        LOG.error(f"文件格式错误：{inputs}")
        raise gr.Error("不支持的文件格式！请上传 WAV、FLAC 或 MP3 文件。")

    # 调用语音识别或翻译函数
    return asr(inputs, task)

# 定义麦克风输入的接口实例，可供外部模块调用
mf_transcribe = gr.Interface(
    fn=transcribe,  # 执行转录的函数
    inputs=[
        gr.Audio(source="microphone", type="filepath", label="麦克风输入"),  # 使用麦克风录制的音频输入
        gr.Radio(choices=["transcribe", "translate"], label="任务类型", value="transcribe"),  # 任务选择（转录或翻译）
    ],
    outputs=gr.Textbox(label="识别结果"),  # 输出为文本
    title="Whisper Large V3: 语音识别",  # 接口标题
    description="使用麦克风录制音频并进行语音识别或翻译。",  # 接口描述
)

# 定义文件上传的接口实例，用于处理上传的音频文件
file_transcribe = gr.Interface(
    fn=transcribe,  # 执行转录的函数
    inputs=[
        gr.Audio(source="upload", type="filepath", label="上传音频文件"),  # 上传的音频文件输入
        gr.Radio(choices=["transcribe", "translate"], label="任务类型", value="transcribe"),  # 任务选择（转录或翻译）
    ],
    outputs=gr.Textbox(label="识别结果"),  # 输出为文本
    title="Whisper Large V3: 转录音频文件",  # 接口标题
    description="上传音频文件（WAV、FLAC 或 MP3）并进行语音识别或翻译。",  # 接口描述
)

# 仅当此脚本作为主程序运行时，执行 Gradio 应用的启动代码
if __name__ == "__main__":
    # 创建一个 Gradio Blocks 实例，用于包含多个接口
    with gr.Blocks() as demo:
        # 使用 TabbedInterface 将 mf_transcribe 和 file_transcribe 接口分别放置在 "麦克风" 和 "音频文件" 选项卡中
        gr.TabbedInterface(
            [mf_transcribe, file_transcribe],
            ["麦克风", "音频文件"]
        )

    # 启动Gradio应用，允许队列功能，并通过 HTTPS 访问
    demo.queue().launch(
        share=False,
        server_name="127.0.0.1",
        # auth=("django", "1234") # ⚠️注意：记住修改密码
    )
