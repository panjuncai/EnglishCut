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
    short_word_length = 9
    def __init__(self):
        """初始化烧制器"""
        LOG.info("🎬 视频字幕烧制器初始化完成")
    
    def get_key_words_for_burning(self, series_id: int) -> List[Dict]:
        """
        获取指定系列用于烧制的所有字幕和重点单词
        
        参数:
        - series_id: 系列ID
        
        返回:
        - List[Dict]: 每条字幕的信息，包含该字幕的关键词（如果有）
        """
        try:
            # 获取系列的所有字幕
            subtitles = db_manager.get_subtitles(series_id)
            if not subtitles:
                return []
            
            burn_data = []
            keyword_count = 0
            
            for subtitle in subtitles:
                subtitle_id = subtitle['id']
                begin_time = subtitle['begin_time']
                end_time = subtitle['end_time']
                english_text = subtitle.get('english_text', '')
                chinese_text = subtitle.get('chinese_text', '')
                
                # 为每个字幕创建基础数据
                subtitle_data = {
                    'subtitle_id': subtitle_id,
                    'begin_time': begin_time,
                    'end_time': end_time,
                    'duration': end_time - begin_time,
                    'english_text': english_text,
                    'chinese_text': chinese_text,
                    'has_keyword': False,
                    'keyword': None,
                    'phonetic': None,
                    'explanation': None,
                    'coca_rank': None
                }
                
                # 获取该字幕的所有关键词
                keywords = db_manager.get_keywords(subtitle_id=subtitle_id)
                if keywords:
                    # 筛选已选中的关键词
                    eligible_keywords = []
                    for keyword in keywords:
                        # 检查is_selected字段，如果为1则选中
                        if keyword.get('is_selected', 0) == 1:
                            eligible_keywords.append(keyword)
                    
                    if eligible_keywords:
                        # 选择最重要的关键词
                        selected_keyword = self._select_most_important_keyword(eligible_keywords)
                        
                        if selected_keyword:
                            # 添加关键词信息到字幕数据
                            subtitle_data['has_keyword'] = True
                            subtitle_data['keyword'] = selected_keyword['key_word']
                            subtitle_data['phonetic'] = selected_keyword.get('phonetic_symbol', '')
                            subtitle_data['explanation'] = selected_keyword.get('explain_text', '')
                            subtitle_data['coca_rank'] = selected_keyword.get('coca', 0)
                            keyword_count += 1
                
                burn_data.append(subtitle_data)
            
            LOG.info(f"📊 找到 {len(burn_data)} 条字幕，其中 {keyword_count} 条有重点单词")
            return burn_data
            
        except Exception as e:
            LOG.error(f"获取烧制数据失败: {e}")
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
        # 确保当coca为None时，将其视为0而不是尝试取负值
        sorted_keywords = sorted(
            keywords,
            key=lambda x: (-(x.get('coca') or 0), len(x.get('key_word', '')))
        )
        
        selected = sorted_keywords[0]
        LOG.debug(f"选择关键词: {selected['key_word']} (COCA: {selected.get('coca')}, 长度: {len(selected.get('key_word', ''))})")
        
        return selected
    
    def _get_video_dimensions(self, video_path: str) -> Tuple[int, int]:
        """
        使用ffprobe获取视频的宽度和高度
        """
        try:
            import subprocess
            import json
            
            cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'json', video_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            data = json.loads(result.stdout)
            width = data['streams'][0]['width']
            height = data['streams'][0]['height']
            LOG.info(f"获取到视频尺寸: {width}x{height}")
            return width, height
        except Exception as e:
            LOG.error(f"无法获取视频尺寸 {video_path}: {e}")
            return 720, 720 # 返回默认值
    
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
    
    def _build_video_filter(self, top_text: str, bottom_text: str, keyword_text: Dict = None, width: int = 720, height: int = 720) -> str:
        """
        构建FFmpeg视频滤镜，根据1:1视频的宽度，添加顶部和底部以达到9:16的比例
        
        参数:
        - top_text: 顶部文字
        - bottom_text: 底部文字
        - keyword_text: 重点单词信息
        - width: 视频宽度
        - height: 视频高度 (假定与宽度相同)
        
        返回:
        - str: FFmpeg滤镜字符串
        """
        # 转义文本中的特殊字符
        def escape_text(text):
            if not text:
                return ""
            return text.replace("\\", "\\\\").replace(":", "\\\\:").replace("'", "`").replace(",", "\\\\,").replace("=", "\\\\=")

        top_text_escaped = escape_text(top_text)
        
        # 字体路径
        douyin_font = '/Users/panjc/Library/Fonts/DouyinSansBold.ttf'
        phonetic_font = '/Users/panjc/Library/Fonts/NotoSans-Regular.ttf'

        if not os.path.exists(douyin_font):
            LOG.warning(f"抖音字体不存在: {douyin_font}")
            douyin_font = 'Arial.ttf' # Fallback
        
        if not os.path.exists(phonetic_font):
            LOG.warning(f"音标字体不存在: {phonetic_font}")
            phonetic_font = douyin_font # Fallback

        # 按照 2:9:5 的比例分配高度
        # 总比例份数 = 2 + 9 + 5 = 16
        # 视频本身占9份，所以一份的高度是 width / 9
        unit_height = width / 9
        top_padding = int(unit_height * 2)
        bottom_padding = int(unit_height * 5)
        
        # 确保总高度与计算的目标高度一致
        # 由于我们先将视频scale成了正方形(width x width)，所以视频内容的高度现在是 width
        final_height = top_padding + width + bottom_padding
        LOG.info(f"原视频尺寸: {width}x{height}, 目标尺寸: {width}x{final_height}")
        LOG.info(f"顶部高度: {top_padding}, 底部高度: {bottom_padding}")
        
        # 滤镜链
        filter_chain = [
            f"scale={width}:{width}",
            "setsar=1",
            # 1. 设置视频帧的尺寸和填充
            # pad滤镜：w=保持原宽, h=目标高, x=居中, y=顶部留白, color=背景色
            f"pad=w={width}:h={final_height}:x=0:y={top_padding}:color=black",
            
            # 2. 顶部区域背景 (如果需要和视频区域不同的颜色)
            # 顶部区域y=0, 高度为top_padding
            f"drawbox=x=0:y=0:w={width}:h={top_padding}:color=black@1.0:t=fill",
            
            # 3. 底部区域背景
            # 底部区域y从顶部+视频高度开始
            f"drawbox=x=0:y={top_padding + width}:w={width}:h={bottom_padding}:color=#fbfbf3@1.0:t=fill",
            
            # 4. 顶部标题文字
            # y坐标 = 顶部区域中心
            f"drawtext=text='{top_text_escaped}':fontcolor=white:fontsize={int(width*0.1)}:x=(w-text_w)/2:y=({top_padding}-text_h)/2:fontfile='{douyin_font}':shadowcolor=black@0.6:shadowx=1:shadowy=1",
        ]
        
        # 5. 底部字幕文字
        if bottom_text:
            lines = bottom_text.split('\n')
            num_lines = len(lines)
            line_height = int(width * 0.08) # 基于宽度的动态行高
            
            # 总字幕高度
            total_text_height = num_lines * line_height
            # 字幕起始y坐标 = 底部区域中心 - 总文本高度的一半
            start_y = (top_padding + width) + (bottom_padding - total_text_height) / 2
            
            for i, line in enumerate(lines):
                escaped_line = escape_text(line)
                y_pos = start_y + i * line_height
                
                # 区分中英文，使用不同字体大小
                font_size = int(width * 0.065) # 默认英文字体大小
                # 简单的通过是否包含中文字符来判断
                if any('\u4e00' <= char <= '\u9fff' for char in line):
                    font_size = int(width * 0.05) # 中文字体稍小
                
                    filter_chain.append(
                    f"drawtext=text='{escaped_line}':fontcolor=#111111:fontsize={font_size}:x=(w-text_w)/2:y={y_pos}:fontfile='{douyin_font}'"
                    )
                    
        # 6. 关键词和音标
        if keyword_text and all(k in keyword_text for k in ['word', 'phonetic', 'meaning']):
            word = escape_text(keyword_text['word'])
            phonetic = escape_text(keyword_text['phonetic'])
            meaning = escape_text(keyword_text['meaning'])
            
            # 动态调整关键词字号以适应背景框
            max_word_h = int(width * 0.15)
            # 当字符数超过10个时，开始缩小字号
            char_limit = 10
            if len(word) > char_limit:
                scale_factor = char_limit / len(word)
                word_h = int(max_word_h * scale_factor)
                # 设置一个最小字号，防止过小
                min_word_h = int(width * 0.08)
                word_h = max(word_h, min_word_h)
            else:
                word_h = max_word_h

            phonetic_h = int(width * 0.08)
            meaning_h = int(width * 0.08)
            v_padding = int(width * 0.04) # 上下边距
            bottom_margin = int(width * 0.05) # 距离视频区域底部的边距

            # 计算内容和背景框高度
            content_h = word_h + phonetic_h + meaning_h
            box_h = content_h + (v_padding * 2)

            # 定位：靠在视频区域底部
            box_y = top_padding + width - box_h - bottom_margin
            y_pos_word = box_y + v_padding

            # 背景框参数
            box_w = int(width * 0.9)
            box_x = int((width - box_w) / 2)

            # 添加半透明背景框
            filter_chain.append(f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=black@0.5:t=fill")

            # 关键词
            filter_chain.append(f"drawtext=text='{word}':fontcolor=yellow:fontsize={word_h}:x=(w-text_w)/2:y={y_pos_word}:fontfile='{douyin_font}':shadowcolor=black@0.7:shadowx=2:shadowy=2")
            
            # 音标
            y_pos_phonetic = y_pos_word + word_h
            filter_chain.append(f"drawtext=text='{phonetic}':fontcolor=white:fontsize={phonetic_h}:x=(w-text_w)/2:y={y_pos_phonetic}:fontfile='{phonetic_font}'")
            
            # 释义
            y_pos_meaning = y_pos_phonetic + phonetic_h
            filter_chain.append(f"drawtext=text='{meaning}':fontcolor=white:fontsize={meaning_h}:x=(w-text_w)/2:y={y_pos_meaning}:fontfile='{douyin_font}'")
            
        filter_chain.append("setdar=9/16")
        return ",".join(filter_chain)
    
    def _build_keywords_only_filter(self, top_text: str, keyword_text: Dict = None, width: int = 720, height: int = 720) -> str:
        """
        只烧制重点单词，不处理底部字幕
        """
        def escape_text(text):
            if not text:
                return ""
            return text.replace("\\", "\\\\").replace(":", "\\\\:").replace("'", "`").replace(",", "\\\\,").replace("=", "\\\\=")

        top_text_escaped = escape_text(top_text)
        
        douyin_font = '/Users/panjc/Library/Fonts/DouyinSansBold.ttf'
        phonetic_font = '/Users/panjc/Library/Fonts/NotoSans-Regular.ttf'

        if not os.path.exists(douyin_font):
            douyin_font = 'Arial.ttf'
        if not os.path.exists(phonetic_font):
            phonetic_font = douyin_font

        unit_height = width / 9
        top_padding = int(unit_height * 2)
        bottom_padding = int(unit_height * 5)
        final_height = top_padding + width + bottom_padding
        
        filter_chain = [
            f"scale={width}:{width}",
            "setsar=1",
            f"pad=w={width}:h={final_height}:x=0:y={top_padding}:color=black",
            f"drawbox=x=0:y=0:w={width}:h={top_padding}:color=black@1.0:t=fill",
            f"drawbox=x=0:y={top_padding + width}:w={width}:h={bottom_padding}:color=#fbfbf3@1.0:t=fill",
            f"drawtext=text='{top_text_escaped}':fontcolor=white:fontsize={int(width*0.1)}:x=(w-text_w)/2:y=({top_padding}-text_h)/2:fontfile='{douyin_font}':shadowcolor=black@0.6:shadowx=1:shadowy=1",
        ]
        
        if keyword_text and all(k in keyword_text for k in ['word', 'phonetic', 'meaning']):
            word = escape_text(keyword_text['word'])
            phonetic = escape_text(keyword_text['phonetic'])
            meaning = escape_text(keyword_text['meaning'])
            
            # 动态调整关键词字号以适应背景框
            max_word_h = int(width * 0.15)
            # 当字符数超过10个时，开始缩小字号
            char_limit = 10
            if len(word) > char_limit:
                scale_factor = char_limit / len(word)
                word_h = int(max_word_h * scale_factor)
                # 设置一个最小字号，防止过小
                min_word_h = int(width * 0.08)
                word_h = max(word_h, min_word_h)
            else:
                word_h = max_word_h

            phonetic_h = int(width * 0.08)
            meaning_h = int(width * 0.08)
            v_padding = int(width * 0.04) # 上下边距
            bottom_margin = int(width * 0.05) # 距离视频区域底部的边距

            # 计算内容和背景框高度
            content_h = word_h + phonetic_h + meaning_h
            box_h = content_h + (v_padding * 2)

            # 定位：靠在视频区域底部
            box_y = top_padding + width - box_h - bottom_margin
            y_pos_word = box_y + v_padding

            # 背景框参数
            box_w = int(width * 0.9)
            box_x = int((width - box_w) / 2)

            # 添加半透明背景框
            filter_chain.append(f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=black@0.5:t=fill")

            # 关键词
            filter_chain.append(f"drawtext=text='{word}':fontcolor=yellow:fontsize={word_h}:x=(w-text_w)/2:y={y_pos_word}:fontfile='{douyin_font}':shadowcolor=black@0.7:shadowx=2:shadowy=2")
            
            # 音标
            y_pos_phonetic = y_pos_word + word_h
            filter_chain.append(f"drawtext=text='{phonetic}':fontcolor=white:fontsize={phonetic_h}:x=(w-text_w)/2:y={y_pos_phonetic}:fontfile='{phonetic_font}'")
            
            # 释义
            y_pos_meaning = y_pos_phonetic + phonetic_h
            filter_chain.append(f"drawtext=text='{meaning}':fontcolor=white:fontsize={meaning_h}:x=(w-text_w)/2:y={y_pos_meaning}:fontfile='{douyin_font}'")
            
        filter_chain.append("setdar=9/16")
        return ",".join(filter_chain)
    
    def _build_no_subtitle_filter(self, top_text: str, width: int = 720, height: int = 720) -> str:
        """
        构建只有顶部标题的FFmpeg视频滤镜，根据1:1视频添加上下黑边
        """
        def escape_text(text):
            if not text:
                return ""
            return text.replace("\\", "\\\\").replace(":", "\\\\:").replace("'", "`").replace(",", "\\\\,").replace("=", "\\\\=")

        top_text_escaped = escape_text(top_text)
        douyin_font = '/Users/panjc/Library/Fonts/DouyinSansBold.ttf'
        if not os.path.exists(douyin_font):
            douyin_font = 'Arial.ttf'

        # 2:9:5 logic
        unit_height = width / 9
        top_padding = int(unit_height * 2)
        bottom_padding = int(unit_height * 5)
        final_height = top_padding + width + bottom_padding
        
        filter_chain = [
            f"scale={width}:{width}",
            "setsar=1",
            f"pad=w={width}:h={final_height}:x=0:y={top_padding}:color=black",
            f"drawbox=x=0:y=0:w={width}:h={top_padding}:color=black@1.0:t=fill",
            f"drawbox=x=0:y={top_padding + width}:w={width}:h={bottom_padding}:color=#fbfbf3@1.0:t=fill",
            f"drawtext=text='{top_text_escaped}':fontcolor=white:fontsize={int(width*0.1)}:x=(w-text_w)/2:y=({top_padding}-text_h)/2:fontfile='{douyin_font}':shadowcolor=black@0.6:shadowx=1:shadowy=1",
        ]
        
        filter_chain.append("setdar=9/16")
        return ','.join(filter_chain)
    
    def burn_video_with_keywords(self, 
                                input_video: str, 
                                output_video: str, 
                                burn_data: List[Dict],
                                title_text: str,
                                progress_callback=None) -> bool:
        """
        烧制视频，添加字幕和重点单词，处理整个视频
        
        参数:
        - input_video: 输入视频路径
        - output_video: 输出视频路径
        - burn_data: 烧制数据（所有字幕段落，部分带关键词）
        - title_text: 顶部标题栏文字
        - progress_callback: 进度回调函数
        
        返回:
        - bool: 是否成功
        """
        temp_dir = tempfile.mkdtemp(prefix="englishcut_burn_")
        try:
            import subprocess
            
            if progress_callback:
                progress_callback("🎬 开始视频烧制处理...")
            
            if not burn_data:
                if progress_callback:
                    progress_callback("❌ 没有找到字幕数据，无法烧制")
                return False
            
            keyword_segments = [item for item in burn_data if item['has_keyword']]
            if progress_callback:
                progress_callback(f"📊 共 {len(burn_data)} 条字幕，其中 {len(keyword_segments)} 条有重点单词")
            
            successfully_processed_segments = []
            failed_segments = []
            
            for i, item in enumerate(burn_data):
                try:
                    LOG.info(f"开始处理第 {i+1}/{len(burn_data)} 个字幕片段")
                    
                    if progress_callback and i % 10 == 0:
                        if item['has_keyword']:
                            progress_callback(f"🔄 处理字幕 {i+1}/{len(burn_data)}: 关键词 {item['keyword']}")
                        else:
                            progress_callback(f"🔄 处理字幕 {i+1}/{len(burn_data)}")
                    
                    bottom_text = ""
                    if item['english_text']:
                        bottom_text = item['english_text']
                    if item['chinese_text']:
                        if bottom_text:
                            bottom_text += "\n"
                        bottom_text += item['chinese_text']
                    
                    start_time = item['begin_time']
                    end_time = item['end_time']
                    
                    if end_time <= start_time:
                        LOG.warning(f"片段 {i} 的时间段无效: {start_time}-{end_time}，尝试修复")
                        end_time = start_time + 0.1
                    
                    duration = end_time - start_time
                    LOG.info(f"片段 {i}: 时间 {start_time:.2f}-{end_time:.2f}, 时长: {duration:.2f}秒")
                    
                    temp_segment_path = os.path.join(temp_dir, f"temp_segment_{i}.mp4")
                    processed_segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
                    
                    segment_cmd = [
                        'ffmpeg', '-y',
                        '-i', input_video,
                        '-ss', str(start_time),
                        '-to', str(end_time),
                        '-c:v', 'libx264', '-c:a', 'aac',
                        '-vsync', '2',
                        temp_segment_path
                    ]
                    
                    LOG.info(f"执行裁剪命令: {' '.join(segment_cmd)}")
                    
                    proc = subprocess.Popen(
                        segment_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    stdout, stderr = proc.communicate()
                    
                    if proc.returncode != 0:
                        LOG.error(f"片段 {i} 裁剪失败: {stderr}")
                        failed_segments.append(i)
                        continue
                    
                    if not os.path.exists(temp_segment_path) or os.path.getsize(temp_segment_path) == 0:
                        LOG.error(f"片段 {i} 裁剪后的文件无效: {temp_segment_path}")
                        failed_segments.append(i)
                        continue
                    
                    video_width, video_height = self._get_video_dimensions(temp_segment_path)
                    
                    keyword_info = None
                    if item['has_keyword']:
                        keyword_info = {
                            'word': item['keyword'],
                            'phonetic': item['phonetic'],
                            'meaning': item['explanation']
                        }
                    
                    video_filter = self._build_video_filter(title_text, bottom_text, keyword_info, width=video_width, height=video_height)
                    
                    process_cmd = [
                        'ffmpeg', '-y',
                        '-i', temp_segment_path,
                        '-vf', video_filter,
                        '-c:a', 'copy',
                        '-preset', 'medium',
                        '-crf', '23',
                        processed_segment_path
                    ]
                    
                    proc = subprocess.Popen(
                        process_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    stdout, stderr = proc.communicate()
                    
                    if proc.returncode != 0:
                        LOG.error(f"片段 {i} 处理失败: {stderr}")
                        failed_segments.append(i)
                        continue
                    
                    if not os.path.exists(processed_segment_path) or os.path.getsize(processed_segment_path) == 0:
                        LOG.error(f"片段 {i} 处理后的文件无效: {processed_segment_path}")
                        failed_segments.append(i)
                        continue
                    
                    successfully_processed_segments.append(i)
                    
                    if progress_callback and i % 5 == 0:
                        current_progress = f"🎬 进度: {i+1}/{len(burn_data)} | 成功: {len(successfully_processed_segments)}"
                        if item['has_keyword']:
                            current_progress += f" | 单词: {item['keyword']}"
                        progress_callback(current_progress)
                    
                except Exception as e:
                    LOG.error(f"处理片段 {i} 时发生异常: {str(e)}")
                    import traceback
                    LOG.error(traceback.format_exc())
                    failed_segments.append(i)
                    continue
            
            LOG.info(f"成功处理 {len(successfully_processed_segments)}/{len(burn_data)} 个片段")
            if failed_segments:
                LOG.warning(f"失败片段索引: {failed_segments}")
            
            if progress_callback:
                success_rate = len(successfully_processed_segments) / len(burn_data) * 100
                progress_callback(f"📊 成功处理 {len(successfully_processed_segments)}/{len(burn_data)} 个片段 ({success_rate:.1f}%)")
                if failed_segments:
                    progress_callback(f"⚠️ {len(failed_segments)} 个片段处理失败")
            
            if not successfully_processed_segments:
                if progress_callback:
                    progress_callback("❌ 没有成功处理的片段，无法生成视频")
                return False
            
            segments_list_path = os.path.join(temp_dir, "segments.txt")
            LOG.info(f"创建片段列表文件: {segments_list_path}")
            
            with open(segments_list_path, 'w') as f:
                for i in successfully_processed_segments:
                    segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        abs_segment_path = os.path.abspath(segment_path)
                        f.write(f"file '{abs_segment_path}'\n")
            
            if progress_callback:
                progress_callback("🔄 开始合并所有视频片段...")
                
            concat_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', segments_list_path,
                '-c', 'copy',
                output_video
            ]
            
            LOG.info(f"执行合并命令: {' '.join(concat_cmd)}")
            
            proc = subprocess.Popen(
                concat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = proc.communicate()
            
            if proc.returncode == 0 and os.path.exists(output_video) and os.path.getsize(output_video) > 0:
                if progress_callback:
                    progress_callback("✅ 视频烧制完成！")
                LOG.info(f"✅ 视频烧制成功: {output_video}")
                return True
            else:
                LOG.error(f"合并失败: {stderr}")
                return False
                
        except Exception as e:
            error_msg = f"视频烧制失败: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}")
            LOG.error(error_msg)
            return False
        finally:
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    LOG.info(f"🧹 临时目录已清理: {temp_dir}")
            except Exception as e:
                LOG.warning(f"清理临时目录失败: {e}")
    
    def process_series_video(self, 
                            series_id: int, 
                            output_dir: str = "input",
                            title_text: str = "",
                            progress_callback=None) -> Optional[str]:
        """
        处理整个系列的视频烧制
        
        参数:
        - series_id: 系列ID
        - output_dir: 输出目录，默认为input
        - title_text: 顶部标题栏文字
        - progress_callback: 进度回调函数
        
        返回:
        - str: 输出视频路径，失败返回None
        """
        temp_dir = tempfile.mkdtemp(prefix="englishcut_burn_")
        try:
            if progress_callback:
                progress_callback("🔍 开始处理系列视频...")
            
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
            
            input_video = target_series.get('new_file_path')
            if not input_video or not os.path.exists(input_video):
                    if progress_callback:
                        progress_callback(f"❌ 找不到预处理的1:1视频: {input_video}，请先执行预处理")
                        return None
            else:
                    if progress_callback:
                        progress_callback(f"📹 使用1:1裁剪视频: {os.path.basename(input_video)}")
            
            burn_data = self.get_key_words_for_burning(series_id)
            if not burn_data:
                if progress_callback:
                    progress_callback("⚠️ 没有找到符合条件的重点单词")
                return None
            
            if progress_callback:
                progress_callback(f"📚 找到 {len(burn_data)} 个重点单词用于烧制")
            
            os.makedirs(output_dir, exist_ok=True)
            
            input_basename = os.path.basename(input_video)
            base_name = os.path.splitext(input_basename)[0].replace("_0", "")
            
            output_video = os.path.join(output_dir, f"{base_name}_3.mp4")
            
            if progress_callback:
                progress_callback(f"📋 输入视频: {input_basename}, 输出视频: {os.path.basename(output_video)}")
            
            success = self.burn_video_with_keywords(
                input_video, 
                output_video, 
                burn_data,
                title_text,
                progress_callback
            )
            
            if success:
                db_manager.update_series_video_info(
                    series_id,
                    third_name=os.path.basename(output_video),
                    third_file_path=output_video
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
        finally:
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    LOG.info(f"🧹 临时目录已清理: {temp_dir}")
            except Exception as e:
                LOG.warning(f"清理临时目录失败: {e}")
    
    def burn_keywords_only_video(self, 
                                   input_video: str, 
                                   output_video: str, 
                                   burn_data: List[Dict],
                                   title_text: str,
                                   progress_callback=None) -> bool:
        """
        只烧制带重点单词的视频片段
        """
        temp_dir = tempfile.mkdtemp(prefix="englishcut_kw_burn_")
        try:
            import subprocess
            
            if progress_callback:
                progress_callback("🎬 开始只烧制重点单词视频...")
            
            successfully_processed_segments = []
            
            for i, item in enumerate(burn_data):
                try:
                    start_time = item['begin_time']
                    end_time = item['end_time']
                    
                    temp_segment_path = os.path.join(temp_dir, f"kw_temp_segment_{i}.mp4")
                    processed_segment_path = os.path.join(temp_dir, f"kw_segment_{i}.mp4")
                    
                    segment_cmd = [
                        'ffmpeg', '-y',
                        '-i', input_video,
                        '-ss', str(start_time),
                        '-to', str(end_time),
                        '-c:v', 'libx264', '-c:a', 'aac',
                        '-vsync', '2',
                        temp_segment_path
                    ]
                    
                    subprocess.run(segment_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    video_width, video_height = self._get_video_dimensions(temp_segment_path)
                    
                    keyword_info = {
                            'word': item['keyword'],
                            'phonetic': item['phonetic'],
                            'meaning': item['explanation']
                        }
                    
                    video_filter = self._build_keywords_only_filter(title_text, keyword_info, width=video_width, height=video_height)
                    
                    process_cmd = [
                        'ffmpeg', '-y',
                        '-i', temp_segment_path,
                        '-vf', video_filter,
                        '-c:a', 'copy',
                        '-preset', 'medium',
                        '-crf', '23',
                        processed_segment_path
                    ]
                    
                    subprocess.run(process_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    successfully_processed_segments.append(processed_segment_path)
                    
                except Exception as e:
                    LOG.error(f"处理关键词片段 {i} 失败: {e}")
                    continue
            
            if not successfully_processed_segments:
                if progress_callback:
                    progress_callback("❌ 没有成功处理的关键词片段")
                return False
            
            segments_list_path = os.path.join(temp_dir, "kw_segments.txt")
            with open(segments_list_path, 'w') as f:
                for path in successfully_processed_segments:
                    f.write(f"file '{os.path.abspath(path)}'\n")

            concat_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', segments_list_path,
                '-c', 'copy',
                output_video
            ]
            
            subprocess.run(concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if progress_callback:
                progress_callback("✅ 重点单词视频烧制完成！")
            
            return True
            
        except Exception as e:
            LOG.error(f"只烧制重点单词视频失败: {e}")
            if progress_callback:
                progress_callback(f"❌ 只烧制重点单词视频失败: {e}")
            return False
        finally:
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    LOG.info(f"🧹 重点单词视频临时目录已清理: {temp_dir}")
            except Exception as e:
                LOG.warning(f"清理临时目录失败: {e}")

    def process_keywords_only_video(self, 
                                   series_id: int, 
                                   output_dir: str = "input",
                                   title_text: str = "",
                                   progress_callback=None) -> Optional[str]:
        """
        处理只烧制带重点单词片段的视频
        """
        temp_dir = tempfile.mkdtemp(prefix="englishcut_burn_")
        try:
            if progress_callback:
                progress_callback("🔍 开始处理只含重点单词的视频...")
            
            series_list = db_manager.get_series()
            target_series = next((s for s in series_list if s['id'] == series_id), None)
                
            if not target_series:
                if progress_callback:
                    progress_callback("❌ 找不到指定的系列")
                    return None
                
            input_video = target_series.get('new_file_path')
            if not input_video or not os.path.exists(input_video):
                if progress_callback:
                    progress_callback(f"❌ 找不到预处理的1:1视频: {input_video}，请先执行预处理")
                return None

            if progress_callback:
                progress_callback(f"📹 使用1:1裁剪视频: {os.path.basename(input_video)}")
            
            burn_data = self.get_key_words_for_burning(series_id)
            keyword_burn_data = [item for item in burn_data if item['has_keyword']]
            
            if not keyword_burn_data:
                if progress_callback:
                    progress_callback("⚠️ 没有找到符合条件的重点单词")
                return None
            
            if progress_callback:
                progress_callback(f"📚 找到 {len(keyword_burn_data)} 条带重点单词的字幕用于烧制")
            
            os.makedirs(output_dir, exist_ok=True)
            input_basename = os.path.basename(input_video)
            base_name = os.path.splitext(input_basename)[0].replace("_0", "")
            
            output_video = os.path.join(output_dir, f"{base_name}_2.mp4")
            
            if progress_callback:
                progress_callback(f"📋 输入视频: {input_basename}, 输出视频: {os.path.basename(output_video)}")
            
            success = self.burn_keywords_only_video(
                input_video, 
                output_video, 
                keyword_burn_data,
                title_text,
                progress_callback
            )
            
            if success:
                    db_manager.update_series_video_info(
                        series_id,
                        second_name=os.path.basename(output_video),
                        second_file_path=output_video
                    )
                    
            if progress_callback:
                    progress_callback(f"🎉 重点单词视频完成！输出文件: {output_video}")
                
                    return output_video
            else:
                    return None
                
        except Exception as e:
            error_msg = f"处理重点单词视频失败: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}")
            LOG.error(error_msg)
            return None
        finally:
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    LOG.info(f"🧹 临时目录已清理: {temp_dir}")
            except Exception as e:
                LOG.warning(f"清理临时目录失败: {e}")
    
    def get_burn_preview(self, series_id: int) -> Dict:
        """
        获取烧制预览信息，包括一张带字幕的预览图和一条预览音频
        """
        temp_dir = tempfile.mkdtemp(prefix="englishcut_preview_")
        LOG.warning(f"创建预览临时目录: {temp_dir}，此目录不会自动清理，需由调用方管理。")
        try:
            import subprocess
            
            burn_data = self.get_key_words_for_burning(series_id)
            if not burn_data:
                return {"error": "没有找到可烧制的字幕数据"}
            
            first_keyword_item = None
            for item in burn_data:
                if item['has_keyword']:
                    first_keyword_item = item
                    break
            
            if not first_keyword_item:
                return {"error": "没有找到带重点单词的字幕"}
            
            series_list = db_manager.get_series()
            target_series = next((s for s in series_list if s['id'] == series_id), None)
            if not target_series:
                return {"error": "找不到指定的系列"}
            
            input_video = target_series.get('new_file_path')
            if not input_video or not os.path.exists(input_video):
                return {"error": "找不到预处理的1:1视频"}
            
            preview_image_path = os.path.join(temp_dir, "preview.jpg")
            
            start_time = first_keyword_item['begin_time']
            bottom_text = f"{first_keyword_item['english_text']}\n{first_keyword_item['chinese_text']}"
            keyword_info = {
                'word': first_keyword_item['keyword'],
                'phonetic': first_keyword_item['phonetic'],
                'meaning': first_keyword_item['explanation']
            }
            
            width, height = self._get_video_dimensions(input_video)

            video_filter = self._build_video_filter("预览标题", bottom_text, keyword_info, width, height)
            
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', input_video,
                '-vf', video_filter,
                '-frames:v', '1',
                preview_image_path
            ]
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if os.path.exists(preview_image_path):
                return {"preview_image": preview_image_path}
            else:
                return {"error": "生成预览图失败"}
            
        except Exception as e:
            LOG.error(f"生成预览失败: {e}")
            return {"error": f"生成预览失败: {str(e)}"}
    
    def cleanup(self):
        """清理临时目录"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                LOG.info(f"🧹 临时目录已清理: {self.temp_dir}")
        except Exception as e:
            LOG.warning(f"清理临时目录失败: {e}")
    
    def process_no_subtitle_video(self, 
                                 series_id: int, 
                                 output_dir: str = "input",
                                 title_text: str = "",
                                 progress_callback=None) -> Optional[str]:
        """
        处理没有字幕的视频，只添加顶部标题
        """
        temp_dir = tempfile.mkdtemp(prefix="englishcut_burn_")
        try:
            if progress_callback:
                progress_callback("🔍 开始处理无字幕视频...")
            
            series_list = db_manager.get_series()
            target_series = next((s for s in series_list if s['id'] == series_id), None)
            if not target_series:
                if progress_callback:
                    progress_callback("❌ 找不到指定的系列")
                return None
            
            input_video = target_series.get('new_file_path')
            if not input_video or not os.path.exists(input_video):
                if progress_callback:
                    progress_callback(f"❌ 找不到预处理的1:1视频: {input_video}，请先执行预处理")
                    return None
                
            width, height = self._get_video_dimensions(input_video)
            
            os.makedirs(output_dir, exist_ok=True)
            input_basename = os.path.basename(input_video)
            base_name = os.path.splitext(input_basename)[0].replace("_0", "")
            output_video = os.path.join(output_dir, f"{base_name}_1.mp4")
            
            video_filter = self._build_no_subtitle_filter(title_text, width=width, height=height)

            cmd = [
                'ffmpeg', '-y',
                '-i', input_video,
                '-vf', video_filter,
                '-c:a', 'copy',
                '-preset', 'medium',
                '-crf', '23',
                output_video
            ]
            
            import subprocess
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if os.path.exists(output_video):
                db_manager.update_series_video_info(
                    series_id,
                    first_name=os.path.basename(output_video),
                    first_file_path=output_video
                )
                if progress_callback:
                    progress_callback(f"✅ 无字幕视频处理完成: {output_video}")
                return output_video
            else:
                return None
                
        except Exception as e:
            LOG.error(f"处理无字幕视频失败: {e}")
            if progress_callback:
                progress_callback(f"❌ 处理无字幕视频失败: {e}")
            return None
        finally:
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    LOG.info(f"🧹 临时目录已清理: {temp_dir}")
            except Exception as e:
                LOG.warning(f"清理临时目录失败: {e}")
    
    def merge_video_series(self, 
                           first_video_path: str, 
                           second_video_path: str, 
                           third_video_path: str, 
                           output_video: str,
                           progress_callback=None) -> bool:
        """
        合并三个视频系列（无字幕，只有关键词，完整字幕）
        """
        temp_dir = tempfile.mkdtemp(prefix="englishcut_merge_")
        try:
            import subprocess
            
            if progress_callback:
                progress_callback("🔄 开始合并视频系列...")
            
            videos_to_merge = []
            if first_video_path and os.path.exists(first_video_path):
                videos_to_merge.append(first_video_path)
            if second_video_path and os.path.exists(second_video_path):
                videos_to_merge.append(second_video_path)
            if third_video_path and os.path.exists(third_video_path):
                videos_to_merge.append(third_video_path)
            
            if len(videos_to_merge) < 2:
                if progress_callback:
                    progress_callback("⚠️ 少于两个视频，无需合并")
                return False
            
            segments_list_path = os.path.join(temp_dir, "merge_list.txt")
            with open(segments_list_path, 'w') as f:
                for video_path in videos_to_merge:
                    f.write(f"file '{os.path.abspath(video_path)}'\n")
            
            concat_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', segments_list_path,
                '-c', 'copy',
                output_video
            ]
            
            subprocess.run(concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if progress_callback:
                progress_callback(f"✅ 视频合并成功: {output_video}")
                
                return True
            
        except Exception as e:
            LOG.error(f"合并视频失败: {e}")
            if progress_callback:
                progress_callback(f"❌ 合并视频失败: {e}")
            return False
        finally:
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    LOG.info(f"🧹 合并视频临时目录已清理: {temp_dir}")
            except Exception as e:
                LOG.warning(f"清理合并视频临时目录失败: {e}")

# 全局实例
video_burner = VideoSubtitleBurner() 