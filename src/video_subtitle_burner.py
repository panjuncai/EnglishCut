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
        # 转义文本中的特殊字符，防止FFmpeg命令解析错误
        def escape_text(text):
            if not text:
                return ""
            # 转义FFmpeg命令中的特殊字符，特别是:,'等会影响命令解析的字符
            # 单引号需要特别处理，在FFmpeg中使用\'转义
            escaped = text.replace("\\", "\\\\").replace(":", "\\\\:").replace("'", "`")
            # 逗号和等号也可能导致解析问题
            escaped = escaped.replace(",", "\\\\,").replace("=", "\\\\=")
            return escaped
        
        # 转义各文本
        top_text_escaped = escape_text(top_text)
        
        # 检查字体路径，优先使用抖音字体，找不到再使用苹方
        douyin_font = '/Users/panjc/Library/Fonts/DouyinSansBold.ttf'
        
        # 专门用于音标的字体，优先使用支持IPA的字体
        phonetic_fonts = [
            '/Users/panjc/Library/Fonts/NotoSans-Regular.ttf',  # Google Noto字体如果已安装
        ]
        
        # 选择一个可用的音标字体
        phonetic_font = None
        for font in phonetic_fonts:
            if os.path.exists(font):
                phonetic_font = font
                # LOG.info(f"使用音标字体: {phonetic_font}")
                break
        
        if not phonetic_font:
            LOG.warning("未找到合适的音标字体，将使用常规字体，可能导致音标显示不完整")
            phonetic_font = douyin_font  # 如果找不到专用字体，退回到常规字体
        
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
            pass
            # LOG.info(f"找到抖音字体: {douyin_font}")
        
        # 视频滤镜：假设输入已经是9:16比例的视频，只添加顶部和底部区域
        filter_chain = [
            # 保持视频原始尺寸（应该已经是720:1280）
            "scale=720:1280",  # 确保尺寸一致
            
            # 第1步：顶部区域 - 创建完全不透明的黑色背景
            "drawbox=x=0:y=0:w=720:h=128:color=black@1.0:t=fill",  # 完全不透明的黑色背景
            
            # 第2步：底部区域 - 创建单一浅米色背景
            # 底部区域从1080像素开始，高度为270像素（适合最多5行字幕：3行英文+2行中文）
            "drawbox=x=0:y=1070:w=720:h=270:color=#fbfbf3@1.0:t=fill",  # 底部区域浅米色不透明背景
            
            # 第3步：添加顶部文字（调大白色字体，使用粗体字体文件）
            f"drawtext=text='{top_text_escaped}':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=64-text_h/2:fontfile='{douyin_font}':shadowcolor=black@0.6:shadowx=1:shadowy=1:box=1:boxcolor=black@0.2:boxborderw=5",
        ]
        
        # 第4步：添加底部文字（鲜亮黄色字体带粗黑色描边，模拟图片效果）
        # 将底部文字分行并居中处理
        if bottom_text:
            # 分割英文和中文部分（如果有换行符）
            text_lines = bottom_text.split('\n')
            
            # 英文文本处理
            if len(text_lines) >= 1 and text_lines[0]:
                english_text = text_lines[0]
                english_text_escaped = escape_text(english_text)
                
                # 判断英文是否过长需要分行（基于字符数判断）
                eng_fontsize = 36
                if len(english_text) > 45:  # 如果超过45个字符，分为三行
                    # 尝试更智能地分割句子
                    words = english_text.split(' ')
                    total_words = len(words)
                    
                    # 计算每行大约的单词数
                    words_per_line = total_words // 3
                    
                    # 确保第一行和第二行的结束位置在合理的位置（句子中间的空格）
                    first_line_end = words_per_line
                    second_line_end = words_per_line * 2
                    
                    # 微调分割点，尽量在标点或句子自然断点处分行
                    # 第一行分割点调整
                    for i in range(first_line_end-3, first_line_end+3):
                        if 0 <= i < total_words and i < second_line_end-5:
                            word = words[i]
                            if word.endswith(('.', ',', ';', ':', '?', '!')):
                                first_line_end = i + 1
                                break
                    
                    # 第二行分割点调整
                    for i in range(second_line_end-3, second_line_end+3):
                        if first_line_end < i < total_words:
                            word = words[i]
                            if word.endswith(('.', ',', ';', ':', '?', '!')):
                                second_line_end = i + 1
                                break
                    
                    eng_first_line = ' '.join(words[:first_line_end])
                    eng_second_line = ' '.join(words[first_line_end:second_line_end])
                    eng_third_line = ' '.join(words[second_line_end:])
                    
                    eng_first_line_escaped = escape_text(eng_first_line)
                    eng_second_line_escaped = escape_text(eng_second_line)
                    eng_third_line_escaped = escape_text(eng_third_line)
                    
                    # 添加英文第一行
                    # -10 是上移10像素
                    filter_chain.append(
                        f"drawtext=text='{eng_first_line_escaped}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1110-text_h/2-10:fontfile='{douyin_font}':"
                        f"bordercolor=black:borderw=4:box=0"
                    )
                    
                    # 添加英文第二行
                    filter_chain.append(
                        f"drawtext=text='{eng_second_line_escaped}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1150-text_h/2-10:fontfile='{douyin_font}':"
                        f"bordercolor=black:borderw=4:box=0"
                    )
                    
                    # 添加英文第三行
                    filter_chain.append(
                        f"drawtext=text='{eng_third_line_escaped}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1170-text_h/2+5:fontfile='{douyin_font}':"  # Y坐标从1160调整到1170
                        f"bordercolor=black:borderw=4:box=0"
                    )
                    
                elif len(english_text) > 30:  # 如果超过30个字符，分为两行
                    # 找到适合分行的位置（句子中间的空格）
                    words = english_text.split(' ')
                    total_words = len(words)
                    half_point = total_words // 2
                    
                    # 找到接近中点的空格位置，尽量在标点或句子自然断点处分行
                    for i in range(half_point-3, half_point+3):
                        if 0 <= i < total_words:
                            word = words[i]
                            if word.endswith(('.', ',', ';', ':', '?', '!')):
                                half_point = i + 1
                                break
                    
                    eng_first_line = ' '.join(words[:half_point])
                    eng_second_line = ' '.join(words[half_point:])
                    
                    # 转义分行后的文本
                    eng_first_line_escaped = escape_text(eng_first_line)
                    eng_second_line_escaped = escape_text(eng_second_line)
                    
                    # 添加英文第一行
                    filter_chain.append(
                        f"drawtext=text='{eng_first_line_escaped}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1100-text_h/2+10:fontfile='{douyin_font}':"  # Y坐标下移10像素
                        f"bordercolor=black:borderw=4:box=0"
                    )
                    
                    # 添加英文第二行
                    filter_chain.append(
                        f"drawtext=text='{eng_second_line_escaped}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1140-text_h/2+10:fontfile='{douyin_font}':"  # Y坐标下移10像素
                        f"bordercolor=black:borderw=4:box=0"
                    )
                else:
                    # 英文行 - 位置在底部区域的上半部分
                    filter_chain.append(
                        f"drawtext=text='{english_text_escaped}':fontcolor=#FFFF00:fontsize={eng_fontsize}:"
                        f"x=(w-text_w)/2:y=1130-text_h/2+10:fontfile='{douyin_font}':"  # Y坐标从1120调整到1130
                        f"bordercolor=black:borderw=4:box=0"
                    )
            
            # 中文文本处理
            if len(text_lines) >= 2 and text_lines[1]:
                chinese_text = text_lines[1]
                chinese_text_escaped = escape_text(chinese_text)
                
                # 确定中文字幕的垂直位置（根据英文的行数调整）
                cn_fontsize = 32
                
                # 根据英文行数动态调整中文位置
                if len(english_text) > 45:  # 三行英文
                    cn_base_y = 1210  # 从1240(1200+40)调整到1210，上移30像素
                elif len(english_text) > 30:  # 两行英文
                    cn_base_y = 1190  # 从1200调整到1190，上移10像素
                else:  # 单行英文
                    cn_base_y = 1180  # 从1200调整到1180，上移20像素
                
                # 判断中文是否过长需要分行（超过15个汉字就分行）
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
                    
                    # 转义分行后的文本
                    cn_first_line_escaped = escape_text(cn_first_line)
                    cn_second_line_escaped = escape_text(cn_second_line)
                    
                    # 添加中文第一行（根据英文行数调整位置）
                    filter_chain.append(
                        f"drawtext=text='{cn_first_line_escaped}':fontcolor=#FFFF00:fontsize={cn_fontsize}:"
                        f"x=(w-text_w)/2:y={cn_base_y}-text_h/2+10:fontfile='{douyin_font}':"  # Y坐标下移10像素
                        f"bordercolor=black:borderw=3:box=0"
                    )
                    # LOG.info(f"添加中文第一行: {cn_first_line_escaped}")
                    
                    # 添加中文第二行
                    filter_chain.append(
                        f"drawtext=text='{cn_second_line_escaped}':fontcolor=#FFFF00:fontsize={cn_fontsize}:"
                        f"x=(w-text_w)/2:y={cn_base_y+40}-text_h/2+10:fontfile='{douyin_font}':"  # Y坐标下移10像素
                        f"bordercolor=black:borderw=3:box=0"
                    )
                    # LOG.info(f"添加中文第二行: {cn_second_line_escaped}")
                else:
                    # 中文行 - 位置在底部区域的下半部分（根据英文行数调整）
                    filter_chain.append(
                        f"drawtext=text='{chinese_text_escaped}':fontcolor=#FFFF00:fontsize={cn_fontsize}:"
                        f"x=(w-text_w)/2:y={cn_base_y}-text_h/2+10:fontfile='{douyin_font}':"  # Y坐标下移10像素
                        f"bordercolor=black:borderw=3:box=0"
                    )
            
            # 如果只有一行文本，居中显示
            if len(text_lines) == 1 and not (len(text_lines[0]) > 30):
                text_escaped = escape_text(text_lines[0])
                filter_chain.append(
                    f"drawtext=text='{text_escaped}':fontcolor=#FFFF00:fontsize=36:"
                    f"x=(w-text_w)/2:y=1180-text_h/2+10:fontfile='{douyin_font}':"  # Y坐标下移10像素
                    f"bordercolor=black:borderw=4:box=0"
                )
        
        # 第5步：如果提供了重点单词信息，添加单词展示区域
        if keyword_text and isinstance(keyword_text, dict):
            # 获取单词信息并转义
            word = escape_text(keyword_text.get('word', ''))
            phonetic = escape_text(keyword_text.get('phonetic', ''))
            meaning = escape_text(keyword_text.get('meaning', ''))
            
            if word:
                # 字体大小设置 - 根据单词长度自适应调整
                # 短单词用大字体，长单词用小字体
                original_word = keyword_text.get('word', '')
                if len(original_word) > 10:  # 超过10个字母就用小字体
                    word_fontsize = 64     # 较长单词使用较小字体
                else:
                    word_fontsize = 152    # 短单词使用更大字体
                
                meaning_fontsize = 48   # 中文释义字体大小 - 中文中字
                phonetic_fontsize = 24  # 音标字体大小 - 音标小字
                
                # 计算文本垂直位置和行间距
                # 根据单词长度调整垂直位置
                if len(original_word) > 10:
                    base_y = 800  # 矩形框顶部Y坐标
                else:  # 短单词
                    base_y = 750  # 短单词时矩形框整体上移50像素，避免与底部重叠
                    
                line_height_1 = 150  # 第一行(英文大字)到第二行(中文小字)的行高，增加高度以适应更大字体
                line_height_2 = 70   # 第二行(中文小字)到第三行(音标小字)的行高
                padding_y = 30  # 垂直内边距
                
                # 计算三行文本的垂直位置 - 如果是小字体，调整Y坐标
                word_y = base_y + padding_y
                if len(original_word) > 10:
                    word_y -= 10  # 长单词时整体上移10像素
                
                # 根据单词长度调整行间距
                if len(original_word) > 10:
                    # 长单词时，减小行间距使布局更紧凑
                    adjusted_line_height_1 = 90  # 减小第一行到第二行的距离
                    adjusted_line_height_2 = 60  # 减小第二行到第三行的距离
                else:
                    # 短单词时使用正常行间距
                    adjusted_line_height_1 = line_height_1
                    adjusted_line_height_2 = line_height_2
                
                # 计算中文和音标位置（根据单词长度调整）
                meaning_y = word_y + adjusted_line_height_1
                phonetic_y = meaning_y + adjusted_line_height_2
                
                # 根据单词长度调整宽度和估算字符宽度
                if len(original_word) > 10:
                    # 小字体(64px)下的估算宽度
                    word_width = len(original_word) * 30  # 64px字体下英文字符约30像素
                else:
                    # 大字体(152px)下的估算宽度
                    word_width = len(original_word) * 60  # 152px字体下英文字符约60像素
                
                meaning_width = len(keyword_text.get('meaning', '')) * 36 if keyword_text.get('meaning', '') else 0   # 48px字体下中文字符约36像素
                phonetic_width = len(keyword_text.get('phonetic', '')) * 10 if keyword_text.get('phonetic', '') else 0  # 24px字体下音标字符约10像素
                
                # 取最宽的文本长度
                max_text_len = max(word_width, meaning_width, phonetic_width)
                
                # 计算宽度，确保有足够边距
                padding_x = 100  # 左右各50像素的内边距，增加以确保更大字体有足够空间
                rect_width = max(350, min(max_text_len + padding_x, 700))
                center_x = 360  # 屏幕中心水平坐标
                rect_x = center_x - rect_width/2
                
                # 计算矩形高度，考虑不同行高
                if meaning and phonetic:
                    if len(original_word) > 10:
                        # 长单词情况下，三行内容需要更多空间
                        rect_height = padding_y + adjusted_line_height_1 + adjusted_line_height_2 + padding_y + 20
                    else:
                        # 短单词+大字体情况下使用更大的高度
                        rect_height = padding_y + line_height_1 + line_height_2 + padding_y + 30
                elif meaning:
                    if len(original_word) > 10:
                        # 长单词+中文释义情况
                        rect_height = padding_y + adjusted_line_height_1 + padding_y
                    else:
                        # 短单词+大字体+中文释义情况
                        rect_height = padding_y + line_height_1 + padding_y + 20
                elif phonetic:
                    if len(original_word) > 10:
                        # 长单词+音标情况
                        rect_height = padding_y + adjusted_line_height_1 + adjusted_line_height_2 + 20
                    else:
                        # 短单词+大字体+音标情况
                        rect_height = padding_y + line_height_1 + line_height_2 + 30
                else:
                    # 只有单词一行
                    if len(original_word) > 10:
                        rect_height = padding_y + 90 + padding_y  # 长单词行高
                    else:
                        rect_height = padding_y + 120 + padding_y  # 短单词大字体行高
                
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
                    filter_chain.append(f"drawtext=text='{phonetic}':fontcolor=black:fontsize={phonetic_fontsize}:x={center_x}-text_w/2:y={phonetic_y}:fontfile='{phonetic_font}'")
        
        # 最后，对整个滤镜字符串进行额外检查，确保没有未转义的特殊字符
        filter_str = ','.join(filter_chain)
        # LOG.debug(f"生成的滤镜字符串: {filter_str}")
        return filter_str
    
    def _build_keywords_only_filter(self, top_text: str, keyword_text: Dict = None) -> str:
        """
        构建只有顶部标题和关键词的FFmpeg视频滤镜，不添加底部字幕区域
        
        参数:
        - top_text: 顶部文字
        - keyword_text: 重点单词信息，格式为 {"word": "text", "phonetic": "音标", "meaning": "释义"}
        
        返回:
        - str: FFmpeg滤镜字符串
        """
        # 转义文本中的特殊字符，防止FFmpeg命令解析错误
        def escape_text(text):
            if not text:
                return ""
            # 转义FFmpeg命令中的特殊字符，特别是:,'等会影响命令解析的字符
            # 单引号需要特别处理，在FFmpeg中使用\'转义
            escaped = text.replace("\\", "\\\\").replace(":", "\\\\:").replace("'", "`")
            # 逗号和等号也可能导致解析问题
            escaped = escaped.replace(",", "\\\\,").replace("=", "\\\\=")
            return escaped
        
        # 转义各文本
        top_text_escaped = escape_text(top_text)
        
        # 检查字体路径，优先使用抖音字体，找不到再使用苹方
        douyin_font = '/Users/panjc/Library/Fonts/DouyinSansBold.ttf'
        
        # 专门用于音标的字体，优先使用支持IPA的字体
        phonetic_fonts = [
            '/Users/panjc/Library/Fonts/NotoSans-Regular.ttf',  # Google Noto字体如果已安装
        ]
        
        # 选择一个可用的音标字体
        phonetic_font = None
        for font in phonetic_fonts:
            if os.path.exists(font):
                phonetic_font = font
                break
        
        if not phonetic_font:
            LOG.warning("未找到合适的音标字体，将使用常规字体，可能导致音标显示不完整")
            phonetic_font = douyin_font  # 如果找不到专用字体，退回到常规字体
        
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
        
        # 视频滤镜：假设输入已经是9:16比例的视频，只添加顶部区域和关键词
        filter_chain = [
            # 保持视频原始尺寸（应该已经是720:1280）
            "scale=720:1280",  # 确保尺寸一致
            
            # 第1步：顶部区域 - 创建完全不透明的黑色背景
            "drawbox=x=0:y=0:w=720:h=128:color=black@1.0:t=fill",  # 完全不透明的黑色背景
            
            # 第2步：添加顶部文字（调大白色字体，使用粗体字体文件）
            f"drawtext=text='{top_text_escaped}':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=64-text_h/2:fontfile='{douyin_font}':shadowcolor=black@0.6:shadowx=1:shadowy=1:box=1:boxcolor=black@0.2:boxborderw=5",
        ]
        
        # 第3步：如果提供了重点单词信息，添加单词展示区域
        if keyword_text and isinstance(keyword_text, dict):
            # 获取单词信息并转义
            word = escape_text(keyword_text.get('word', ''))
            phonetic = escape_text(keyword_text.get('phonetic', ''))
            meaning = escape_text(keyword_text.get('meaning', ''))
            
            if word:
                # 字体大小设置 - 根据单词长度自适应调整
                # 短单词用大字体，长单词用小字体
                original_word = keyword_text.get('word', '')
                if len(original_word) > 10:  # 超过10个字母就用小字体
                    word_fontsize = 64     # 较长单词使用较小字体
                else:
                    word_fontsize = 152    # 短单词使用更大字体
                
                meaning_fontsize = 48   # 中文释义字体大小 - 中文中字
                phonetic_fontsize = 24  # 音标字体大小 - 音标小字
                
                # 计算文本垂直位置和行间距
                # 根据单词长度调整垂直位置
                if len(original_word) > 10:
                    base_y = 800  # 矩形框顶部Y坐标
                else:  # 短单词
                    base_y = 750  # 短单词时矩形框整体上移50像素，避免与底部重叠
                    
                line_height_1 = 150  # 第一行(英文大字)到第二行(中文小字)的行高，增加高度以适应更大字体
                line_height_2 = 70   # 第二行(中文小字)到第三行(音标小字)的行高
                padding_y = 30  # 垂直内边距
                
                # 计算三行文本的垂直位置 - 如果是小字体，调整Y坐标
                word_y = base_y + padding_y
                if len(original_word) > 10:
                    word_y -= 10  # 长单词时整体上移10像素
                
                # 根据单词长度调整行间距
                if len(original_word) > 10:
                    # 长单词时，减小行间距使布局更紧凑
                    adjusted_line_height_1 = 90  # 减小第一行到第二行的距离
                    adjusted_line_height_2 = 60  # 减小第二行到第三行的距离
                else:
                    # 短单词时使用正常行间距
                    adjusted_line_height_1 = line_height_1
                    adjusted_line_height_2 = line_height_2
                
                # 计算中文和音标位置（根据单词长度调整）
                meaning_y = word_y + adjusted_line_height_1
                phonetic_y = meaning_y + adjusted_line_height_2
                
                # 根据单词长度调整宽度和估算字符宽度
                if len(original_word) > 10:
                    # 小字体(64px)下的估算宽度
                    word_width = len(original_word) * 30  # 64px字体下英文字符约30像素
                else:
                    # 大字体(152px)下的估算宽度
                    word_width = len(original_word) * 60  # 152px字体下英文字符约60像素
                
                meaning_width = len(keyword_text.get('meaning', '')) * 36 if keyword_text.get('meaning', '') else 0   # 48px字体下中文字符约36像素
                phonetic_width = len(keyword_text.get('phonetic', '')) * 10 if keyword_text.get('phonetic', '') else 0  # 24px字体下音标字符约10像素
                
                # 取最宽的文本长度
                max_text_len = max(word_width, meaning_width, phonetic_width)
                
                # 计算宽度，确保有足够边距
                padding_x = 100  # 左右各50像素的内边距，增加以确保更大字体有足够空间
                rect_width = max(350, min(max_text_len + padding_x, 700))
                center_x = 360  # 屏幕中心水平坐标
                rect_x = center_x - rect_width/2
                
                # 计算矩形高度，考虑不同行高
                if meaning and phonetic:
                    if len(original_word) > 10:
                        # 长单词情况下，三行内容需要更多空间
                        rect_height = padding_y + adjusted_line_height_1 + adjusted_line_height_2 + padding_y + 20
                    else:
                        # 短单词+大字体情况下使用更大的高度
                        rect_height = padding_y + line_height_1 + line_height_2 + padding_y + 30
                elif meaning:
                    if len(original_word) > 10:
                        # 长单词+中文释义情况
                        rect_height = padding_y + adjusted_line_height_1 + padding_y
                    else:
                        # 短单词+大字体+中文释义情况
                        rect_height = padding_y + line_height_1 + padding_y + 20
                elif phonetic:
                    if len(original_word) > 10:
                        # 长单词+音标情况
                        rect_height = padding_y + adjusted_line_height_1 + adjusted_line_height_2 + 20
                    else:
                        # 短单词+大字体+音标情况
                        rect_height = padding_y + line_height_1 + line_height_2 + 30
                else:
                    # 只有单词一行
                    if len(original_word) > 10:
                        rect_height = padding_y + 90 + padding_y  # 长单词行高
                    else:
                        rect_height = padding_y + 120 + padding_y  # 短单词大字体行高
                
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
                    filter_chain.append(f"drawtext=text='{phonetic}':fontcolor=black:fontsize={phonetic_fontsize}:x={center_x}-text_w/2:y={phonetic_y}:fontfile='{phonetic_font}'")
        
        # 返回滤镜字符串
        filter_str = ','.join(filter_chain)
        return filter_str
    
    def _build_no_subtitle_filter(self, top_text: str) -> str:
        """
        构建只有顶部标题的FFmpeg视频滤镜，不添加底部字幕区域和关键词
        
        参数:
        - top_text: 顶部文字
        
        返回:
        - str: FFmpeg滤镜字符串
        """
        # 转义文本中的特殊字符，防止FFmpeg命令解析错误
        def escape_text(text):
            if not text:
                return ""
            # 转义FFmpeg命令中的特殊字符，特别是:,'等会影响命令解析的字符
            escaped = text.replace("\\", "\\\\").replace(":", "\\\\:").replace("'", "`")
            # 逗号和等号也可能导致解析问题
            escaped = escaped.replace(",", "\\\\,").replace("=", "\\\\=")
            return escaped
        
        # 转义顶部文本
        top_text_escaped = escape_text(top_text)
        
        # 检查字体路径，优先使用抖音字体，找不到再使用苹方
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
        
        # 视频滤镜：假设输入已经是9:16比例的视频，只添加顶部区域
        filter_chain = [
            # 保持视频原始尺寸（应该已经是720:1280）
            "scale=720:1280",  # 确保尺寸一致
            
            # 第1步：顶部区域 - 创建完全不透明的黑色背景
            "drawbox=x=0:y=0:w=720:h=128:color=black@1.0:t=fill",  # 完全不透明的黑色背景
            
            # 第2步：添加顶部文字（调大白色字体，使用粗体字体文件）
            f"drawtext=text='{top_text_escaped}':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=64-text_h/2:fontfile='{douyin_font}':shadowcolor=black@0.6:shadowx=1:shadowy=1:box=1:boxcolor=black@0.2:boxborderw=5"
        ]
        
        # 返回滤镜字符串
        filter_str = ','.join(filter_chain)
        return filter_str
    
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
            successfully_processed_segments = []  # 跟踪成功处理的片段
            failed_segments = []  # 跟踪失败的片段
            
            for i, item in enumerate(burn_data):
                try:
                    # 记录开始处理此片段
                    LOG.info(f"开始处理第 {i+1}/{len(burn_data)} 个字幕片段")
                    
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
                    
                    # 检查时间段是否有效
                    if end_time <= start_time:
                        LOG.warning(f"片段 {i} 的时间段无效: {start_time}-{end_time}，尝试修复")
                        # 修复时间段，确保至少有0.1秒长度
                        end_time = start_time + 0.1
                    
                    duration = end_time - start_time
                    LOG.info(f"片段 {i}: 时间 {start_time:.2f}-{end_time:.2f}, 时长: {duration:.2f}秒")
                    
                    # 为当前时间段创建临时文件名
                    # 第一步：原视频裁剪后的临时文件
                    temp_segment_path = os.path.join(self.temp_dir, f"temp_segment_{i}.mp4")
                    # 第二步：添加字幕和关键词后的临时文件
                    processed_segment_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    
                    # 裁剪当前时间段的视频
                    segment_cmd = [
                        'ffmpeg', '-y',
                        '-i', input_video,
                        '-ss', str(start_time),
                        '-to', str(end_time),
                        '-c:v', 'libx264', '-c:a', 'aac',
                        '-vsync', '2',  # 保持视频同步
                        temp_segment_path
                    ]
                    
                    LOG.info(f"执行裁剪命令: {' '.join(segment_cmd)}")
                    
                    # 执行裁剪命令
                    proc = subprocess.Popen(
                        segment_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    stdout, stderr = proc.communicate()
                    
                    # 检查裁剪是否成功
                    if proc.returncode != 0:
                        LOG.error(f"片段 {i} 裁剪失败: {stderr}")
                        failed_segments.append(i)
                        continue
                    
                    # 验证裁剪后的文件是否存在且有效
                    if not os.path.exists(temp_segment_path) or os.path.getsize(temp_segment_path) == 0:
                        LOG.error(f"片段 {i} 裁剪后的文件无效: {temp_segment_path}")
                        failed_segments.append(i)
                        continue
                    
                    # LOG.info(f"片段 {i} 裁剪成功: {temp_segment_path}")
                    
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
                        '-i', temp_segment_path,
                        '-vf', video_filter,
                        '-aspect', '9:16',  # 设置宽高比为9:16
                        '-c:a', 'copy',  # 音频直接复制
                        '-preset', 'medium',
                        '-crf', '23',
                        processed_segment_path
                    ]
                    
                    # LOG.info(f"执行处理命令: {' '.join(process_cmd)}")
                    
                    # 执行处理命令
                    proc = subprocess.Popen(
                        process_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    stdout, stderr = proc.communicate()
                    
                    # 检查处理是否成功
                    if proc.returncode != 0:
                        LOG.error(f"片段 {i} 处理失败: {stderr}")
                        failed_segments.append(i)
                        continue
                    
                    # 验证处理后的文件是否存在且有效
                    if not os.path.exists(processed_segment_path) or os.path.getsize(processed_segment_path) == 0:
                        LOG.error(f"片段 {i} 处理后的文件无效: {processed_segment_path}")
                        failed_segments.append(i)
                        continue
                    
                    # LOG.info(f"片段 {i} 处理成功: {processed_segment_path}")
                    successfully_processed_segments.append(i)
                    
                    # 向前端发送处理成功的信息
                    if progress_callback and i % 5 == 0:  # 每5个片段更新一次，避免过于频繁
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
            
            # 报告处理结果
            LOG.info(f"成功处理 {len(successfully_processed_segments)}/{len(burn_data)} 个片段")
            if failed_segments:
                LOG.warning(f"失败片段索引: {failed_segments}")
            
            # 向前端发送处理结果统计
            if progress_callback:
                success_rate = len(successfully_processed_segments) / len(burn_data) * 100
                progress_callback(f"📊 成功处理 {len(successfully_processed_segments)}/{len(burn_data)} 个片段 ({success_rate:.1f}%)")
                if failed_segments:
                    progress_callback(f"⚠️ {len(failed_segments)} 个片段处理失败")
            
            # 只处理成功的片段
            if not successfully_processed_segments:
                if progress_callback:
                    progress_callback("❌ 没有成功处理的片段，无法生成视频")
                return False
            
            # 创建包含所有处理过的片段的文件列表
            segments_list_path = os.path.join(self.temp_dir, "segments.txt")
            LOG.info(f"创建片段列表文件: {segments_list_path}")
            
            with open(segments_list_path, 'w') as f:
                for i in successfully_processed_segments:
                    segment_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    # 再次验证文件存在
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        # 使用绝对路径，确保ffmpeg能找到文件
                        abs_segment_path = os.path.abspath(segment_path)
                        # 需要特殊处理路径中的单引号，替换为\'
                        escaped_path = abs_segment_path.replace("'", "\\'")
                        f.write(f"file '{escaped_path}'\n")
                        LOG.info(f"添加片段到列表: {abs_segment_path}")
                    else:
                        LOG.warning(f"跳过无效片段文件: {segment_path}")
            
            # 显示segments.txt文件内容用于调试
            try:
                with open(segments_list_path, 'r') as f:
                    content = f.read()
                    LOG.info(f"segments.txt内容:\n{content}")
            except Exception as e:
                LOG.error(f"无法读取segments.txt: {e}")
            
            if progress_callback:
                progress_callback("🔄 合并所有视频片段...")
                
            # 使用concat过滤器合并所有片段
            concat_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', segments_list_path,
                '-c', 'copy',
                output_video
            ]
            
            # LOG.info(f"执行合并命令: {' '.join(concat_cmd)}")
            
            # 执行合并命令
            proc = subprocess.Popen(
                concat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = proc.communicate()
            
            # 详细记录stderr以便调试
            # if stderr:
            #     LOG.info(f"FFmpeg合并输出: {stderr}")
            
            # 检查输出文件
            if proc.returncode == 0 and os.path.exists(output_video) and os.path.getsize(output_video) > 0:
                if progress_callback:
                    # 添加关键词统计信息
                    keyword_count = sum(1 for item in burn_data if item['has_keyword'])
                    
                    # 词频分布统计
                    coca_ranges = {
                        '500-5000': 0,
                        '5000-10000': 0,
                        '10000以上': 0
                    }
                    
                    for item in burn_data:
                        if item['has_keyword'] and item['coca_rank']:
                            coca_rank = item['coca_rank']
                            if 500 < coca_rank <= 5000:
                                coca_ranges['500-5000'] += 1
                            elif 5000 < coca_rank <= 10000:
                                coca_ranges['5000-10000'] += 1
                            else:
                                coca_ranges['10000以上'] += 1
                    
                    # 添加统计信息到进度
                    progress_callback("📈 关键词统计:")
                    progress_callback(f"  - 总计: {keyword_count} 个单词")
                    progress_callback(f"  - 500-5000: {coca_ranges['500-5000']} 个")
                    progress_callback(f"  - 5000-10000: {coca_ranges['5000-10000']} 个")
                    progress_callback(f"  - 10000以上: {coca_ranges['10000以上']} 个")
                    progress_callback("✅ 视频烧制完成！")
                
                LOG.info(f"✅ 视频烧制成功: {output_video}, 大小: {os.path.getsize(output_video)/1024/1024:.2f}MB")
                return True
            else:
                # 合并失败，尝试替代方案
                if progress_callback:
                    progress_callback("⚠️ 标准合并失败，尝试替代方案...")
                
                LOG.warning(f"标准合并失败，尝试使用过滤器链方式合并")
                
                # 构建过滤器复杂链
                filter_complex = []
                for idx, i in enumerate(successfully_processed_segments):
                    segment_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    # 确保文件存在
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        filter_complex.append(f"[{idx}:v][{idx}:a]")
                
                if not filter_complex:
                    error_msg = "所有片段都无效，无法生成视频"
                    if progress_callback:
                        progress_callback(f"❌ {error_msg}")
                    LOG.error(error_msg)
                    return False
                
                # 构建备用命令
                inputs = []
                for i in successfully_processed_segments:
                    segment_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        inputs.extend(['-i', segment_path])
                
                # 如果只有一个片段，直接复制
                if len(successfully_processed_segments) == 1:
                    segment_path = os.path.join(self.temp_dir, f"segment_{successfully_processed_segments[0]}.mp4")
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        fallback_cmd = [
                            'ffmpeg', '-y',
                            '-i', segment_path,
                            '-c', 'copy',
                            output_video
                        ]
                else:
                    # 构建备用命令
                    filter_str = ''.join(filter_complex) + f"concat=n={len(filter_complex)}:v=1:a=1[outv][outa]"
                    fallback_cmd = [
                        'ffmpeg', '-y'
                    ] + inputs + [
                        '-filter_complex', filter_str,
                        '-map', '[outv]',
                        '-map', '[outa]',
                        '-preset', 'medium',
                        '-crf', '23',
                        output_video
                    ]
                
                LOG.info(f"执行备用合并命令: {' '.join(fallback_cmd)}")
                
                if progress_callback:
                    progress_callback("🔄 尝试备用合并方法...")
                
                # 执行备用命令
                proc = subprocess.Popen(
                    fallback_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                stdout, stderr = proc.communicate()
                
                if proc.returncode == 0 and os.path.exists(output_video) and os.path.getsize(output_video) > 0:
                    if progress_callback:
                        progress_callback("✅ 备用方法视频烧制完成！")
                    LOG.info(f"✅ 备用方法视频烧制成功: {output_video}")
                    return True
                else:
                    error_msg = f"备用合并方法也失败: {stderr}"
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
                # 清理临时视频文件
                for i in range(len(burn_data)):
                    temp_files = [
                        os.path.join(self.temp_dir, f"temp_segment_{i}.mp4"),
                        os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    ]
                    for temp_file in temp_files:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            LOG.debug(f"已删除临时文件: {temp_file}")
                
                # 删除临时片段列表文件
                segments_list_path = os.path.join(self.temp_dir, "segments.txt")
                if os.path.exists(segments_list_path):
                    os.remove(segments_list_path)
                    LOG.debug("已删除临时片段列表文件")
                
                LOG.info("🧹 临时文件清理完成")
            except Exception as e:
                LOG.warning(f"清理临时文件失败: {e}")
    
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
    
    def process_keywords_only_video(self, 
                                   series_id: int, 
                                   output_dir: str = "input",
                                   title_text: str = "",
                                   progress_callback=None) -> Optional[str]:
        """
        处理只烧制关键词（没有字幕）的视频
        
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
                progress_callback("🔍 开始处理只烧制关键词的视频...")
            
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
            
            # 筛选出有关键词的段落
            keyword_data = [item for item in burn_data if item['has_keyword']]
            if not keyword_data:
                if progress_callback:
                    progress_callback("⚠️ 没有找到有关键词的段落")
                return None
            
            if progress_callback:
                progress_callback(f"📚 找到 {len(keyword_data)} 个有关键词的段落用于烧制")
            
            # 准备输出路径
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取原始文件名中的基础部分（例如从9_1.mp4中提取9）
            input_basename = os.path.basename(input_video)
            if "_" in input_basename:
                base_name = input_basename.split("_")[0]  # 获取下划线前的部分（例如9）
            else:
                # 如果没有下划线，直接使用文件名（不含扩展名）
                base_name = os.path.splitext(input_basename)[0]
            
            # 生成新的文件名：基础名称_2.mp4
            output_video = os.path.join(output_dir, f"{base_name}_2.mp4")
            
            if progress_callback:
                progress_callback(f"📋 输入视频: {input_basename}, 输出视频: {base_name}_2.mp4")
            
            # 执行烧制 - 只处理有关键词的段落
            import subprocess
            
            if progress_callback:
                progress_callback("🎬 开始只烧制关键词处理...")
            
            # 处理每个有关键词的段落
            successfully_processed_segments = []  # 跟踪成功处理的片段
            failed_segments = []  # 跟踪失败的片段
            
            for i, item in enumerate(keyword_data):
                try:
                    # 记录开始处理此片段
                    LOG.info(f"开始处理第 {i+1}/{len(keyword_data)} 个关键词片段")
                    
                    if progress_callback and i % 10 == 0:  # 每处理10个关键词更新一次进度
                        progress_callback(f"🔄 处理关键词 {i+1}/{len(keyword_data)}: {item['keyword']}")
                    
                    # 提取时间段
                    start_time = item['begin_time']
                    end_time = item['end_time']
                    
                    # 检查时间段是否有效
                    if end_time <= start_time:
                        LOG.warning(f"片段 {i} 的时间段无效: {start_time}-{end_time}，尝试修复")
                        # 修复时间段，确保至少有0.1秒长度
                        end_time = start_time + 0.1
                    
                    duration = end_time - start_time
                    LOG.info(f"片段 {i}: 时间 {start_time:.2f}-{end_time:.2f}, 时长: {duration:.2f}秒")
                    
                    # 为当前时间段创建临时文件名
                    # 第一步：原视频裁剪后的临时文件
                    temp_segment_path = os.path.join(self.temp_dir, f"temp_segment_{i}.mp4")
                    # 第二步：添加关键词后的临时文件
                    processed_segment_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    
                    # 裁剪当前时间段的视频
                    segment_cmd = [
                        'ffmpeg', '-y',
                        '-i', input_video,
                        '-ss', str(start_time),
                        '-to', str(end_time),
                        '-c:v', 'libx264', '-c:a', 'aac',
                        '-vsync', '2',  # 保持视频同步
                        temp_segment_path
                    ]
                    
                    LOG.info(f"执行裁剪命令: {' '.join(segment_cmd)}")
                    
                    # 执行裁剪命令
                    proc = subprocess.Popen(
                        segment_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    stdout, stderr = proc.communicate()
                    
                    # 检查裁剪是否成功
                    if proc.returncode != 0:
                        LOG.error(f"片段 {i} 裁剪失败: {stderr}")
                        failed_segments.append(i)
                        continue
                    
                    # 验证裁剪后的文件是否存在且有效
                    if not os.path.exists(temp_segment_path) or os.path.getsize(temp_segment_path) == 0:
                        LOG.error(f"片段 {i} 裁剪后的文件无效: {temp_segment_path}")
                        failed_segments.append(i)
                        continue
                    
                    # 构建关键词信息
                    keyword_info = {
                        'word': item['keyword'],
                        'phonetic': item['phonetic'],
                        'meaning': item['explanation']
                    }
                    
                    # 为当前片段应用视频滤镜 - 使用只有关键词的滤镜
                    video_filter = self._build_keywords_only_filter(title_text, keyword_info)
                    
                    process_cmd = [
                        'ffmpeg', '-y',
                        '-i', temp_segment_path,
                        '-vf', video_filter,
                        '-aspect', '9:16',  # 设置宽高比为9:16
                        '-c:a', 'copy',  # 音频直接复制
                        '-preset', 'medium',
                        '-crf', '23',
                        processed_segment_path
                    ]
                    
                    # 执行处理命令
                    proc = subprocess.Popen(
                        process_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    stdout, stderr = proc.communicate()
                    
                    # 检查处理是否成功
                    if proc.returncode != 0:
                        LOG.error(f"片段 {i} 处理失败: {stderr}")
                        failed_segments.append(i)
                        continue
                    
                    # 验证处理后的文件是否存在且有效
                    if not os.path.exists(processed_segment_path) or os.path.getsize(processed_segment_path) == 0:
                        LOG.error(f"片段 {i} 处理后的文件无效: {processed_segment_path}")
                        failed_segments.append(i)
                        continue
                    
                    successfully_processed_segments.append(i)
                    
                    # 向前端发送处理成功的信息
                    if progress_callback and i % 5 == 0:  # 每5个片段更新一次，避免过于频繁
                        current_progress = f"🎬 进度: {i+1}/{len(keyword_data)} | 成功: {len(successfully_processed_segments)}"
                        current_progress += f" | 单词: {item['keyword']}"
                        progress_callback(current_progress)
                    
                except Exception as e:
                    LOG.error(f"处理片段 {i} 时发生异常: {str(e)}")
                    import traceback
                    LOG.error(traceback.format_exc())
                    failed_segments.append(i)
                    continue
            
            # 报告处理结果
            LOG.info(f"成功处理 {len(successfully_processed_segments)}/{len(keyword_data)} 个关键词片段")
            if failed_segments:
                LOG.warning(f"失败片段索引: {failed_segments}")
            
            # 向前端发送处理结果统计
            if progress_callback:
                success_rate = len(successfully_processed_segments) / len(keyword_data) * 100 if keyword_data else 0
                progress_callback(f"📊 成功处理 {len(successfully_processed_segments)}/{len(keyword_data)} 个片段 ({success_rate:.1f}%)")
                if failed_segments:
                    progress_callback(f"⚠️ {len(failed_segments)} 个片段处理失败")
            
            # 只处理成功的片段
            if not successfully_processed_segments:
                if progress_callback:
                    progress_callback("❌ 没有成功处理的片段，无法生成视频")
                return None
            
            # 创建包含所有处理过的片段的文件列表
            segments_list_path = os.path.join(self.temp_dir, "segments.txt")
            LOG.info(f"创建片段列表文件: {segments_list_path}")
            
            with open(segments_list_path, 'w') as f:
                for i in successfully_processed_segments:
                    segment_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    # 再次验证文件存在
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        # 使用绝对路径，确保ffmpeg能找到文件
                        abs_segment_path = os.path.abspath(segment_path)
                        # 需要特殊处理路径中的单引号，替换为\'
                        escaped_path = abs_segment_path.replace("'", "\\'")
                        f.write(f"file '{escaped_path}'\n")
                        LOG.info(f"添加片段到列表: {abs_segment_path}")
                    else:
                        LOG.warning(f"跳过无效片段文件: {segment_path}")
            
            if progress_callback:
                progress_callback("🔄 合并所有视频片段...")
                
            # 使用concat过滤器合并所有片段
            concat_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', segments_list_path,
                '-c', 'copy',
                output_video
            ]
            
            # 执行合并命令
            proc = subprocess.Popen(
                concat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = proc.communicate()
            
            # 检查输出文件
            if proc.returncode == 0 and os.path.exists(output_video) and os.path.getsize(output_video) > 0:
                if progress_callback:
                    # 添加关键词统计信息
                    progress_callback("📈 关键词统计:")
                    progress_callback(f"  - 总计: {len(keyword_data)} 个单词")
                    progress_callback("✅ 关键词烧制视频完成！")
                
                # 更新数据库中的烧制视频信息 - 更新为第二遍
                db_manager.update_series_video_info(
                    series_id,
                    second_name=os.path.basename(output_video),
                    second_file_path=output_video
                )
                
                LOG.info(f"✅ 关键词烧制成功: {output_video}, 大小: {os.path.getsize(output_video)/1024/1024:.2f}MB")
                return output_video
            else:
                # 合并失败，尝试替代方案
                if progress_callback:
                    progress_callback("⚠️ 标准合并失败，尝试替代方案...")
                
                LOG.warning(f"标准合并失败，尝试使用过滤器链方式合并")
                
                # 构建过滤器复杂链
                filter_complex = []
                for idx, i in enumerate(successfully_processed_segments):
                    segment_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    # 确保文件存在
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        filter_complex.append(f"[{idx}:v][{idx}:a]")
                
                if not filter_complex:
                    error_msg = "所有片段都无效，无法生成视频"
                    if progress_callback:
                        progress_callback(f"❌ {error_msg}")
                    LOG.error(error_msg)
                    return None
                
                # 构建备用命令
                inputs = []
                for i in successfully_processed_segments:
                    segment_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        inputs.extend(['-i', segment_path])
                
                # 如果只有一个片段，直接复制
                if len(successfully_processed_segments) == 1:
                    segment_path = os.path.join(self.temp_dir, f"segment_{successfully_processed_segments[0]}.mp4")
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                        fallback_cmd = [
                            'ffmpeg', '-y',
                            '-i', segment_path,
                            '-c', 'copy',
                            output_video
                        ]
                else:
                    # 构建备用命令
                    filter_str = ''.join(filter_complex) + f"concat=n={len(filter_complex)}:v=1:a=1[outv][outa]"
                    fallback_cmd = [
                        'ffmpeg', '-y'
                    ] + inputs + [
                        '-filter_complex', filter_str,
                        '-map', '[outv]',
                        '-map', '[outa]',
                        '-preset', 'medium',
                        '-crf', '23',
                        output_video
                    ]
                
                LOG.info(f"执行备用合并命令: {' '.join(fallback_cmd)}")
                
                if progress_callback:
                    progress_callback("🔄 尝试备用合并方法...")
                
                # 执行备用命令
                proc = subprocess.Popen(
                    fallback_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                stdout, stderr = proc.communicate()
                
                if proc.returncode == 0 and os.path.exists(output_video) and os.path.getsize(output_video) > 0:
                    if progress_callback:
                        progress_callback("✅ 备用方法视频烧制完成！")
                    
                    # 更新数据库中的烧制视频信息 - 更新为第二遍
                    db_manager.update_series_video_info(
                        series_id,
                        second_name=os.path.basename(output_video),
                        second_file_path=output_video
                    )
                    
                    LOG.info(f"✅ 备用方法关键词烧制成功: {output_video}")
                    return output_video
                else:
                    error_msg = f"备用合并方法也失败: {stderr}"
                    if progress_callback:
                        progress_callback(f"❌ 烧制失败: {error_msg}")
                    LOG.error(error_msg)
                    return None
                
        except Exception as e:
            error_msg = f"关键词视频烧制失败: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}")
            LOG.error(error_msg)
            return None
        finally:
            # 清理临时文件
            try:
                # 清理临时视频文件
                for i in range(len(keyword_data)):
                    temp_files = [
                        os.path.join(self.temp_dir, f"temp_segment_{i}.mp4"),
                        os.path.join(self.temp_dir, f"segment_{i}.mp4")
                    ]
                    for temp_file in temp_files:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            LOG.debug(f"已删除临时文件: {temp_file}")
                
                # 删除临时片段列表文件
                segments_list_path = os.path.join(self.temp_dir, "segments.txt")
                if os.path.exists(segments_list_path):
                    os.remove(segments_list_path)
                    LOG.debug("已删除临时片段列表文件")
                
                LOG.info("🧹 临时文件清理完成")
            except Exception as e:
                LOG.warning(f"清理临时文件失败: {e}")
    
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
            
            # 获取所有关键词，包括未选中的
            all_keywords = db_manager.get_keywords(series_id=series_id)
            total_keywords = len(all_keywords)
            
            # 计算选中的关键词数量
            selected_keywords = [kw for kw in all_keywords if kw.get('is_selected', 0) == 1]
            selected_count = len(selected_keywords)
            
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
                'title': "",
                'total_available_keywords': total_keywords,
                'selected_keywords': selected_count
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
                'title': "",
                'total_available_keywords': 0,
                'selected_keywords': 0
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
    
    def process_no_subtitle_video(self, 
                                 series_id: int, 
                                 output_dir: str = "input",
                                 title_text: str = "",
                                 progress_callback=None) -> Optional[str]:
        """
        处理无字幕视频，只添加顶部标题
        
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
                progress_callback("🔍 开始处理无字幕视频...")
            
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
            
            # 准备输出路径
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取原始文件名中的基础部分（例如从9_0.mp4中提取9）
            input_basename = os.path.basename(input_video)
            if "_" in input_basename:
                base_name = input_basename.split("_")[0]  # 获取下划线前的部分（例如9）
            else:
                # 如果没有下划线，直接使用文件名（不含扩展名）
                base_name = os.path.splitext(input_basename)[0]
            
            # 生成新的文件名：基础名称_1.mp4
            output_video = os.path.join(output_dir, f"{base_name}_1.mp4")
            
            if progress_callback:
                progress_callback(f"📋 输入视频: {input_basename}, 输出视频: {base_name}_1.mp4")
            
            # 应用视频滤镜
            video_filter = self._build_no_subtitle_filter(title_text)
            
            # 构建FFmpeg命令
            import subprocess
            
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-i', input_video,
                '-vf', video_filter,
                '-aspect', '9:16',  # 设置宽高比为9:16
                '-c:a', 'copy',  # 音频直接复制
                '-preset', 'medium',
                '-crf', '23',
                output_video
            ]
            
            if progress_callback:
                progress_callback("🔄 开始处理视频...")
            
            # 执行FFmpeg命令
            proc = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = proc.communicate()
            
            # 检查是否成功
            if proc.returncode == 0 and os.path.exists(output_video) and os.path.getsize(output_video) > 0:
                # 更新数据库中的烧制视频信息
                db_manager.update_series_video_info(
                    series_id,
                    first_name=os.path.basename(output_video),
                    first_file_path=output_video
                )
                
                if progress_callback:
                    progress_callback("✅ 无字幕视频处理完成！")
                
                LOG.info(f"✅ 无字幕视频处理成功: {output_video}, 大小: {os.path.getsize(output_video)/1024/1024:.2f}MB")
                return output_video
            else:
                if progress_callback:
                    progress_callback(f"❌ 处理失败: {stderr}")
                LOG.error(f"无字幕视频处理失败: {stderr}")
                return None
                
        except Exception as e:
            error_msg = f"处理无字幕视频失败: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}")
            LOG.error(error_msg)
            return None

# 全局实例
video_burner = VideoSubtitleBurner() 