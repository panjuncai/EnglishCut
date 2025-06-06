#!/usr/bin/env python3
"""
字幕智能切分器
将长句子切分成适合手机屏幕显示的短句，特别针对抖音等短视频平台优化
"""

import re
from typing import List, Dict, Tuple
from logger import LOG

class SubtitleSplitter:
    """字幕智能切分器 - 基于语义单元的精准切分"""
    
    def __init__(self):
        """初始化切分器"""
        
        # 英文连词和分割标记 - 按优先级排序
        self.english_connectors = [
            'and', 'but', 'or', 'so', 'yet', 'for', 'nor',  # 并列连词
            'because', 'since', 'although', 'while', 'when', 'where', 'if',  # 从属连词
            'however', 'therefore', 'moreover', 'furthermore', 'nevertheless'  # 副词连词
        ]
        
        # 英文标点分割符
        self.english_punctuation = [',', ';', ':', '-', '–', '—', '(', ')', '[', ']']
        
        # 句子结束符
        self.sentence_endings = ['.', '!', '?']
        
        # 中文标点符号对应
        self.chinese_punctuation_map = {
            ',': '，',
            ';': '；', 
            ':': '：',
            '.': '。',
            '!': '！',
            '?': '？',
            '(': '（',
            ')': '）',
            '[': '【',
            ']': '】'
        }
        
        # 中文连接词
        self.chinese_connectors = [
            '和', '而且', '但是', '或者', '所以', '因为', '虽然', '当', '如果', '然后', '接着', '于是'
        ]
        
        LOG.info("🔧 语义单元字幕切分器初始化完成")
    
    def split_english_text(self, text: str, start_time: float, end_time: float) -> List[Dict]:
        """
        基于语义单元切分英文文本
        
        参数:
        - text: 原始英文文本
        - start_time: 开始时间（秒）
        - end_time: 结束时间（秒）
        
        返回:
        - List[Dict]: 切分后的字幕段落列表
        """
        if not text.strip():
            return []
        
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 基于语义单元切分
        segments = self._split_by_semantic_units(text)
        
        # 计算时间分配
        return self._assign_timestamps(segments, start_time, end_time)
    
    def split_chinese_text(self, text: str, start_time: float, end_time: float) -> List[Dict]:
        """
        切分中文文本
        
        参数:
        - text: 原始中文文本
        - start_time: 开始时间（秒）
        - end_time: 结束时间（秒）
        
        返回:
        - List[Dict]: 切分后的字幕段落列表
        """
        if not text.strip():
            return []
        
        # 去除多余空格
        text = re.sub(r'\s+', '', text.strip())
        
        # 按句子分割
        sentences = self._split_chinese_by_sentences(text)
        
        # 按长度进一步切分
        segments = []
        for sentence in sentences:
            if len(sentence) <= self.max_chars_per_line:
                segments.append(sentence)
            else:
                # 需要进一步切分
                sub_segments = self._split_long_chinese_sentence(sentence)
                segments.extend(sub_segments)
        
        # 计算时间分配
        return self._assign_timestamps(segments, start_time, end_time)
    
    def split_bilingual_text(self, english_text: str, chinese_text: str, 
                           start_time: float, end_time: float) -> List[Dict]:
        """
        切分双语文本 - 保持语义单元对应
        
        参数:
        - english_text: 英文文本
        - chinese_text: 中文文本
        - start_time: 开始时间（秒）
        - end_time: 结束时间（秒）
        
        返回:
        - List[Dict]: 切分后的双语字幕段落列表
        """
        if not english_text.strip() and not chinese_text.strip():
            return []
        
        # 基于英文的语义单元切分，然后同步切分中文
        english_segments = self._split_by_semantic_units(english_text) if english_text else []
        chinese_segments = self._split_chinese_by_english_units(chinese_text, english_segments) if chinese_text else []
        
        # 对齐双语段落
        aligned_segments = self._align_bilingual_segments(english_segments, chinese_segments)
        
        # 计算时间分配
        return self._assign_timestamps_bilingual(aligned_segments, start_time, end_time)
    
    def _split_by_semantic_units(self, text: str) -> List[str]:
        """基于语义单元切分英文文本"""
        if not text.strip():
            return []
        
        segments = []
        
        # 首先按句子分割
        sentences = self._split_sentences(text)
        
        for sentence in sentences:
            # 对每个句子进行语义单元切分
            units = self._split_sentence_to_units(sentence)
            segments.extend(units)
        
        return [seg.strip() for seg in segments if seg.strip()]
    
    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割文本"""
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            if char in self.sentence_endings:
                sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # 处理最后一个句子
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return [s for s in sentences if s]
    
    def _split_sentence_to_units(self, sentence: str) -> List[str]:
        """将单个句子分割为语义单元"""
        if not sentence.strip():
            return []
        
        units = []
        words = sentence.split()
        current_unit = []
        
        i = 0
        while i < len(words):
            word = words[i]
            
            # 检查是否是连词（需要开始新单元）
            if word.lower() in self.english_connectors and current_unit:
                # 保存当前单元
                units.append(' '.join(current_unit))
                current_unit = [word]
            else:
                current_unit.append(word)
            
            # 检查标点符号
            if any(punct in word for punct in self.english_punctuation):
                if current_unit:
                    units.append(' '.join(current_unit))
                    current_unit = []
            
            i += 1
        
        # 添加最后一个单元
        if current_unit:
            units.append(' '.join(current_unit))
        
        return units
    
    def _split_chinese_by_english_units(self, chinese_text: str, english_segments: List[str]) -> List[str]:
        """根据英文语义单元同步切分中文文本"""
        if not chinese_text.strip() or not english_segments:
            return []
        
        # 简单策略：按英文段落数量等比例分割中文
        # 这里可以后续优化为基于翻译对应关系的精确切分
        
        chinese_text = chinese_text.strip()
        num_segments = len(english_segments)
        
        if num_segments == 1:
            return [chinese_text]
        
        # 寻找中文的自然分割点
        chinese_segments = []
        
        # 按标点符号切分中文
        segments = self._split_chinese_by_punctuation(chinese_text)
        
        if len(segments) >= num_segments:
            # 如果中文段落比英文多，合并一些段落
            step = len(segments) / num_segments
            chinese_segments = []
            for i in range(num_segments):
                start_idx = int(i * step)
                end_idx = int((i + 1) * step) if i < num_segments - 1 else len(segments)
                combined = ''.join(segments[start_idx:end_idx])
                if combined:
                    chinese_segments.append(combined)
        else:
            # 如果中文段落比英文少，尝试智能分割
            chinese_segments = _smart_split_chinese(chinese_text, num_segments)
        
        # 确保返回正确数量的段落
        while len(chinese_segments) < num_segments:
            chinese_segments.append("")
        
        return chinese_segments[:num_segments]
    
    def _split_chinese_by_punctuation(self, text: str) -> List[str]:
        """按标点符号分割中文文本"""
        if not text:
            return []
        
        chinese_punctuation = ['，', '。', '！', '？', '；', '：', '、']
        segments = []
        current_segment = ""
        
        for char in text:
            current_segment += char
            if char in chinese_punctuation:
                if current_segment.strip():
                    segments.append(current_segment.strip())
                current_segment = ""
        
        # 添加最后一段
        if current_segment.strip():
            segments.append(current_segment.strip())
        
        return segments
    
    def _split_long_sentence(self, sentence: str) -> List[str]:
        """切分过长的英文句子"""
        words = sentence.split()
        segments = []
        current_segment = []
        
        for word in words:
            # 检查添加当前单词后是否超长
            test_segment = current_segment + [word]
            test_text = ' '.join(test_segment)
            
            if (len(test_segment) <= self.max_words_per_line and 
                len(test_text) <= self.max_chars_per_line):
                current_segment.append(word)
            else:
                # 保存当前段落，开始新段落
                if current_segment:
                    segments.append(' '.join(current_segment))
                current_segment = [word]
        
        # 添加最后一个段落
        if current_segment:
            segments.append(' '.join(current_segment))
        
        return segments
    
    def _split_long_chinese_sentence(self, sentence: str) -> List[str]:
        """切分过长的中文句子"""
        segments = []
        current_segment = ""
        
        # 首先尝试按标点符号分割
        parts = []
        current_part = ""
        
        for char in sentence:
            current_part += char
            if char in self.chinese_phrase_breaks:
                parts.append(current_part)
                current_part = ""
        
        if current_part:
            parts.append(current_part)
        
        # 如果没有标点符号，直接按字符数切分
        if not parts or len(parts) == 1:
            for i in range(0, len(sentence), self.max_chars_per_line):
                segment = sentence[i:i + self.max_chars_per_line]
                if segment:
                    segments.append(segment)
        else:
            # 按标点符号切分的结果进行组合
            for part in parts:
                if len(current_segment + part) <= self.max_chars_per_line:
                    current_segment += part
                else:
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = part
            
            if current_segment:
                segments.append(current_segment)
        
        return segments
    
    def _split_text_only(self, text: str) -> List[str]:
        """只切分文本，不分配时间"""
        if not text.strip():
            return []
        
        text = re.sub(r'\s+', ' ', text.strip())
        sentences = self._split_by_sentences(text)
        
        segments = []
        for sentence in sentences:
            if len(sentence.split()) <= self.max_words_per_line and len(sentence) <= self.max_chars_per_line:
                segments.append(sentence)
            else:
                sub_segments = self._split_long_sentence(sentence)
                segments.extend(sub_segments)
        
        return segments
    
    def _split_chinese_text_only(self, text: str) -> List[str]:
        """只切分中文文本，不分配时间"""
        if not text.strip():
            return []
        
        text = re.sub(r'\s+', '', text.strip())
        sentences = self._split_chinese_by_sentences(text)
        
        segments = []
        for sentence in sentences:
            if len(sentence) <= self.max_chars_per_line:
                segments.append(sentence)
            else:
                sub_segments = self._split_long_chinese_sentence(sentence)
                segments.extend(sub_segments)
        
        return segments
    
    def _align_bilingual_segments(self, english_segments: List[str], chinese_segments: List[str]) -> List[Dict]:
        """对齐双语段落"""
        aligned = []
        max_len = max(len(english_segments), len(chinese_segments))
        
        for i in range(max_len):
            english = english_segments[i] if i < len(english_segments) else ""
            chinese = chinese_segments[i] if i < len(chinese_segments) else ""
            
            if english or chinese:
                aligned.append({
                    "english": english,
                    "chinese": chinese
                })
        
        return aligned
    
    def _assign_timestamps(self, segments: List[str], start_time: float, end_time: float) -> List[Dict]:
        """为单语段落分配时间戳"""
        if not segments:
            return []
        
        total_chars = sum(len(seg) for seg in segments)
        duration = end_time - start_time
        
        result = []
        current_time = start_time
        
        for i, segment in enumerate(segments):
            # 按字符数比例分配时间
            segment_ratio = len(segment) / total_chars if total_chars > 0 else 1 / len(segments)
            segment_duration = duration * segment_ratio
            
            # 确保最后一个段落结束时间正确
            if i == len(segments) - 1:
                segment_end_time = end_time
            else:
                segment_end_time = current_time + segment_duration
            
            result.append({
                "text": segment,
                "timestamp": [current_time, segment_end_time]
            })
            
            current_time = segment_end_time
        
        return result
    
    def _assign_timestamps_bilingual(self, segments: List[Dict], start_time: float, end_time: float) -> List[Dict]:
        """为双语段落分配时间戳"""
        if not segments:
            return []
        
        # 计算总权重（优先考虑英文字符数）
        total_weight = 0
        for seg in segments:
            english_chars = len(seg.get("english", ""))
            chinese_chars = len(seg.get("chinese", ""))
            weight = max(english_chars, chinese_chars)  # 取较长的文本作为权重
            total_weight += weight
        
        duration = end_time - start_time
        result = []
        current_time = start_time
        
        for i, segment in enumerate(segments):
            english_chars = len(segment.get("english", ""))
            chinese_chars = len(segment.get("chinese", ""))
            segment_weight = max(english_chars, chinese_chars)
            
            # 按权重分配时间
            segment_ratio = segment_weight / total_weight if total_weight > 0 else 1 / len(segments)
            segment_duration = duration * segment_ratio
            
            # 确保最后一个段落结束时间正确
            if i == len(segments) - 1:
                segment_end_time = end_time
            else:
                segment_end_time = current_time + segment_duration
            
            result.append({
                "english": segment.get("english", ""),
                "chinese": segment.get("chinese", ""),
                "timestamp": [current_time, segment_end_time]
            })
            
            current_time = segment_end_time
        
        return result

def split_subtitle_chunks(chunks: List[Dict], is_bilingual: bool = False, **kwargs) -> List[Dict]:
    """
    基于语义单元智能切分字幕块，让中英文精确对应
    
    参数:
    - chunks: 原始字幕块列表
    - is_bilingual: 是否为双语字幕
    
    返回:
    - List[Dict]: 切分后的字幕块列表
    """
    if not chunks:
        return []
    
    splitter = SubtitleSplitter()
    result_chunks = []
    
    LOG.info(f"🔧 开始语义单元切分: {len(chunks)} 个原始片段, 双语模式: {is_bilingual}")
    
    for chunk in chunks:
        timestamp = chunk.get("timestamp", [None, None])
        if timestamp[0] is None or timestamp[1] is None:
            continue
        
        start_time, end_time = timestamp
        
        if is_bilingual:
            # 双语模式
            english_text = chunk.get("english", "")
            chinese_text = chunk.get("chinese", "")
            
            if english_text or chinese_text:
                split_segments = splitter.split_bilingual_text(
                    english_text, chinese_text, start_time, end_time
                )
                
                for segment in split_segments:
                    result_chunks.append({
                        "english": segment["english"],
                        "chinese": segment["chinese"],
                        "timestamp": segment["timestamp"]
                    })
        
        else:
            # 单语模式
            text = chunk.get("text", "")
            
            if text:
                split_segments = splitter.split_english_text(text, start_time, end_time)
                
                for segment in split_segments:
                    result_chunks.append({
                        "text": segment["text"],
                        "timestamp": segment["timestamp"]
                    })
    
    LOG.info(f"✅ 语义单元切分完成: {len(result_chunks)} 个新片段")
    return result_chunks

# 在文件末尾添加智能中文切分方法
def _smart_split_chinese(chinese_text: str, num_segments: int) -> List[str]:
    """智能分割中文文本为指定数量的段落"""
    if not chinese_text or num_segments <= 0:
        return []
    
    if num_segments == 1:
        return [chinese_text]
    
    # 首先尝试找到自然的分割点（标点符号）
    chinese_punctuation = ['，', '。', '！', '？', '；', '：', '、']
    potential_splits = []
    
    for i, char in enumerate(chinese_text):
        if char in chinese_punctuation:
            potential_splits.append(i + 1)  # +1 包含标点符号
    
    if len(potential_splits) >= num_segments - 1:
        # 选择最均匀分布的分割点
        step = len(potential_splits) / (num_segments - 1)
        selected_splits = []
        for i in range(num_segments - 1):
            idx = int(i * step)
            if idx < len(potential_splits):
                selected_splits.append(potential_splits[idx])
        
        # 根据选择的分割点分割文本
        segments = []
        start = 0
        for split_pos in selected_splits:
            segments.append(chinese_text[start:split_pos])
            start = split_pos
        segments.append(chinese_text[start:])  # 最后一段
        
        return [seg for seg in segments if seg]
    
    else:
        # 没有足够的标点符号，按字符数平均分割
        char_per_segment = len(chinese_text) // num_segments
        segments = []
        for i in range(num_segments):
            start = i * char_per_segment
            if i == num_segments - 1:
                end = len(chinese_text)
            else:
                end = (i + 1) * char_per_segment
            segment = chinese_text[start:end]
            if segment:
                segments.append(segment)
        
        return segments 