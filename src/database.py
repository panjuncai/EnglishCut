#!/usr/bin/env python3
"""
数据库管理模块
管理媒体文件、字幕和重点单词的数据库操作
"""

import sqlite3
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from logger import LOG

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/englishcut.db"):
        """初始化数据库连接"""
        self.db_path = db_path
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        LOG.info(f"📊 数据库初始化完成: {db_path}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建系列表（媒体文件元数据）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS t_series (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    file_path TEXT,
                    file_type TEXT,
                    duration REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建字幕表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS t_subtitle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    series_id INTEGER NOT NULL,
                    begin_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    english_text TEXT,
                    chinese_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (series_id) REFERENCES t_series (id) ON DELETE CASCADE
                )
            """)
            
            # 创建重点单词表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS t_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subtitle_id INTEGER NOT NULL,
                    key_word TEXT NOT NULL,
                    phonetic_symbol TEXT,
                    explain_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subtitle_id) REFERENCES t_subtitle (id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_series_id ON t_subtitle(series_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_time ON t_subtitle(begin_time, end_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_subtitle_id ON t_keywords(subtitle_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_word ON t_keywords(key_word)")
            
            conn.commit()
    
    def create_series(self, name: str, file_path: str = None, file_type: str = None, duration: float = None) -> int:
        """
        创建新的媒体系列
        
        参数:
        - name: 系列名称（通常是文件名）
        - file_path: 文件路径
        - file_type: 文件类型（audio/video）
        - duration: 时长（秒）
        
        返回:
        - series_id: 新创建的系列ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO t_series (name, file_path, file_type, duration)
                VALUES (?, ?, ?, ?)
            """, (name, file_path, file_type, duration))
            
            series_id = cursor.lastrowid
            conn.commit()
            
            LOG.info(f"📊 创建媒体系列: {name} (ID: {series_id})")
            return series_id
    
    def create_subtitles(self, series_id: int, subtitles: List[Dict]) -> List[int]:
        """
        批量创建字幕条目
        
        参数:
        - series_id: 系列ID
        - subtitles: 字幕列表，每个字幕包含 begin_time, end_time, english_text, chinese_text
        
        返回:
        - List[int]: 创建的字幕ID列表
        """
        subtitle_ids = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for subtitle in subtitles:
                cursor.execute("""
                    INSERT INTO t_subtitle (series_id, begin_time, end_time, english_text, chinese_text)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    series_id,
                    subtitle.get('begin_time'),
                    subtitle.get('end_time'),
                    subtitle.get('english_text', ''),
                    subtitle.get('chinese_text', '')
                ))
                
                subtitle_ids.append(cursor.lastrowid)
            
            conn.commit()
            
            LOG.info(f"📊 创建字幕条目: {len(subtitle_ids)} 条 (系列ID: {series_id})")
            return subtitle_ids
    
    def create_keywords(self, subtitle_id: int, keywords: List[Dict]) -> List[int]:
        """
        为指定字幕创建重点单词
        
        参数:
        - subtitle_id: 字幕ID
        - keywords: 单词列表，每个单词包含 key_word, phonetic_symbol, explain_text
        
        返回:
        - List[int]: 创建的单词ID列表
        """
        keyword_ids = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for keyword in keywords:
                cursor.execute("""
                    INSERT INTO t_keywords (subtitle_id, key_word, phonetic_symbol, explain_text)
                    VALUES (?, ?, ?, ?)
                """, (
                    subtitle_id,
                    keyword.get('key_word'),
                    keyword.get('phonetic_symbol', ''),
                    keyword.get('explain_text', '')
                ))
                
                keyword_ids.append(cursor.lastrowid)
            
            conn.commit()
            
            LOG.info(f"📊 创建重点单词: {len(keyword_ids)} 个 (字幕ID: {subtitle_id})")
            return keyword_ids
    
    def get_series(self, series_id: int = None) -> List[Dict]:
        """
        获取媒体系列信息
        
        参数:
        - series_id: 系列ID，如果为None则返回所有系列
        
        返回:
        - List[Dict]: 系列信息列表
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if series_id:
                cursor.execute("SELECT * FROM t_series WHERE id = ?", (series_id,))
                result = cursor.fetchone()
                return [dict(result)] if result else []
            else:
                cursor.execute("SELECT * FROM t_series ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
    
    def get_subtitles(self, series_id: int) -> List[Dict]:
        """
        获取指定系列的所有字幕
        
        参数:
        - series_id: 系列ID
        
        返回:
        - List[Dict]: 字幕列表
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM t_subtitle 
                WHERE series_id = ? 
                ORDER BY begin_time
            """, (series_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_keywords(self, subtitle_id: int = None, series_id: int = None) -> List[Dict]:
        """
        获取重点单词
        
        参数:
        - subtitle_id: 字幕ID（获取特定字幕的单词）
        - series_id: 系列ID（获取整个系列的单词）
        
        返回:
        - List[Dict]: 单词列表
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if subtitle_id:
                cursor.execute("""
                    SELECT * FROM t_keywords 
                    WHERE subtitle_id = ?
                    ORDER BY created_at
                """, (subtitle_id,))
            elif series_id:
                cursor.execute("""
                    SELECT k.*, s.begin_time, s.end_time 
                    FROM t_keywords k
                    JOIN t_subtitle s ON k.subtitle_id = s.id
                    WHERE s.series_id = ?
                    ORDER BY s.begin_time, k.created_at
                """, (series_id,))
            else:
                cursor.execute("SELECT * FROM t_keywords ORDER BY created_at DESC")
            
            return [dict(row) for row in cursor.fetchall()]
    
    def search_keywords(self, keyword: str) -> List[Dict]:
        """
        搜索单词（支持模糊匹配）
        
        参数:
        - keyword: 搜索关键词
        
        返回:
        - List[Dict]: 匹配的单词及其上下文信息
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    k.*,
                    s.begin_time,
                    s.end_time,
                    s.english_text,
                    s.chinese_text,
                    ser.name as series_name
                FROM t_keywords k
                JOIN t_subtitle s ON k.subtitle_id = s.id
                JOIN t_series ser ON s.series_id = ser.id
                WHERE k.key_word LIKE ?
                ORDER BY k.key_word, ser.name, s.begin_time
            """, (f"%{keyword}%",))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """
        获取数据库统计信息
        
        返回:
        - Dict: 统计信息
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 统计各表的记录数
            cursor.execute("SELECT COUNT(*) FROM t_series")
            series_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM t_subtitle")
            subtitle_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM t_keywords")
            keyword_count = cursor.fetchone()[0]
            
            # 统计独特单词数
            cursor.execute("SELECT COUNT(DISTINCT key_word) FROM t_keywords")
            unique_words = cursor.fetchone()[0]
            
            # 总时长
            cursor.execute("SELECT SUM(duration) FROM t_series WHERE duration IS NOT NULL")
            total_duration = cursor.fetchone()[0] or 0
            
            return {
                'series_count': series_count,
                'subtitle_count': subtitle_count,
                'keyword_count': keyword_count,
                'unique_words': unique_words,
                'total_duration': total_duration
            }
    
    def delete_series(self, series_id: int) -> bool:
        """
        删除系列（级联删除相关字幕和单词）
        
        参数:
        - series_id: 系列ID
        
        返回:
        - bool: 是否删除成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM t_series WHERE id = ?", (series_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    LOG.info(f"📊 删除系列: ID {series_id}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            LOG.error(f"删除系列失败: {e}")
            return False

# 全局数据库实例
db_manager = DatabaseManager() 