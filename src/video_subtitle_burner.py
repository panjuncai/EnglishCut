#!/usr/bin/env python3
"""
视频字幕烧制模块
将重点单词和词组烧制到视频中，用于无字幕观看美国新闻
"""

import os
import json
import tempfile
from typing import List, Dict, Optional, Tuple
from logger import LOG
from database import db_manager

class VideoSubtitleBurner:
    """视频字幕烧制器"""
    
    def __init__(self):
        """初始化烧制器"""
        self.temp_dir = tempfile.mkdtemp(prefix="englishcut_burn_")
        LOG.info("🎬 视频字幕烧制器初始化完成")
    
    def get_key_words_for_burning(self, series_id: int) -> List[Dict]:
        """
        获取指定系列用于烧制的重点单词
        
        参数:
        - series_id: 系列ID
        
        返回:
        - List[Dict]: 每条字幕的最重要单词信息
        """
        try:
            # 获取系列的所有字幕
            subtitles = db_manager.get_subtitles(series_id)
            if not subtitles:
                return []
            
            burn_data = []
            
            for subtitle in subtitles:
                subtitle_id = subtitle['id']
                begin_time = subtitle['begin_time']
                end_time = subtitle['end_time']
                
                # 获取该字幕的所有关键词
                keywords = db_manager.get_keywords(subtitle_id=subtitle_id)
                if not keywords:
                    continue
                
                # 筛选符合条件的关键词：COCA排名 > 5000 且不为空
                eligible_keywords = []
                for keyword in keywords:
                    coca_rank = keyword.get('coca')
                    if coca_rank and coca_rank > 5000:  # 低频重点词汇
                        eligible_keywords.append(keyword)
                
                if not eligible_keywords:
                    continue
                
                # 选择最重要的关键词
                selected_keyword = self._select_most_important_keyword(eligible_keywords)
                
                if selected_keyword:
                    burn_data.append({
                        'subtitle_id': subtitle_id,
                        'begin_time': begin_time,
                        'end_time': end_time,
                        'duration': end_time - begin_time,
                        'keyword': selected_keyword['key_word'],
                        'phonetic': selected_keyword.get('phonetic_symbol', ''),
                        'explanation': selected_keyword.get('explain_text', ''),
                        'coca_rank': selected_keyword.get('coca', 0)
                    })
            
            LOG.info(f"📊 找到 {len(burn_data)} 个重点单词用于烧制")
            return burn_data
            
        except Exception as e:
            LOG.error(f"获取烧制单词失败: {e}")
            return []
    
    def _select_most_important_keyword(self, keywords: List[Dict]) -> Optional[Dict]:
        """
        从多个关键词中选择最重要的一个
        
        规则:
        1. 选择COCA排名最大的（词频最低=最重要）
        2. 如果COCA排名相同，选择长度最短的
        
        参数:
        - keywords: 关键词列表
        
        返回:
        - Dict: 最重要的关键词，如果没有则返回None
        """
        if not keywords:
            return None
        
        if len(keywords) == 1:
            return keywords[0]
        
        # 按COCA排名降序（数字大=频率低=重要度高），长度升序排序
        sorted_keywords = sorted(
            keywords,
            key=lambda x: (-x.get('coca', 0), len(x.get('key_word', '')))
        )
        
        selected = sorted_keywords[0]
        LOG.debug(f"选择关键词: {selected['key_word']} (COCA: {selected.get('coca')}, 长度: {len(selected.get('key_word', ''))})")
        
        return selected
    
    def create_subtitle_file(self, burn_data: List[Dict], subtitle_path: str) -> Tuple[str, str]:
        """
        创建烧制用的SRT字幕文件
        创建两个字幕文件：一个用于原视频区域的中英文字幕，一个用于底部区域的重点单词
        
        参数:
        - burn_data: 烧制数据
        - subtitle_path: 字幕文件保存路径
        
        返回:
        - Tuple[str, str]: (原文字幕文件路径, 重点单词字幕文件路径)
        """
        try:
            # 两个SRT文件路径
            orig_subtitle_path = subtitle_path.replace('.ass', '_original.srt')
            keyword_subtitle_path = subtitle_path.replace('.ass', '_keywords.srt')
            
            # 原文字幕内容
            orig_subtitle_content = []
            # 重点单词字幕内容
            keyword_subtitle_content = []
            
            for i, item in enumerate(burn_data, 1):
                start_time = self._seconds_to_srt_time(item['begin_time'])
                end_time = self._seconds_to_srt_time(item['end_time'])
                
                keyword = item['keyword']
                phonetic = item['phonetic'].strip('/')
                explanation = item['explanation']
                
                # 获取原始英文字幕
                subtitle_id = item['subtitle_id']
                subtitle_info = db_manager.get_subtitle_by_id(subtitle_id)
                
                # 构建原文字幕内容（英文+中文）
                orig_lines = []
                if subtitle_info:
                    if 'english_text' in subtitle_info and subtitle_info['english_text']:
                        orig_lines.append(subtitle_info['english_text'])
                    if 'chinese_text' in subtitle_info and subtitle_info['chinese_text']:
                        orig_lines.append(subtitle_info['chinese_text'])
                
                # 构建重点单词字幕内容
                keyword_lines = []
                # 单词 + 音标格式
                highlight_line = ""
                if phonetic:
                    highlight_line = f"{keyword} [{phonetic}]"
                else:
                    highlight_line = keyword
                
                keyword_lines.append(highlight_line)
                
                # 解释行（词性 + 中文解释）
                if explanation:
                    keyword_lines.append(f"adj. {explanation}")
                
                # 添加到各自的字幕内容
                if orig_lines:
                    orig_subtitle_content.append(f"{i}")
                    orig_subtitle_content.append(f"{start_time} --> {end_time}")
                    orig_subtitle_content.append('\n'.join(orig_lines))
                    orig_subtitle_content.append("")  # 空行分隔
                
                if keyword_lines:
                    keyword_subtitle_content.append(f"{i}")
                    keyword_subtitle_content.append(f"{start_time} --> {end_time}")
                    keyword_subtitle_content.append('\n'.join(keyword_lines))
                    keyword_subtitle_content.append("")  # 空行分隔
            
            # 写入原文字幕文件
            with open(orig_subtitle_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(orig_subtitle_content))
            
            # 写入重点单词字幕文件
            with open(keyword_subtitle_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(keyword_subtitle_content))
            
            LOG.info(f"📝 创建字幕文件: {orig_subtitle_path} 和 {keyword_subtitle_path}")
            return orig_subtitle_path, keyword_subtitle_path
            
        except Exception as e:
            LOG.error(f"创建字幕文件失败: {e}")
            raise
    
    def _seconds_to_ass_time(self, seconds: float) -> str:
        """
        将秒数转换为ASS时间格式
        
        参数:
        - seconds: 秒数
        
        返回:
        - str: ASS时间格式 (H:MM:SS.cc)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """
        将秒数转换为SRT时间格式
        
        参数:
        - seconds: 秒数
        
        返回:
        - str: SRT时间格式 (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def burn_video_with_keywords(self, 
                                input_video: str, 
                                output_video: str, 
                                burn_data: List[Dict],
                                title_text: str = "第二遍: 词汇与文法分析",
                                progress_callback=None) -> bool:
        """
        烧制视频，添加重点单词字幕
        
        参数:
        - input_video: 输入视频路径
        - output_video: 输出视频路径
        - burn_data: 烧制数据
        - title_text: 顶部标题栏文字
        - progress_callback: 进度回调函数
        
        返回:
        - bool: 是否成功
        """
        try:
            import subprocess
            
            if progress_callback:
                progress_callback("🎬 开始视频烧制处理...")
            
            # 创建临时SRT字幕文件
            subtitle_path = os.path.join(self.temp_dir, "keywords.srt")
            orig_subtitle_path, keyword_subtitle_path = self.create_subtitle_file(burn_data, subtitle_path)
            
            if progress_callback:
                progress_callback("📝 字幕文件创建完成，开始视频处理...")
            
            # FFmpeg命令：裁剪到竖屏 + 烧制字幕
            cmd = [
                'ffmpeg', '-y',  # 覆盖输出文件
                '-i', input_video,  # 输入视频
                '-vf', self._build_video_filter(orig_subtitle_path, keyword_subtitle_path, title_text),  # 视频滤镜
                '-aspect', '3:4',  # 设置宽高比为3:4 (竖屏)
                '-c:a', 'copy',  # 音频直接复制
                '-preset', 'medium',  # 编码预设
                '-crf', '23',  # 质量控制
                output_video
            ]
            
            if progress_callback:
                progress_callback(f"🔄 执行FFmpeg命令...")
            
            LOG.info(f"🎬 执行FFmpeg命令: {' '.join(cmd)}")
            
            # 执行FFmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                if progress_callback:
                    progress_callback("✅ 视频烧制完成！")
                LOG.info(f"✅ 视频烧制成功: {output_video}")
                return True
            else:
                error_msg = f"FFmpeg错误: {stderr}"
                if progress_callback:
                    progress_callback(f"❌ 烧制失败: {error_msg}")
                LOG.error(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"视频烧制失败: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}")
            LOG.error(error_msg)
            return False
        finally:
            # 清理临时文件
            try:
                if os.path.exists(orig_subtitle_path):
                    os.remove(orig_subtitle_path)
                if os.path.exists(keyword_subtitle_path):
                    os.remove(keyword_subtitle_path)
            except:
                pass
    
    def _build_video_filter(self, orig_subtitle_path: str, keyword_subtitle_path: str, title_text: str = "第二遍: 词汇与文法分析") -> str:
        """
        构建FFmpeg视频滤镜
        
        参数:
        - orig_subtitle_path: 原文字幕文件路径
        - keyword_subtitle_path: 重点单词字幕文件路径
        - title_text: 顶部标题栏文字
        
        返回:
        - str: FFmpeg滤镜字符串
        """
        # 转义路径中的特殊字符
        escaped_orig_path = orig_subtitle_path.replace('\\', '\\\\').replace(':', '\\:').replace('\'', '\\\'')
        escaped_keyword_path = keyword_subtitle_path.replace('\\', '\\\\').replace(':', '\\:').replace('\'', '\\\'')
        
        # 视频滤镜：使用多步处理
        # 1. 裁剪原视频到竖屏
        # 2. 添加顶部标题区域和底部词汇区域，使视频整体成为3:4比例
        # 3. 在新创建的区域上添加文字
        
        filter_chain = [
            # 第1步：裁剪原视频（从中间裁剪到接近正方形）
            "scale=-1:ih",  # 保持高度不变，调整宽度
            "crop=ih*0.9:ih:(iw-ow)/2:0",  # 从中间裁剪接近正方形区域
            
            # 第2步：在上下添加空白区域，形成3:4比例
            "pad=iw:ih*1.3:0:ih*0.15:lightblue",  # 顶部添加15%高度的浅蓝色区域，底部会自动填充
            
            # 第3步：在底部添加黄色区域
            "drawbox=x=0:y=ih*0.85:w=iw:h=ih*0.3:color=yellow@1:t=fill",  # 底部30%区域填充黄色
            
            # 第4步：添加顶部标题文字
            f"drawtext=text='{title_text}':fontcolor=blue:fontsize=30:x=(w-text_w)/2:y=(h*0.15-text_h)/2:fontfile=/System/Library/Fonts/STHeiti Medium.ttc",
            
            # 第5步：烧制原视频中英文字幕（较小字体）
            f"subtitles='{escaped_orig_path}':force_style='Fontname=Microsoft YaHei,Fontsize=16,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=4,Outline=1,Shadow=1,Alignment=2,MarginV=5,MarginL=30,MarginR=30,Bold=0,Spacing=1'",
            
            # 第6步：烧制底部区域的重点单词（较大字体，应用偏移确保显示在黄色区域）
            f"subtitles='{escaped_keyword_path}':force_style='Fontname=Microsoft YaHei,Fontsize=30,PrimaryColour=&H00000000,BackColour=&H00000000,BorderStyle=0,Outline=0,Shadow=0,Alignment=2,MarginV=250,MarginL=30,MarginR=30,Bold=1,Spacing=1'"
        ]
        
        return ','.join(filter_chain)
    
    def process_series_video(self, 
                            series_id: int, 
                            output_dir: str = "output",
                            title_text: str = "第二遍: 词汇与文法分析",
                            progress_callback=None) -> Optional[str]:
        """
        处理整个系列的视频烧制
        
        参数:
        - series_id: 系列ID
        - output_dir: 输出目录
        - title_text: 顶部标题栏文字
        - progress_callback: 进度回调函数
        
        返回:
        - str: 输出视频路径，失败返回None
        """
        try:
            if progress_callback:
                progress_callback("🔍 开始处理系列视频...")
            
            # 获取系列信息
            series_list = db_manager.get_series()
            target_series = None
            for series in series_list:
                if series['id'] == series_id:
                    target_series = series
                    break
            
            if not target_series:
                if progress_callback:
                    progress_callback("❌ 找不到指定的系列")
                return None
            
            # 获取原视频路径
            input_video = target_series.get('file_path')
            if not input_video or not os.path.exists(input_video):
                if progress_callback:
                    progress_callback("❌ 找不到原视频文件")
                return None
            
            if progress_callback:
                progress_callback(f"📹 找到视频文件: {os.path.basename(input_video)}")
            
            # 获取烧制数据
            burn_data = self.get_key_words_for_burning(series_id)
            if not burn_data:
                if progress_callback:
                    progress_callback("⚠️ 没有找到符合条件的重点单词")
                return None
            
            if progress_callback:
                progress_callback(f"📚 找到 {len(burn_data)} 个重点单词用于烧制")
            
            # 准备输出路径
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(input_video))[0]
            output_video = os.path.join(output_dir, f"{base_name}_keywords_mobile.mp4")
            
            # 执行烧制
            success = self.burn_video_with_keywords(
                input_video, 
                output_video, 
                burn_data,
                title_text,
                progress_callback
            )
            
            if success:
                # 更新数据库中的烧制视频信息
                db_manager.update_series_video_info(
                    series_id,
                    new_name=os.path.basename(output_video),
                    new_file_path=output_video
                )
                
                if progress_callback:
                    progress_callback(f"🎉 烧制完成！输出文件: {output_video}")
                
                return output_video
            else:
                return None
                
        except Exception as e:
            error_msg = f"处理系列视频失败: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}")
            LOG.error(error_msg)
            return None
    
    def get_burn_preview(self, series_id: int) -> Dict:
        """
        获取烧制预览信息
        
        参数:
        - series_id: 系列ID
        
        返回:
        - Dict: 预览信息
        """
        try:
            burn_data = self.get_key_words_for_burning(series_id)
            
            # 统计信息
            total_keywords = len(burn_data)
            total_duration = sum(item['duration'] for item in burn_data)
            
            # 词频分布
            coca_ranges = {
                '5000-10000': 0,
                '10000-20000': 0,
                '20000+': 0
            }
            
            for item in burn_data:
                coca_rank = item['coca_rank']
                if 5000 < coca_rank <= 10000:
                    coca_ranges['5000-10000'] += 1
                elif 10000 < coca_rank <= 20000:
                    coca_ranges['10000-20000'] += 1
                else:
                    coca_ranges['20000+'] += 1
            
            # 示例单词（前5个）
            sample_keywords = burn_data[:5] if burn_data else []
            
            return {
                'total_keywords': total_keywords,
                'total_duration': round(total_duration, 2),
                'coca_distribution': coca_ranges,
                'sample_keywords': sample_keywords,
                'estimated_file_size': f"{total_keywords * 0.5:.1f} MB"  # 估算
            }
            
        except Exception as e:
            LOG.error(f"获取烧制预览失败: {e}")
            return {
                'total_keywords': 0,
                'total_duration': 0,
                'coca_distribution': {},
                'sample_keywords': [],
                'estimated_file_size': '0 MB'
            }
    
    def cleanup(self):
        """清理临时文件"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                LOG.info("🧹 临时文件清理完成")
        except Exception as e:
            LOG.warning(f"清理临时文件失败: {e}")

# 全局实例
video_burner = VideoSubtitleBurner() 