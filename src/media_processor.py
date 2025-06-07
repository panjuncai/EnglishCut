#!/usr/bin/env python3
"""
多媒体处理器
统一处理音频和视频文件，提供转录和字幕生成功能
"""

import os
import tempfile
import subprocess
import time
from pathlib import Path
from logger import LOG
from file_detector import FileType, validate_file, get_file_info
from video_processor import extract_audio_from_video, check_ffmpeg_availability
from openai_whisper import asr, generate_lrc_content, save_lrc_file, generate_srt_content, save_srt_file
try:
    from database import db_manager
except ImportError:
    # 如果在其他目录运行，尝试相对导入
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from database import db_manager

class MediaProcessor:
    """多媒体处理器类"""
    
    def __init__(self):
        """初始化处理器"""
        self.temp_files = []  # 记录临时文件，用于清理
        # 创建专用的临时目录用于存放处理后的视频
        self.processed_videos_dir = os.path.join(tempfile.gettempdir(), "englishcut_processed_videos")
        os.makedirs(self.processed_videos_dir, exist_ok=True)
        LOG.info("🎵 多媒体处理器初始化完成")
    
    def process_file(self, file_path, output_format="SRT", enable_translation=False, enable_short_subtitles=False):
        """
        处理多媒体文件
        
        参数:
        - file_path: 输入文件路径
        - output_format: 输出格式 ("LRC" 或 "SRT")
        - enable_translation: 是否启用翻译
        - enable_short_subtitles: 是否启用短字幕模式
        
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
            
            # 如果是视频文件，先进行9:16格式处理
            processed_video_path = None
            if file_type == FileType.VIDEO:
                processed_video_path = self._preprocess_video_to_9_16(file_path, file_info['name'])
                if not processed_video_path:
                    LOG.warning("⚠️ 视频9:16预处理失败，将使用原始视频继续处理")
                else:
                    LOG.info(f"✅ 视频已预处理为9:16格式: {processed_video_path}")
                    # 更新文件信息中的路径，但保留原始路径作为参考
                    file_info['original_path'] = file_info['path']
                    file_info['path'] = processed_video_path
            
            # 确定音频文件路径
            audio_path = self._prepare_audio_file(file_info['path'], file_type)
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
                enable_translation,
                enable_short_subtitles
            )
            
            # 保存到数据库
            self._save_to_database(file_info, recognition_result, subtitle_result, enable_translation, processed_video_path)
            
            # 清理临时文件
            self._cleanup_temp_files()
            
            return subtitle_result
            
        except Exception as e:
            LOG.error(f"❌ 处理文件时发生错误: {str(e)}")
            self._cleanup_temp_files()
            return self._create_error_result(f"处理失败: {str(e)}")
    
    def _preprocess_video_to_9_16(self, video_path, video_name):
        """
        对视频进行9:16比例预处理
        
        参数:
        - video_path: 原始视频路径
        - video_name: 视频名称
        
        返回:
        - str: 处理后的视频路径，失败返回None
        """
        try:
            # 检查ffmpeg是否可用
            if not check_ffmpeg_availability():
                LOG.error("❌ 未找到ffmpeg，无法预处理视频")
                return None
            
            # 生成输出文件路径
            base_name = os.path.splitext(video_name)[0]
            # 使用更简洁的命名格式: 原文件名_1.mp4
            output_filename = f"{base_name}_1.mp4"
            # 确保input目录存在
            input_dir = "input"
            os.makedirs(input_dir, exist_ok=True)
            # 保存到input目录下 (使用绝对路径)
            rel_output_path = os.path.join(input_dir, output_filename)
            output_path = os.path.abspath(rel_output_path)
            
            LOG.info(f"🔄 开始对视频进行9:16比例预处理: {video_path}")
            
            # 使用ffmpeg对视频进行9:16处理，应用pre_process.py中的处理逻辑
            # 从原视频中央挖出9:16比例的部分，忽略底部1/5的广告字幕
            cmd = [
                'ffmpeg', '-y',  # 覆盖输出文件
                '-i', video_path,  # 输入视频
                '-vf', "crop=ih*4/5*9/16:ih*4/5:iw/2-ih*4/5*9/16/2:0,scale=720:1280",  # 从中心裁剪9:16比例，避开底部1/5区域
                '-c:a', 'copy',  # 音频直接复制
                '-preset', 'medium',  # 编码预设
                '-crf', '23',  # 质量控制
                output_path
            ]
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                LOG.info(f"✅ 视频9:16预处理成功: {output_path}")
                return output_path
            else:
                LOG.error(f"❌ 视频9:16预处理失败: {stderr}")
                return None
                
        except Exception as e:
            LOG.error(f"❌ 视频9:16预处理出错: {str(e)}")
            return None
    
    def _save_to_database(self, file_info, recognition_result, subtitle_result, is_bilingual, processed_video_path=None):
        """
        保存处理结果到数据库
        
        参数:
        - file_info: 文件信息
        - recognition_result: 识别结果  
        - subtitle_result: 字幕生成结果
        - is_bilingual: 是否双语
        - processed_video_path: 预处理后的视频路径
        """
        try:
            LOG.info(f"🔄 开始保存到数据库: 文件={file_info.get('name', 'Unknown')}, 双语={is_bilingual}")
            
            # 准备文件路径信息
            original_path = file_info.get('original_path', file_info['path'])
            
            # 1. 创建媒体系列记录
            series_id = db_manager.create_series(
                name=file_info['name'],
                file_path=original_path,  # 保存原始文件路径
                file_type=file_info['type'],
                duration=recognition_result.get('audio_duration')
            )
            LOG.info(f"📁 创建媒体系列成功: ID={series_id}")
            
            # 如果有预处理的9:16视频，更新系列信息
            if processed_video_path:
                db_manager.update_series_video_info(
                    series_id,
                    new_name=os.path.basename(processed_video_path),
                    new_file_path=processed_video_path
                )
                LOG.info(f"🔄 更新系列的9:16预处理视频信息: {processed_video_path}")
            
            # 2. 准备字幕数据
            subtitles_data = []
            chunks = recognition_result.get('chunks', [])
            LOG.info(f"📝 处理字幕数据: {len(chunks)} 个chunks")
            
            if is_bilingual:
                # 双语模式
                english_chunks = recognition_result.get('english_chunks', [])
                chinese_chunks = recognition_result.get('chinese_chunks', [])
                LOG.info(f"🌐 双语模式: 英文chunks={len(english_chunks)}, 中文chunks={len(chinese_chunks)}")
                
                for i, chunk in enumerate(chunks):
                    timestamp = chunk.get('timestamp', [0, 0])
                    english_text = english_chunks[i].get('text', '') if i < len(english_chunks) else ''
                    chinese_text = chinese_chunks[i].get('text', '') if i < len(chinese_chunks) else ''
                    
                    subtitles_data.append({
                        'begin_time': timestamp[0],
                        'end_time': timestamp[1],
                        'english_text': english_text,
                        'chinese_text': chinese_text
                    })
            else:
                # 单语模式
                LOG.info("📝 单语模式处理")
                for chunk in chunks:
                    timestamp = chunk.get('timestamp', [0, 0])
                    text = chunk.get('text', '')
                    
                    subtitles_data.append({
                        'begin_time': timestamp[0],
                        'end_time': timestamp[1],
                        'english_text': text,
                        'chinese_text': ''
                    })
            
            # 3. 批量创建字幕记录
            if subtitles_data:
                LOG.info(f"💾 准备保存 {len(subtitles_data)} 条字幕到数据库")
                subtitle_ids = db_manager.create_subtitles(series_id, subtitles_data)
                LOG.info(f"✅ 数据库保存成功: 系列ID {series_id}, {len(subtitle_ids)} 条字幕")
                
                # 4. 提取并保存重点单词（可选功能，暂时留空，后续实现）
                # self._extract_and_save_keywords(subtitle_ids, subtitles_data)
            else:
                LOG.warning("⚠️ 没有字幕数据需要保存")
            
        except Exception as e:
            LOG.error(f"❌ 保存到数据库失败: {e}")
            import traceback
            LOG.error(f"详细错误信息: {traceback.format_exc()}")
            # 不抛出异常，避免影响主流程
    
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
    
    def _generate_subtitles(self, recognition_result, file_info, output_format, is_bilingual, enable_short_subtitles):
        """
        生成字幕文件
        
        参数:
        - recognition_result: 识别结果
        - file_info: 文件信息
        - output_format: 输出格式
        - is_bilingual: 是否双语
        - enable_short_subtitles: 是否启用短字幕模式
        
        返回:
        - dict: 字幕生成结果
        """
        try:
            # 如果启用短字幕模式，先对识别结果进行切分
            if enable_short_subtitles:
                from subtitle_splitter import split_subtitle_chunks
                
                # 获取原始chunks
                original_chunks = recognition_result.get("english_chunks", recognition_result.get("chunks", []))
                
                if is_bilingual:
                    # 双语模式：使用对齐后的chunks
                    from openai_whisper import align_bilingual_chunks
                    english_chunks = recognition_result.get("english_chunks", [])
                    chinese_chunks = recognition_result.get("chinese_chunks", [])
                    aligned_chunks = align_bilingual_chunks(english_chunks, chinese_chunks)
                    
                    # 切分双语字幕
                    split_chunks = split_subtitle_chunks(aligned_chunks, is_bilingual=True)
                    
                    # 更新识别结果
                    recognition_result["english_chunks"] = [{"text": chunk["english"], "timestamp": chunk["timestamp"]} for chunk in split_chunks]
                    recognition_result["chinese_chunks"] = [{"text": chunk["chinese"], "timestamp": chunk["timestamp"]} for chunk in split_chunks]
                    recognition_result["chunks"] = recognition_result["english_chunks"]  # 保持兼容性
                else:
                    # 单语模式
                    split_chunks = split_subtitle_chunks(original_chunks, is_bilingual=False)
                    recognition_result["chunks"] = split_chunks
                
                LOG.info(f"🔧 字幕切分完成: 原始 {len(original_chunks)} 段 -> 切分后 {len(split_chunks)} 段")
            
            # 使用原始文件名（不含扩展名）
            original_file_name = os.path.splitext(file_info['name'])[0]
            
            # 确保output目录存在
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            
            if output_format.upper() == "LRC":
                # 生成LRC字幕
                lrc_content = generate_lrc_content(recognition_result, original_file_name)
                
                # 创建LRC文件路径 - 使用原始文件名
                lrc_filename = f"{original_file_name}.lrc"
                lrc_filepath = os.path.join(output_dir, lrc_filename)
                lrc_filepath = os.path.abspath(lrc_filepath)
                
                # 写入LRC文件
                with open(lrc_filepath, 'w', encoding='utf-8') as f:
                    f.write(lrc_content)
                
                LOG.info(f"📁 LRC字幕文件已生成: {lrc_filepath}")
                
                return {
                    'success': True,
                    'file_type': file_info['type'],
                    'subtitle_format': 'LRC',
                    'subtitle_file': lrc_filepath,
                    'subtitle_content': lrc_content,
                    'is_bilingual': is_bilingual,
                    'text': recognition_result.get('english_text', recognition_result.get('text', '')),
                    'chinese_text': recognition_result.get('chinese_text', ''),
                    'chunks_count': len(recognition_result.get('chunks', [])),
                    'processing_time': recognition_result.get('processing_time', 0)
                }
            
            elif output_format.upper() == "SRT":
                # 生成SRT字幕
                srt_content = generate_srt_content(recognition_result, original_file_name)
                
                # 创建SRT文件路径 - 使用原始文件名
                srt_filename = f"{original_file_name}.srt"
                srt_filepath = os.path.join(output_dir, srt_filename)
                srt_filepath = os.path.abspath(srt_filepath)
                
                # 写入SRT文件
                with open(srt_filepath, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                
                LOG.info(f"📁 SRT字幕文件已生成: {srt_filepath}")
                
                return {
                    'success': True,
                    'file_type': file_info['type'],
                    'subtitle_format': 'SRT',
                    'subtitle_file': srt_filepath,
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

def process_media_file(file_path, output_format="SRT", enable_translation=False, enable_short_subtitles=False):
    """
    处理多媒体文件的便捷函数
    
    参数:
    - file_path: 文件路径
    - output_format: 输出格式
    - enable_translation: 是否启用翻译
    - enable_short_subtitles: 是否启用短字幕模式
    
    返回:
    - dict: 处理结果
    """
    return media_processor.process_file(file_path, output_format, enable_translation, enable_short_subtitles)

def get_media_formats_info():
    """获取媒体格式信息"""
    return media_processor.get_supported_formats_info() 