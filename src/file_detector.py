#!/usr/bin/env python3
"""
文件类型检测模块
负责检测和分类音频、视频文件格式
"""

import os
import sys
# 添加当前目录到系统路径，以支持模块导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from logger import LOG

# 支持的音频格式
SUPPORTED_AUDIO_FORMATS = ['.wav', '.flac', '.mp3', '.aac', '.ogg', '.m4a']

# 支持的视频格式
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']

class FileType:
    """文件类型枚举"""
    UNKNOWN = "unknown"
    AUDIO = "audio"
    VIDEO = "video"

def get_file_type(file_path):
    """
    检测文件类型
    
    参数:
    - file_path: 文件路径
    
    返回:
    - str: 文件类型 (FileType.AUDIO, FileType.VIDEO, FileType.UNKNOWN)
    """
    if not file_path or not os.path.exists(file_path):
        return FileType.UNKNOWN
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext in SUPPORTED_AUDIO_FORMATS:
        return FileType.AUDIO
    elif file_ext in SUPPORTED_VIDEO_FORMATS:
        return FileType.VIDEO
    else:
        return FileType.UNKNOWN

def is_audio_file(file_path):
    """
    检查是否为音频文件
    
    参数:
    - file_path: 文件路径
    
    返回:
    - bool: 是否为音频文件
    """
    return get_file_type(file_path) == FileType.AUDIO

def is_video_file(file_path):
    """
    检查是否为视频文件
    
    参数:
    - file_path: 文件路径
    
    返回:
    - bool: 是否为视频文件
    """
    return get_file_type(file_path) == FileType.VIDEO

def is_supported_file(file_path):
    """
    检查是否为支持的文件格式
    
    参数:
    - file_path: 文件路径
    
    返回:
    - bool: 是否为支持的格式
    """
    return get_file_type(file_path) != FileType.UNKNOWN

def get_file_info(file_path):
    """
    获取文件基本信息
    
    参数:
    - file_path: 文件路径
    
    返回:
    - dict: 文件信息字典
    """
    if not file_path or not os.path.exists(file_path):
        return None
    
    file_stat = os.stat(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()
    file_type = get_file_type(file_path)
    
    info = {
        'path': file_path,
        'name': os.path.basename(file_path),
        'extension': file_ext,
        'type': file_type,
        'size': file_stat.st_size,
        'size_mb': file_stat.st_size / (1024 * 1024),
        'modified_time': file_stat.st_mtime
    }
    
    LOG.info(f"📁 文件信息: {info['name']} ({info['type']}, {info['size_mb']:.1f}MB)")
    
    return info

def get_supported_formats():
    """
    获取所有支持的格式
    
    返回:
    - dict: 包含音频和视频格式的字典
    """
    return {
        'audio': SUPPORTED_AUDIO_FORMATS.copy(),
        'video': SUPPORTED_VIDEO_FORMATS.copy(),
        'all': SUPPORTED_AUDIO_FORMATS + SUPPORTED_VIDEO_FORMATS
    }

def format_supported_formats_text():
    """
    格式化支持的格式为显示文本
    
    返回:
    - str: 格式化的文本
    """
    formats = get_supported_formats()
    
    audio_text = ', '.join(formats['audio']).upper().replace('.', '')
    video_text = ', '.join(formats['video']).upper().replace('.', '')
    
    return f"音频: {audio_text} | 视频: {video_text}"

def validate_file(file_path):
    """
    验证文件是否有效且支持
    
    参数:
    - file_path: 文件路径
    
    返回:
    - tuple: (is_valid, file_type, error_message)
    """
    if not file_path:
        return False, FileType.UNKNOWN, "未提供文件"
    
    if not os.path.exists(file_path):
        return False, FileType.UNKNOWN, "文件不存在"
    
    file_type = get_file_type(file_path)
    
    if file_type == FileType.UNKNOWN:
        supported = format_supported_formats_text()
        return False, FileType.UNKNOWN, f"不支持的文件格式。支持的格式: {supported}"
    
    # 检查文件大小（可选的大小限制）
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 500:  # 500MB 限制
        LOG.warning(f"⚠️ 文件较大: {file_size_mb:.1f}MB，处理可能需要较长时间")
    
    return True, file_type, "" 