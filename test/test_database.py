#!/usr/bin/env python3
"""
测试数据库功能
"""

import sys
import os
sys.path.append('src')

from database import db_manager

def test_database_functionality():
    """测试数据库基础功能"""
    print("=== 测试数据库功能 ===\n")
    
    # 1. 测试创建媒体系列
    print("🧪 测试创建媒体系列...")
    series_id = db_manager.create_series(
        name="test_audio.mp3",
        file_path="/path/to/test_audio.mp3",
        file_type="audio",
        duration=120.5
    )
    print(f"✅ 创建系列成功，ID: {series_id}")
    
    # 2. 测试创建字幕
    print("\n🧪 测试创建字幕...")
    subtitles_data = [
        {
            'begin_time': 0.0,
            'end_time': 3.5,
            'english_text': 'Hello everyone',
            'chinese_text': '大家好'
        },
        {
            'begin_time': 3.5,
            'end_time': 7.2,
            'english_text': 'Welcome to our channel',
            'chinese_text': '欢迎来到我们的频道'
        },
        {
            'begin_time': 7.2,
            'end_time': 12.0,
            'english_text': 'Today we will discuss artificial intelligence',
            'chinese_text': '今天我们将讨论人工智能'
        }
    ]
    
    subtitle_ids = db_manager.create_subtitles(series_id, subtitles_data)
    print(f"✅ 创建字幕成功，IDs: {subtitle_ids}")
    
    # 3. 测试创建关键词
    print("\n🧪 测试创建关键词...")
    keywords_data = [
        {
            'key_word': 'artificial',
            'phonetic_symbol': '/ˌɑːtɪˈfɪʃəl/',
            'explain_text': '人工的，人造的'
        },
        {
            'key_word': 'intelligence',
            'phonetic_symbol': '/ɪnˈtelɪdʒəns/',
            'explain_text': '智力，智能'
        }
    ]
    
    # 为第一个字幕添加关键词
    if subtitle_ids:
        keyword_ids = db_manager.create_keywords(subtitle_ids[2], keywords_data)  # 第三个字幕包含AI相关内容
        print(f"✅ 创建关键词成功，IDs: {keyword_ids}")
    
    # 4. 测试查询功能
    print("\n🧪 测试查询功能...")
    
    # 查询所有系列
    all_series = db_manager.get_series()
    print(f"📊 所有系列数量: {len(all_series)}")
    for series in all_series[-3:]:  # 显示最近3个
        print(f"  - {series['id']}: {series['name']} ({series.get('file_type', 'unknown')})")
    
    # 查询指定系列的字幕
    series_subtitles = db_manager.get_subtitles(series_id)
    print(f"\n📝 系列 {series_id} 的字幕数量: {len(series_subtitles)}")
    for subtitle in series_subtitles:
        print(f"  - [{subtitle['begin_time']:.1f}s-{subtitle['end_time']:.1f}s] {subtitle['english_text'][:50]}...")
    
    # 查询关键词
    series_keywords = db_manager.get_keywords(series_id=series_id)
    print(f"\n📚 系列 {series_id} 的关键词数量: {len(series_keywords)}")
    for keyword in series_keywords:
        print(f"  - {keyword['key_word']} {keyword.get('phonetic_symbol', '')} - {keyword.get('explain_text', '')}")
    
    # 5. 测试搜索功能
    print("\n🧪 测试搜索功能...")
    search_results = db_manager.search_keywords("intelligence")
    print(f"🔍 搜索 'intelligence' 结果数量: {len(search_results)}")
    for result in search_results:
        print(f"  - {result['key_word']} in '{result.get('series_name', 'unknown')}' [{result.get('begin_time', 0):.1f}s-{result.get('end_time', 0):.1f}s]")
    
    # 6. 测试统计信息
    print("\n🧪 测试统计信息...")
    stats = db_manager.get_statistics()
    print("📈 数据库统计:")
    print(f"  - 媒体系列: {stats['series_count']}")
    print(f"  - 字幕条目: {stats['subtitle_count']}")
    print(f"  - 关键词数: {stats['keyword_count']}")
    print(f"  - 独特单词: {stats['unique_words']}")
    print(f"  - 总时长: {stats['total_duration']:.1f} 秒")
    
    print("\n✅ 数据库功能测试完成！")
    print("💡 数据库已准备就绪，可以存储和管理媒体内容了！")
    
    return True

if __name__ == "__main__":
    test_database_functionality() 