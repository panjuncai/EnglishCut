#!/usr/bin/env python3
"""
视频处理模块
负责视频文件的音频提取、格式检测等功能
"""

import os
import tempfile
import subprocess
from pathlib import Path
from logger import LOG

# 支持的视频格式
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']

def is_video_file(file_path):
    """
    检查文件是否为支持的视频格式
    
    参数:
    - file_path: 文件路径
    
    返回:
    - bool: 是否为视频文件
    """
    if not file_path or not os.path.exists(file_path):
        return False
    
    file_ext = os.path.splitext(file_path)[1].lower()
    return file_ext in SUPPORTED_VIDEO_FORMATS

def get_video_info(video_path):
    """
    获取视频文件信息
    
    参数:
    - video_path: 视频文件路径
    
    返回:
    - dict: 视频信息字典
    """
    try:
        # 使用 ffprobe 获取视频信息
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        video_info = json.loads(result.stdout)
        
        # 提取有用信息
        format_info = video_info.get('format', {})
        streams = video_info.get('streams', [])
        
        # 找到视频流和音频流
        video_stream = None
        audio_stream = None
        
        for stream in streams:
            if stream.get('codec_type') == 'video':
                video_stream = stream
            elif stream.get('codec_type') == 'audio':
                audio_stream = stream
        
        info = {
            'duration': float(format_info.get('duration', 0)),
            'size': int(format_info.get('size', 0)),
            'bit_rate': int(format_info.get('bit_rate', 0)),
            'has_video': video_stream is not None,
            'has_audio': audio_stream is not None,
            'video_codec': video_stream.get('codec_name') if video_stream else None,
            'audio_codec': audio_stream.get('codec_name') if audio_stream else None,
            'width': int(video_stream.get('width', 0)) if video_stream else 0,
            'height': int(video_stream.get('height', 0)) if video_stream else 0,
            'fps': eval(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0
        }
        
        LOG.info(f"📹 视频信息: 时长{info['duration']:.1f}秒, "
                f"分辨率{info['width']}x{info['height']}, "
                f"音频{'有' if info['has_audio'] else '无'}")
        
        return info
        
    except subprocess.CalledProcessError as e:
        LOG.error(f"❌ 获取视频信息失败: {e}")
        return None
    except Exception as e:
        LOG.error(f"❌ 解析视频信息失败: {e}")
        return None

def extract_audio_from_video(video_path, output_path=None):
    """
    从视频文件中提取音频
    
    参数:
    - video_path: 视频文件路径
    - output_path: 输出音频文件路径，如果为None则自动生成
    
    返回:
    - str: 提取的音频文件路径，失败返回None
    """
    try:
        # 检查视频文件是否存在
        if not os.path.exists(video_path):
            LOG.error(f"❌ 视频文件不存在: {video_path}")
            return None
        
        # 如果没有指定输出路径，则自动生成
        if output_path is None:
            # 获取视频文件名（无扩展名）
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            
            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(
                suffix=".wav", 
                delete=False,
                prefix=f"{video_name}_audio_"
            ) as temp_audio:
                audio_path = temp_audio.name
        else:
            audio_path = output_path
        
        LOG.info(f"🎬 开始从视频提取音频: {os.path.basename(video_path)}")
        LOG.info(f"📁 输出路径: {audio_path}")
        
        # 使用 ffmpeg 提取音频
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-i', video_path,  # 输入视频文件
            '-vn',  # 不包含视频流
            '-acodec', 'pcm_s16le',  # 音频编码
            '-ar', '16000',  # 采样率
            '-ac', '1',  # 单声道
            audio_path  # 输出音频文件
        ]
        
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # 检查输出文件是否存在
        if os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
            LOG.info(f"✅ 音频提取成功: {audio_path} ({file_size:.1f}MB)")
            return audio_path
        else:
            LOG.error("❌ 音频文件提取失败：输出文件不存在")
            return None
            
    except subprocess.CalledProcessError as e:
        LOG.error(f"❌ FFmpeg 音频提取失败: {e}")
        LOG.error(f"FFmpeg 错误输出: {e.stderr}")
        
        # 清理可能创建的临时文件
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
        
        return None
        
    except Exception as e:
        LOG.error(f"❌ 音频提取过程出错: {e}")
        
        # 清理可能创建的临时文件
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
        
        return None

def cleanup_temp_audio(audio_path):
    """
    清理临时音频文件
    
    参数:
    - audio_path: 音频文件路径
    """
    try:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            LOG.info(f"🧹 已清理临时音频文件: {os.path.basename(audio_path)}")
    except Exception as e:
        LOG.warning(f"⚠️ 清理临时文件失败: {e}")

def get_supported_formats():
    """
    获取支持的视频格式列表
    
    返回:
    - list: 支持的格式列表
    """
    return SUPPORTED_VIDEO_FORMATS.copy()

def check_ffmpeg_availability():
    """
    检查 FFmpeg 是否可用
    
    返回:
    - bool: FFmpeg 是否可用
    """
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        LOG.info("✅ FFmpeg 可用")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        LOG.error("❌ FFmpeg 不可用，请确保已安装 FFmpeg")
        return False 