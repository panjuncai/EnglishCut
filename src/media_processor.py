#!/usr/bin/env python3
"""
多媒体处理器
统一处理音频和视频文件，提供转录和字幕生成功能
"""

import os
import tempfile
from pathlib import Path
from logger import LOG
from file_detector import FileType, get_file_type, validate_file, get_file_info
from video_processor import extract_audio_from_video, cleanup_temp_audio, check_ffmpeg_availability
from openai_whisper import asr, format_time_lrc, generate_lrc_content, save_lrc_file, format_time_srt, generate_srt_content, save_srt_file
from openai_translate import translate_text

class MediaProcessor:
    """多媒体处理器类"""
    
    def __init__(self):
        """初始化处理器"""
        self.temp_files = []  # 记录临时文件，用于清理
        LOG.info("🎵 多媒体处理器初始化完成")
    
    def process_file(self, file_path, output_format="SRT", enable_translation=False):
        """
        处理多媒体文件
        
        参数:
        - file_path: 输入文件路径
        - output_format: 输出格式 ("LRC" 或 "SRT")
        - enable_translation: 是否启用翻译
        
        返回:
        - dict: 处理结果
        """
        try:
            # 验证文件
            is_valid, file_type, error_msg = validate_file(file_path)
            if not is_valid:
                return self._create_error_result(error_msg)
            
            # 获取文件信息
            file_info = get_file_info(file_path)
            LOG.info(f"🔍 开始处理 {file_type} 文件: {file_info['name']}")
            
            # 确定音频文件路径
            audio_path = self._prepare_audio_file(file_path, file_type)
            if not audio_path:
                return self._create_error_result("音频准备失败")
            
            # 执行语音识别
            LOG.info("🎤 开始语音识别...")
            recognition_result = asr(audio_path, task="transcribe", return_bilingual=enable_translation)
            
            if not recognition_result:
                self._cleanup_temp_files()
                return self._create_error_result("语音识别失败")
            
            # 生成字幕文件
            subtitle_result = self._generate_subtitles(
                recognition_result, 
                file_info, 
                output_format,
                enable_translation
            )
            
            # 清理临时文件
            self._cleanup_temp_files()
            
            return subtitle_result
            
        except Exception as e:
            LOG.error(f"❌ 处理文件时发生错误: {str(e)}")
            self._cleanup_temp_files()
            return self._create_error_result(f"处理失败: {str(e)}")
    
    def _prepare_audio_file(self, file_path, file_type):
        """
        准备音频文件
        
        参数:
        - file_path: 原始文件路径
        - file_type: 文件类型
        
        返回:
        - str: 音频文件路径
        """
        if file_type == FileType.AUDIO:
            return file_path
        
        elif file_type == FileType.VIDEO:
            # 检查 ffmpeg 可用性
            if not check_ffmpeg_availability():
                LOG.error("❌ 未找到 ffmpeg，无法处理视频文件")
                return None
            
            # 提取音频
            LOG.info("🎬 从视频中提取音频...")
            temp_audio = self._create_temp_audio_path()
            
            extracted_audio = extract_audio_from_video(file_path, temp_audio)
            if extracted_audio:
                self.temp_files.append(extracted_audio)
                return extracted_audio
            else:
                return None
        
        return None
    
    def _create_temp_audio_path(self):
        """创建临时音频文件路径"""
        temp_dir = tempfile.gettempdir()
        temp_filename = f"temp_audio_{os.getpid()}.wav"
        return os.path.join(temp_dir, temp_filename)
    
    def _generate_subtitles(self, recognition_result, file_info, output_format, is_bilingual):
        """
        生成字幕文件
        
        参数:
        - recognition_result: 识别结果
        - file_info: 文件信息
        - output_format: 输出格式
        - is_bilingual: 是否双语
        
        返回:
        - dict: 字幕生成结果
        """
        try:
            # 生成输出文件路径
            base_name = os.path.splitext(file_info['name'])[0]
            
            if output_format.upper() == "LRC":
                # 生成LRC字幕
                lrc_content = generate_lrc_content(recognition_result, base_name)
                lrc_path = save_lrc_file(recognition_result, file_info['path'])
                
                return {
                    'success': True,
                    'file_type': file_info['type'],
                    'subtitle_format': 'LRC',
                    'subtitle_file': lrc_path,
                    'subtitle_content': lrc_content,
                    'is_bilingual': is_bilingual,
                    'text': recognition_result.get('english_text', recognition_result.get('text', '')),
                    'chinese_text': recognition_result.get('chinese_text', ''),
                    'chunks_count': len(recognition_result.get('chunks', [])),
                    'processing_time': recognition_result.get('processing_time', 0)
                }
            
            elif output_format.upper() == "SRT":
                # 生成SRT字幕
                srt_content = generate_srt_content(recognition_result, base_name)
                srt_path = save_srt_file(recognition_result, file_info['path'])
                
                return {
                    'success': True,
                    'file_type': file_info['type'],
                    'subtitle_format': 'SRT',
                    'subtitle_file': srt_path,
                    'subtitle_content': srt_content,
                    'is_bilingual': is_bilingual,
                    'text': recognition_result.get('english_text', recognition_result.get('text', '')),
                    'chinese_text': recognition_result.get('chinese_text', ''),
                    'chunks_count': len(recognition_result.get('chunks', [])),
                    'processing_time': recognition_result.get('processing_time', 0)
                }
            
            else:
                return self._create_error_result(f"不支持的输出格式: {output_format}")
                
        except Exception as e:
            LOG.error(f"❌ 生成字幕时发生错误: {str(e)}")
            return self._create_error_result(f"字幕生成失败: {str(e)}")
    
    def _create_error_result(self, error_message):
        """创建错误结果"""
        return {
            'success': False,
            'error': error_message,
            'file_type': 'unknown',
            'subtitle_format': None,
            'subtitle_file': None,
            'subtitle_content': None,
            'is_bilingual': False,
            'text': '',
            'chinese_text': '',
            'chunks_count': 0,
            'processing_time': 0
        }
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    LOG.info(f"🗑️ 清理临时文件: {temp_file}")
            except Exception as e:
                LOG.warning(f"⚠️ 清理临时文件失败: {temp_file}, 错误: {str(e)}")
        
        self.temp_files.clear()
    
    def get_supported_formats_info(self):
        """
        获取支持的格式信息
        
        返回:
        - dict: 格式信息
        """
        from file_detector import get_supported_formats, format_supported_formats_text
        
        formats = get_supported_formats()
        
        return {
            'audio_formats': formats['audio'],
            'video_formats': formats['video'],
            'all_formats': formats['all'],
            'description': format_supported_formats_text(),
            'subtitle_formats': ['LRC', 'SRT'],
            'video_subtitle_note': '视频文件仅支持 SRT 格式字幕'
        }

# 全局处理器实例
media_processor = MediaProcessor()

def process_media_file(file_path, output_format="SRT", enable_translation=False):
    """
    处理多媒体文件的便捷函数
    
    参数:
    - file_path: 文件路径
    - output_format: 输出格式
    - enable_translation: 是否启用翻译
    
    返回:
    - dict: 处理结果
    """
    return media_processor.process_file(file_path, output_format, enable_translation)

def get_media_formats_info():
    """获取媒体格式信息"""
    return media_processor.get_supported_formats_info() 