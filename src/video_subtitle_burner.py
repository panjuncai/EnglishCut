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
                    # 筛选符合条件的关键词：COCA排名 > 500 且不为空
                    eligible_keywords = []
                    for keyword in keywords:
                        coca_rank = keyword.get('coca')
                        if coca_rank and coca_rank > 500:  # 低频重点词汇
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
        sorted_keywords = sorted(
            keywords,
            key=lambda x: (-x.get('coca', 0), len(x.get('key_word', '')))
        )
        
        selected = sorted_keywords[0]
        LOG.debug(f"选择关键词: {selected['key_word']} (COCA: {selected.get('coca')}, 长度: {len(selected.get('key_word', ''))})")
        
        return selected
    
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
    
    def _build_video_filter(self, top_text: str, bottom_text: str, keyword_text: Dict = None) -> str:
        """
        构建FFmpeg视频滤镜，使用与pre_process.py相同的视频滤镜逻辑，但不再进行9:16裁剪
        
        参数:
        - top_text: 顶部文字
        - bottom_text: 底部文字
        - keyword_text: 重点单词信息，格式为 {"word": "text", "phonetic": "音标", "meaning": "释义"}
        
        返回:
        - str: FFmpeg滤镜字符串
        """
        # 指定字体路径，优先使用抖音字体，找不到再使用苹方
        douyin_font = '/Users/panjc/Library/Fonts/DouyinSansBold.ttf'
        # 备选字体
        system_fonts = [
            '/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc',  # 苹方
            '/System/Library/Fonts/STHeiti Light.ttc',  # 黑体-简 细体
            '/System/Library/Fonts/Hiragino Sans GB.ttc',  # 冬青黑体
            'Arial.ttf'  # 默认Arial
        ]
        
        # 检查抖音字体是否存在
        if not os.path.exists(douyin_font):
            LOG.warning(f"警告: 抖音字体文件不存在: {douyin_font}")
            # 找到第一个存在的系统字体
            for font in system_fonts:
                if os.path.exists(font):
                    LOG.info(f"使用备选字体: {font}")
                    douyin_font = font
                    break
        else:
            LOG.info(f"找到抖音字体: {douyin_font}")
        
        # 视频滤镜：假设输入已经是9:16比例的视频，只添加顶部和底部区域
        filter_chain = [
            # 保持视频原始尺寸（应该已经是720:1280）
            "scale=720:1280",  # 确保尺寸一致
            
            # 第1步：顶部区域 - 创建完全不透明的黑色背景
            "drawbox=x=0:y=0:w=720:h=128:color=black@1.0:t=fill",  # 完全不透明的黑色背景
            
            # 第2步：底部区域 - 创建单一浅米色背景
            # 底部区域从1080像素开始，高度为200像素（适合4行字幕）
            "drawbox=x=0:y=1080:w=720:h=200:color=#fbfbf3@1.0:t=fill",  # 底部区域浅米色不透明背景
            
            # 第3步：添加顶部文字（调大白色字体，使用粗体字体文件）
            f"drawtext=text='{top_text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=64-text_h/2:fontfile='{douyin_font}':shadowcolor=black@0.6:shadowx=1:shadowy=1:box=1:boxcolor=black@0.2:boxborderw=5",
        ]
        
        # 第4步：添加底部文字（鲜亮黄色字体带粗黑色描边，模拟图片效果）
        # 将底部文字分行并居中处理
        if bottom_text:
            # 分割英文和中文部分（如果有换行符）
            text_lines = bottom_text.split('\n')
            
            # 英文文本处理
            if len(text_lines) >= 1 and text_lines[0]:
                english_text = text_lines[0]
                
                # 判断英文是否过长需要分行（超过30个字符就分行）
                eng_fontsize = 36
                if len(english_text) > 30:
                    # 找到适合分行的位置（句子中间的空格）
                    words = english_text.split(' ')
                    total_words = len(words)
                    half_point = total_words // 2
                    
                    # 找到接近中点的空格位置
                    eng_first_line = ' '.join(words[:half_point])
                    eng_second_line = ' '.join(words[half_point:])
                    
                    # 添加英文第一行
                    filter_chain.append(
                        f"drawtext=text='{eng_first_line}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1100-text_h/2:fontfile='{douyin_font}':"
                        f"bordercolor=black:borderw=4:box=0"
                    )
                    
                    # 添加英文第二行
                    filter_chain.append(
                        f"drawtext=text='{eng_second_line}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1140-text_h/2:fontfile='{douyin_font}':"
                        f"bordercolor=black:borderw=4:box=0"
                    )
                else:
                    # 英文行 - 位置在底部区域的上半部分
                    filter_chain.append(
                        f"drawtext=text='{english_text}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1120-text_h/2:fontfile='{douyin_font}':"
                        f"bordercolor=black:borderw=4:box=0"
                    )
            
            # 中文文本处理
            if len(text_lines) >= 2 and text_lines[1]:
                chinese_text = text_lines[1]
                
                # 判断中文是否过长需要分行（超过15个汉字就分行）
                cn_fontsize = 32
                if len(chinese_text) > 15:
                    # 尽量在中间位置分行
                    half_point = len(chinese_text) // 2
                    
                    # 寻找接近中点的标点符号或空格
                    cn_split_point = half_point
                    for i in range(half_point-3, half_point+3):
                        if 0 <= i < len(chinese_text) and (chinese_text[i] in '，。！？,. ' or chinese_text[i].isspace()):
                            cn_split_point = i + 1
                            break
                    
                    cn_first_line = chinese_text[:cn_split_point]
                    cn_second_line = chinese_text[cn_split_point:]
                    
                    # 添加中文第一行
                    filter_chain.append(
                        f"drawtext=text='{cn_first_line}':fontcolor=#FFFF00:fontsize={cn_fontsize}:"
                        f"x=(w-text_w)/2:y=1180-text_h/2:fontfile='{douyin_font}':"
                        f"bordercolor=black:borderw=3:box=0"
                    )
                    
                    # 添加中文第二行
                    filter_chain.append(
                        f"drawtext=text='{cn_second_line}':fontcolor=#FFFF00:fontsize={cn_fontsize}:"
                        f"x=(w-text_w)/2:y=1220-text_h/2:fontfile='{douyin_font}':"
                        f"bordercolor=black:borderw=3:box=0"
                    )
                else:
                    # 中文行 - 位置在底部区域的下半部分
                    filter_chain.append(
                        f"drawtext=text='{chinese_text}':fontcolor=#FFFF00:fontsize={cn_fontsize}:"
                        f"x=(w-text_w)/2:y=1200-text_h/2:fontfile='{douyin_font}':"
                        f"bordercolor=black:borderw=3:box=0"
                    )
            
            # 如果只有一行文本，居中显示
            if len(text_lines) == 1 and not (len(text_lines[0]) > 30):
                filter_chain.append(
                    f"drawtext=text='{text_lines[0]}':fontcolor=#FFFF00:fontsize=36:"
                    f"x=(w-text_w)/2:y=1180-text_h/2:fontfile='{douyin_font}':"
                    f"bordercolor=black:borderw=4:box=0"
                )
        
        # 第5步：如果提供了重点单词信息，添加单词展示区域
        if keyword_text and isinstance(keyword_text, dict):
            # 获取单词信息
            word = keyword_text.get('word', '')
            phonetic = keyword_text.get('phonetic', '')
            meaning = keyword_text.get('meaning', '')
            
            if word:
                # 字体大小设置
                word_fontsize = 128     # 英文单词字体大小 - 英文大字
                meaning_fontsize = 48   # 中文释义字体大小 - 中文中字
                phonetic_fontsize = 26  # 音标字体大小 - 音标小字
                
                # 计算文本垂直位置和行间距
                base_y = 830  # 矩形框顶部Y坐标，从900调整到830，往上移
                line_height_1 = 110  # 第一行(英文大字)到第二行(中文小字)的行高
                line_height_2 = 60   # 第二行(中文小字)到第三行(音标小字)的行高
                padding_y = 30  # 垂直内边距
                
                # 计算三行文本的垂直位置
                word_y = base_y + padding_y
                meaning_y = word_y + line_height_1
                phonetic_y = meaning_y + line_height_2
                
                # 根据单词长度调整宽度
                # 更精确地估算字符宽度（考虑更新的字体大小）
                word_width = len(word) * 48      # 128px字体下英文字符约48像素
                meaning_width = len(meaning) * 36 if meaning else 0   # 64px字体下中文字符约36像素
                phonetic_width = len(phonetic) * 10 if phonetic else 0  # 26px字体下音标字符约10像素
                
                # 取最宽的文本长度
                max_text_len = max(word_width, meaning_width, phonetic_width)
                
                # 计算宽度，使用更小的内边距
                padding_x = 40  # 左右各20像素的内边距
                rect_width = max(250, min(max_text_len + padding_x, 700))
                center_x = 360  # 屏幕中心水平坐标
                rect_x = center_x - rect_width/2
                
                # 计算矩形高度，考虑不同行高
                if meaning and phonetic:
                    # 全部三行
                    rect_height = padding_y + line_height_1 + line_height_2 + padding_y + 10
                elif meaning:
                    # 两行：单词+中文
                    rect_height = padding_y + line_height_1 + padding_y
                elif phonetic:
                    # 两行：单词+音标
                    rect_height = padding_y + line_height_1 + padding_y
                else:
                    # 只有单词一行
                    rect_height = padding_y + 90 + padding_y  # 单词行高设为90
                
                # 添加亮黄色背景框 - 使用亮黄色 #FFFF00
                filter_chain.append(f"drawbox=x={rect_x}:y={base_y}:w={rect_width}:h={rect_height}:color=#FFFF00@1.0:t=fill")
                
                # 在背景框上添加文本
                # 添加单词文本（英文单词）
                filter_chain.append(f"drawtext=text='{word}':fontcolor=black:fontsize={word_fontsize}:x={center_x}-text_w/2:y={word_y}:fontfile='{douyin_font}'")
                
                # 如果有中文释义，添加释义文本
                if meaning:
                    filter_chain.append(f"drawtext=text='{meaning}':fontcolor=black:fontsize={meaning_fontsize}:x={center_x}-text_w/2:y={meaning_y}:fontfile='{douyin_font}'")
                
                # 如果有音标，添加音标文本
                if phonetic:
                    filter_chain.append(f"drawtext=text='{phonetic}':fontcolor=black:fontsize={phonetic_fontsize}:x={center_x}-text_w/2:y={phonetic_y}:fontfile='{douyin_font}'")
        
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
        try:
            import subprocess
            
            if progress_callback:
                progress_callback("🎬 开始视频烧制处理...")
            
            if not burn_data:
                if progress_callback:
                    progress_callback("❌ 没有找到字幕数据，无法烧制")
                return False
            
            # 获取有关键词的字幕数量
            keyword_segments = [item for item in burn_data if item['has_keyword']]
            if progress_callback:
                progress_callback(f"📊 共 {len(burn_data)} 条字幕，其中 {len(keyword_segments)} 条有重点单词")
            
            # 处理每个字幕段落
            for i, item in enumerate(burn_data):
                if progress_callback and i % 10 == 0:  # 每处理10个字幕更新一次进度
                    if item['has_keyword']:
                        progress_callback(f"🔄 处理字幕 {i+1}/{len(burn_data)}: 关键词 {item['keyword']}")
                    else:
                        progress_callback(f"🔄 处理字幕 {i+1}/{len(burn_data)}")
                
                # 构建底部字幕文本（英文+中文）
                bottom_text = ""
                if item['english_text']:
                    bottom_text = item['english_text']
                if item['chinese_text']:
                    if bottom_text:
                        bottom_text += "\n"
                    bottom_text += item['chinese_text']
                
                # 提取时间段
                start_time = item['begin_time']
                end_time = item['end_time']
                
                # 为当前时间段创建临时输出文件
                temp_output = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                LOG.info(f"temp_output: {temp_output}")
                # 裁剪当前时间段的视频
                segment_cmd = [
                    'ffmpeg', '-y',
                    '-i', input_video,
                    '-ss', str(start_time),
                    '-to', str(end_time),
                    '-c:v', 'libx264', '-c:a', 'aac',
                    '-vsync', '2',  # 保持视频同步
                    self.temp_dir + f"/temp_segment_{i}.mp4"
                ]
                
                # 执行裁剪命令
                proc = subprocess.Popen(
                    segment_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                proc.communicate()
                
                # 构建关键词信息（如果有）
                keyword_info = None
                if item['has_keyword']:
                    keyword_info = {
                        'word': item['keyword'],
                        'phonetic': item['phonetic'],
                        'meaning': item['explanation']
                    }
                
                # 为当前片段应用视频滤镜
                video_filter = self._build_video_filter(title_text, bottom_text, keyword_info)
                
                process_cmd = [
                    'ffmpeg', '-y',
                    '-i', self.temp_dir + f"/temp_segment_{i}.mp4",
                    '-vf', video_filter,
                    '-aspect', '9:16',  # 设置宽高比为9:16
                    '-c:a', 'copy',  # 音频直接复制
                    '-preset', 'medium',
                    '-crf', '23',
                    temp_output
                ]
                
                # 执行处理命令
                proc = subprocess.Popen(
                    process_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                proc.communicate()
            
            # 创建包含所有处理过的片段的文件列表
            segments_list_path = os.path.join(self.temp_dir, "segments.txt")
            with open(segments_list_path, 'w') as f:
                for i in range(len(burn_data)):
                    f.write(f"file '{self.temp_dir}/segment_{i}.mp4'\n")
            
            # 使用concat过滤器合并所有片段
            concat_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', segments_list_path,
                '-c', 'copy',
                output_video
            ]
            
            if progress_callback:
                progress_callback("🔄 合并所有视频片段...")
            
            # 执行合并命令
            proc = subprocess.Popen(
                concat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = proc.communicate()
            
            if proc.returncode == 0:
                if progress_callback:
                    progress_callback("✅ 视频烧制完成！")
                LOG.info(f"✅ 视频烧制成功: {output_video}")
                return True
            else:
                error_msg = f"合并视频失败: {stderr}"
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
            pass
            # 清理临时文件
            # try:
            #     # 保留临时目录，但清理里面的文件，以便下次使用
            #     for file in os.listdir(self.temp_dir):
            #         try:
            #             os.remove(os.path.join(self.temp_dir, file))
            #         except:
            #             pass
            # except:
            #     pass
    
    def process_series_video(self, 
                            series_id: int, 
                            output_dir: str = "input",
                            title_text: str = "第三遍：重点词汇+字幕",
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
            
            # 检查是否存在预处理的9:16视频
            input_video = None
            if 'new_file_path' in target_series and target_series['new_file_path'] and os.path.exists(target_series['new_file_path']):
                input_video = target_series['new_file_path']
                if progress_callback:
                    progress_callback(f"📹 使用预处理的9:16视频: {os.path.basename(input_video)}")
            else:
                # 获取原视频路径
                input_video = target_series.get('file_path')
                if not input_video or not os.path.exists(input_video):
                    if progress_callback:
                        progress_callback("❌ 找不到视频文件")
                    return None
                
                if progress_callback:
                    progress_callback(f"📹 使用原始视频文件: {os.path.basename(input_video)}")
            
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
            
            # 获取原始文件名中的基础部分（例如从9_1.mp4中提取9）
            input_basename = os.path.basename(input_video)
            if "_" in input_basename:
                base_name = input_basename.split("_")[0]  # 获取下划线前的部分（例如9）
            else:
                # 如果没有下划线，直接使用文件名（不含扩展名）
                base_name = os.path.splitext(input_basename)[0]
            
            # 生成新的文件名：基础名称_3.mp4
            output_video = os.path.join(output_dir, f"{base_name}_3.mp4")
            
            if progress_callback:
                progress_callback(f"📋 输入视频: {input_basename}, 输出视频: {base_name}_3.mp4")
            
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
            
            # 筛选出有关键词的数据
            keyword_data = [item for item in burn_data if item['has_keyword']]
            
            # 统计信息
            total_subtitles = len(burn_data)
            total_keywords = len(keyword_data)
            total_duration = sum(item['duration'] for item in burn_data)
            keyword_duration = sum(item['duration'] for item in keyword_data)
            
            # 词频分布
            coca_ranges = {
                '500-5000': 0,
                '5000-10000': 0,
                '10000+': 0
            }
            
            for item in keyword_data:
                coca_rank = item['coca_rank']
                if coca_rank:
                    if 500 < coca_rank <= 5000:
                        coca_ranges['500-5000'] += 1
                    elif 5000 < coca_rank <= 10000:
                        coca_ranges['5000-10000'] += 1
                    else:
                        coca_ranges['10000+'] += 1
            
            # 示例单词（前5个）
            sample_keywords = keyword_data[:5] if keyword_data else []
            
            # 转换为展示格式
            preview_keywords = []
            for item in sample_keywords:
                preview_keywords.append({
                    'keyword': item['keyword'],
                    'phonetic': item['phonetic'],
                    'explanation': item['explanation'],
                    'coca_rank': item['coca_rank']
                })
            
            return {
                'total_subtitles': total_subtitles,
                'total_keywords': total_keywords,
                'total_duration': round(total_duration, 2),
                'keyword_duration': round(keyword_duration, 2),
                'coca_distribution': coca_ranges,
                'sample_keywords': preview_keywords,
                'estimated_file_size': f"{(total_duration/60) * 15:.1f} MB",  # 估算: 每分钟约15MB
                'title': "第三遍：重点词汇+字幕"
            }
            
        except Exception as e:
            LOG.error(f"获取烧制预览失败: {e}")
            return {
                'total_subtitles': 0,
                'total_keywords': 0,
                'total_duration': 0,
                'keyword_duration': 0,
                'coca_distribution': {},
                'sample_keywords': [],
                'estimated_file_size': '0 MB',
                'title': "第三遍：重点词汇+字幕"
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