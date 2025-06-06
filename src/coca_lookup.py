#!/usr/bin/env python3
"""
基于数据库的COCA词频查询模块
从t_coca表查询词频排名
"""

import sqlite3
import re
from typing import Optional, Dict, List
from logger import LOG

class COCADatabaseLookup:
    """基于数据库的COCA词频查询类"""
    
    def __init__(self, db_path: str = "data/englishcut.db"):
        """初始化COCA查询器"""
        self.db_path = db_path
        LOG.info("🔤 COCA数据库查询器初始化完成")
    
    def get_frequency_rank(self, word: str) -> Optional[int]:
        """
        从t_coca表获取单词的频率排名
        
        参数:
        - word: 单词或短语
        
        返回:
        - int: 频率排名（数字越小频率越高），如果未找到返回None
        """
        if not word or not word.strip():
            return None
        
        # 标准化处理
        normalized_word = self._normalize_word(word.strip())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 精确匹配查询
                cursor.execute("SELECT rank FROM t_coca WHERE word = ? LIMIT 1", (normalized_word,))
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                
                # 如果没有找到，尝试不区分大小写查询
                cursor.execute("SELECT rank FROM t_coca WHERE LOWER(word) = LOWER(?) LIMIT 1", (normalized_word,))
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                
                # 如果是短语，尝试估算
                if ' ' in normalized_word:
                    return self._estimate_phrase_frequency(normalized_word)
                
                # 尝试词根匹配
                root_rank = self._find_root_word_frequency(normalized_word)
                if root_rank:
                    return root_rank + 500  # 变形词的排名通常低于原词
                
                # 未找到，返回None
                return None
                
        except Exception as e:
            LOG.error(f"COCA查询失败: {e}")
            return None
    
    def _normalize_word(self, word: str) -> str:
        """标准化单词"""
        # 转换为小写，移除标点符号，保留空格和连字符
        normalized = word.lower().strip()
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        return normalized
    
    def _estimate_phrase_frequency(self, phrase: str) -> Optional[int]:
        """估算短语频率（基于组成词的频率）"""
        words = phrase.split()
        if len(words) <= 1:
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                word_ranks = []
                for word in words:
                    cursor.execute("SELECT rank FROM t_coca WHERE LOWER(word) = LOWER(?) LIMIT 1", (word,))
                    result = cursor.fetchone()
                    if result:
                        word_ranks.append(result[0])
                    else:
                        # 如果某个词找不到，使用较高的默认排名
                        word_ranks.append(10000)
                
                if word_ranks:
                    # 短语作为重点背诵词汇，设置较大排名（低频度）
                    avg_rank = sum(word_ranks) // len(word_ranks)
                    # 确保短语排名在20000以上，标记为重点背诵词汇
                    return max(20000, avg_rank + 5000)  # 短语是重点背诵词汇
                
        except Exception as e:
            LOG.error(f"短语频率估算失败: {e}")
        
        return None
    
    def _find_root_word_frequency(self, word: str) -> Optional[int]:
        """查找词根的频率"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 常见词缀
                suffixes = ['s', 'es', 'ed', 'ing', 'er', 'est', 'ly', 'tion', 'sion', 'ness', 'ment']
                
                for suffix in suffixes:
                    if word.endswith(suffix) and len(word) > len(suffix) + 2:
                        root = word[:-len(suffix)]
                        cursor.execute("SELECT rank FROM t_coca WHERE LOWER(word) = LOWER(?) LIMIT 1", (root,))
                        result = cursor.fetchone()
                        if result:
                            return result[0]
                
                # 尝试去掉常见前缀
                prefixes = ['un', 're', 'pre', 'dis', 'mis', 'over', 'under', 'out']
                for prefix in prefixes:
                    if word.startswith(prefix) and len(word) > len(prefix) + 2:
                        root = word[len(prefix):]
                        cursor.execute("SELECT rank FROM t_coca WHERE LOWER(word) = LOWER(?) LIMIT 1", (root,))
                        result = cursor.fetchone()
                        if result:
                            return result[0]
                            
        except Exception as e:
            LOG.error(f"词根查找失败: {e}")
        
        return None
    
    def get_frequency_level(self, rank: int) -> str:
        """根据排名获取频率等级"""
        if rank <= 100:
            return "极高频"
        elif rank <= 500:
            return "高频"
        elif rank <= 1000:
            return "中高频"
        elif rank <= 2000:
            return "中频"
        elif rank <= 5000:
            return "中低频"
        elif rank <= 10000:
            return "低频"
        else:
            return "很低频"
    
    def batch_lookup(self, words: List[str]) -> Dict[str, Optional[int]]:
        """批量查询词频"""
        results = {}
        
        if not words:
            return results
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for word in words:
                    normalized_word = self._normalize_word(word)
                    cursor.execute("SELECT rank FROM t_coca WHERE LOWER(word) = LOWER(?) LIMIT 1", (normalized_word,))
                    result = cursor.fetchone()
                    results[word] = result[0] if result else None
                    
        except Exception as e:
            LOG.error(f"批量查询失败: {e}")
            # 如果批量查询失败，回退到单个查询
            for word in words:
                results[word] = self.get_frequency_rank(word)
        
        return results
    
    def get_word_details(self, word: str) -> Optional[Dict]:
        """
        获取单词的详细信息（包括不同语料库的频率）
        
        返回:
        - Dict: 包含rank, pos, total, spoken, fiction, magazine, newspaper, academic等信息
        """
        if not word or not word.strip():
            return None
        
        normalized_word = self._normalize_word(word.strip())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT rank, pos, word, total, spoken, fiction, magazine, newspaper, academic
                    FROM t_coca 
                    WHERE LOWER(word) = LOWER(?) 
                    LIMIT 1
                """, (normalized_word,))
                
                result = cursor.fetchone()
                if result:
                    return dict(result)
                    
        except Exception as e:
            LOG.error(f"获取单词详细信息失败: {e}")
        
        return None
    
    def get_database_stats(self) -> Dict:
        """获取COCA数据库统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM t_coca")
                total_words = cursor.fetchone()[0]
                
                cursor.execute("SELECT MIN(rank), MAX(rank) FROM t_coca")
                rank_range = cursor.fetchone()
                
                return {
                    'total_words': total_words,
                    'min_rank': rank_range[0] if rank_range[0] else 0,
                    'max_rank': rank_range[1] if rank_range[1] else 0
                }
                
        except Exception as e:
            LOG.error(f"获取数据库统计失败: {e}")
            return {'total_words': 0, 'min_rank': 0, 'max_rank': 0}

# 全局实例
coca_lookup = COCADatabaseLookup() 