#!/usr/bin/env python3
"""
关键词提取模块
使用OpenAI API分析字幕文本，提取适合大学生英语水平的重点词汇
"""

import re
import json
from typing import List, Dict, Tuple
from openai import OpenAI
from logger import LOG

class KeywordExtractor:
    """关键词提取器"""
    
    def __init__(self):
        """初始化提取器"""
        # 使用和翻译模块相同的配置
        from openai_translate import client
        self.client = client
        
        # 提示词模板
        self.prompt_template = """我是一名大学生，英语水平在六级左右。请分析以下英文文本，提取出对我这个水平来说比较重要的词汇。

请按照以下格式返回，每个词汇一行：
词汇 /音标/ 中文解释

例如：
come up with /kʌm ʌp wɪð/ 想出，提出
artificial /ˌɑːtɪˈfɪʃəl/ adj. 人工的，人造的

要求： 
1. 只提取考研、雅思、托福、GRE范围内的单词
2. 不要提取简单的词汇
3. 包括短语和搭配
4. 音标使用国际音标标准
5. 中文解释简洁准确, 词性要标注

待分析文本：
{text}

请提取重点词汇："""
        
        LOG.info("🔧 关键词提取器初始化完成")
    
    def extract_keywords_from_text(self, text: str) -> List[Dict]:
        """
        从文本中提取关键词
        
        参数:
        - text: 英文文本
        
        返回:
        - List[Dict]: 关键词列表，每个包含 word, phonetic, explanation
        """
        if not text.strip():
            return []
        
        try:
            LOG.info(f"🔍 正在分析文本: {text[:50]}...")
            
            # 构建提示词
            prompt = self.prompt_template.format(text=text.strip())
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一个专业的英语教师，专门帮助大学生学习英语词汇。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # 解析响应
            content = response.choices[0].message.content
            keywords = self._parse_keywords_response(content)
            
            LOG.info(f"✅ 提取到 {len(keywords)} 个关键词")
            return keywords
            
        except Exception as e:
            LOG.error(f"❌ 关键词提取失败: {e}")
            return []
    
    def _parse_keywords_response(self, response_text: str) -> List[Dict]:
        """
        解析AI响应，提取关键词信息
        
        参数:
        - response_text: AI返回的文本
        
        返回:
        - List[Dict]: 解析后的关键词列表
        """
        keywords = []
        
        # 按行分割
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 使用正则表达式匹配格式：词汇 /音标/ 解释
            pattern = r'^(.+?)\s+/([^/]+)/\s+(.+)$'
            match = re.match(pattern, line)
            
            if match:
                word = match.group(1).strip()
                phonetic = match.group(2).strip()
                explanation = match.group(3).strip()
                
                # 获取COCA词频排名
                from coca_lookup import coca_lookup
                coca_rank = coca_lookup.get_frequency_rank(word)
                
                keywords.append({
                    'key_word': word,
                    'phonetic_symbol': f"/{phonetic}/",
                    'explain_text': explanation,
                    'coca': coca_rank
                })
            else:
                # 尝试其他可能的格式
                if '/' in line and len(line.split()) >= 2:
                    parts = line.split()
                    word_part = parts[0]
                    remaining = ' '.join(parts[1:])
                    
                    # 查找音标
                    phonetic_match = re.search(r'/([^/]+)/', remaining)
                    if phonetic_match:
                        phonetic = phonetic_match.group(1)
                        explanation = remaining.replace(f"/{phonetic}/", "").strip()
                        
                        # 获取COCA词频排名
                        from coca_lookup import coca_lookup
                        coca_rank = coca_lookup.get_frequency_rank(word_part)
                        
                        keywords.append({
                            'key_word': word_part,
                            'phonetic_symbol': f"/{phonetic}/",
                            'explain_text': explanation,
                            'coca': coca_rank
                        })
        
        return keywords
    
    def extract_keywords_from_subtitles(self, subtitles: List[Dict]) -> List[Dict]:
        """
        从字幕列表中提取关键词
        
        参数:
        - subtitles: 字幕列表，每个包含 id, english_text 等
        
        返回:
        - List[Dict]: 关键词列表，每个包含 subtitle_id, key_word, phonetic_symbol, explain_text
        """
        all_keywords = []
        
        LOG.info(f"🎯 开始从 {len(subtitles)} 条字幕中提取关键词")
        
        for i, subtitle in enumerate(subtitles):
            subtitle_id = subtitle.get('id')
            english_text = subtitle.get('english_text', '').strip()
            
            if not english_text:
                continue
            
            LOG.info(f"📝 处理字幕 {i+1}/{len(subtitles)}: ID={subtitle_id}")
            
            # 提取当前字幕的关键词
            keywords = self.extract_keywords_from_text(english_text)
            
            # 添加字幕ID
            for keyword in keywords:
                keyword['subtitle_id'] = subtitle_id
                all_keywords.append(keyword)
        
        LOG.info(f"🎉 总计提取到 {len(all_keywords)} 个关键词")
        return all_keywords
    
    def batch_extract_with_context(self, subtitles: List[Dict], batch_size: int = 5) -> List[Dict]:
        """
        批量提取关键词（带上下文）
        
        参数:
        - subtitles: 字幕列表
        - batch_size: 批次大小
        
        返回:
        - List[Dict]: 关键词列表
        """
        all_keywords = []
        
        LOG.info(f"📦 批量提取模式: {len(subtitles)} 条字幕，批次大小={batch_size}")
        
        for i in range(0, len(subtitles), batch_size):
            batch = subtitles[i:i+batch_size]
            
            # 合并当前批次的文本
            combined_text = " ".join([sub.get('english_text', '') for sub in batch if sub.get('english_text')])
            
            if not combined_text.strip():
                continue
            
            LOG.info(f"📝 处理批次 {i//batch_size + 1}: {len(batch)} 条字幕")
            
            # 提取关键词
            keywords = self.extract_keywords_from_text(combined_text)
            
            # 为每个关键词找到最匹配的字幕ID
            for keyword in keywords:
                best_subtitle_id = self._find_best_matching_subtitle(
                    keyword['key_word'], batch
                )
                keyword['subtitle_id'] = best_subtitle_id
                all_keywords.append(keyword)
        
        LOG.info(f"🎉 批量提取完成: {len(all_keywords)} 个关键词")
        return all_keywords
    
    def _find_best_matching_subtitle(self, keyword: str, subtitles: List[Dict]) -> int:
        """
        为关键词找到最匹配的字幕
        
        参数:
        - keyword: 关键词
        - subtitles: 字幕列表
        
        返回:
        - int: 最匹配的字幕ID
        """
        keyword_lower = keyword.lower()
        
        # 查找包含关键词的字幕
        for subtitle in subtitles:
            text = subtitle.get('english_text', '').lower()
            if keyword_lower in text:
                return subtitle.get('id')
        
        # 如果没有找到，返回第一个字幕的ID
        return subtitles[0].get('id') if subtitles else None

# 全局提取器实例
keyword_extractor = KeywordExtractor() 