#!/usr/bin/env python3
"""
测试字幕删除和重新保存功能
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.append('.')

from src.database import db_manager
from src.logger import LOG

def test_subtitle_replace():
    """测试字幕删除和重新保存功能"""
    print("\n=== 测试字幕删除和重新保存功能 ===\n")
    
    # 1. 创建测试系列
    series_id = db_manager.create_series(
        name=f"测试系列-{int(time.time())}",
        file_path="/tmp/test.mp4",
        file_type="video",
        duration=120
    )
    print(f"创建测试系列: ID={series_id}")
    
    # 2. 第一次添加字幕
    subtitles1 = [
        {
            'begin_time': 0,
            'end_time': 5,
            'english_text': "Test subtitle 1",
            'chinese_text': "测试字幕1"
        },
        {
            'begin_time': 5,
            'end_time': 10,
            'english_text': "Test subtitle 2",
            'chinese_text': "测试字幕2"
        }
    ]
    
    subtitle_ids1 = db_manager.create_subtitles(series_id, subtitles1)
    print(f"第一次添加字幕: {len(subtitle_ids1)}条字幕")
    
    # 查询字幕
    subtitles_in_db = db_manager.get_subtitles(series_id)
    print(f"数据库中字幕数量: {len(subtitles_in_db)}")
    for sub in subtitles_in_db:
        print(f" - {sub['begin_time']}-{sub['end_time']}: {sub['english_text']} / {sub['chinese_text']}")
    
    # 3. 删除字幕
    db_manager.delete_subtitles_by_series_id(series_id)
    
    # 查询字幕
    subtitles_in_db = db_manager.get_subtitles(series_id)
    print(f"删除后数据库中字幕数量: {len(subtitles_in_db)}")
    
    # 4. 第二次添加字幕
    subtitles2 = [
        {
            'begin_time': 0,
            'end_time': 6,
            'english_text': "New subtitle 1",
            'chinese_text': "新字幕1"
        },
        {
            'begin_time': 6,
            'end_time': 12,
            'english_text': "New subtitle 2",
            'chinese_text': "新字幕2"
        },
        {
            'begin_time': 12,
            'end_time': 18,
            'english_text': "New subtitle 3",
            'chinese_text': "新字幕3"
        }
    ]
    
    subtitle_ids2 = db_manager.create_subtitles(series_id, subtitles2)
    print(f"第二次添加字幕: {len(subtitle_ids2)}条字幕")
    
    # 查询字幕
    subtitles_in_db = db_manager.get_subtitles(series_id)
    print(f"第二次添加后数据库中字幕数量: {len(subtitles_in_db)}")
    for sub in subtitles_in_db:
        print(f" - {sub['begin_time']}-{sub['end_time']}: {sub['english_text']} / {sub['chinese_text']}")
    
    # 5. 清理测试数据
    db_manager.delete_series(series_id)
    print(f"清理测试数据: 删除系列ID={series_id}")
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    test_subtitle_replace() 