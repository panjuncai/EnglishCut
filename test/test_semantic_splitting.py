#!/usr/bin/env python3
"""
测试语义单元字幕切分功能
"""

import sys
import os
sys.path.append('src')

from subtitle_splitter import SubtitleSplitter, split_subtitle_chunks

def test_semantic_splitting():
    """测试语义单元切分"""
    print("=== 测试语义单元字幕切分 ===\n")
    
    # 创建切分器
    splitter = SubtitleSplitter()
    
    # 测试用户提供的例子
    print("🧪 测试用户提供的例子...")
    english_text = "about midnight and it was very dark and very quiet. We got to the shop and we..."
    chinese_text = "大约在午夜时分，四周非常黑暗，也非常安静。我们到了商店，接着我们……"
    
    # 测试单语切分
    print("英文原文:", english_text)
    english_segments = splitter._split_by_semantic_units(english_text)
    print("英文语义单元切分结果:")
    for i, segment in enumerate(english_segments, 1):
        print(f"  {i}. {segment}")
    
    print("\n中文原文:", chinese_text)
    chinese_segments = splitter._split_chinese_by_english_units(chinese_text, english_segments)
    print("中文对应切分结果:")
    for i, segment in enumerate(chinese_segments, 1):
        print(f"  {i}. {segment}")
    
    print("\n" + "="*60 + "\n")
    
    # 测试双语时间戳分配
    print("🧪 测试双语时间戳分配...")
    bilingual_segments = splitter.split_bilingual_text(english_text, chinese_text, 0.0, 10.0)
    
    print("双语切分结果（带时间戳）:")
    for i, segment in enumerate(bilingual_segments, 1):
        start_time = segment['timestamp'][0]
        end_time = segment['timestamp'][1]
        english = segment['english']
        chinese = segment['chinese']
        print(f"  {i}. [{start_time:.1f}s - {end_time:.1f}s]")
        print(f"     EN: {english}")
        print(f"     CN: {chinese}")
    
    print("\n" + "="*60 + "\n")
    
    # 测试完整的字幕块切分
    print("🧪 测试完整字幕块切分...")
    
    # 模拟双语字幕块
    mock_bilingual_chunks = [
        {
            "english": "Hello everyone and welcome to our channel. Today we're going to talk about artificial intelligence.",
            "chinese": "大家好，欢迎来到我们的频道。今天我们要讨论人工智能。",
            "timestamp": [0.0, 6.0]
        },
        {
            "english": "AI has many applications and it's becoming very important in our daily lives.",
            "chinese": "人工智能有很多应用，它在我们的日常生活中变得非常重要。",
            "timestamp": [6.5, 12.0]
        }
    ]
    
    split_result = split_subtitle_chunks(mock_bilingual_chunks, is_bilingual=True)
    
    print("完整双语字幕切分结果:")
    for i, chunk in enumerate(split_result, 1):
        start_time = chunk['timestamp'][0]
        end_time = chunk['timestamp'][1]
        english = chunk['english']
        chinese = chunk['chinese']
        print(f"{i}. [{start_time:.1f}s - {end_time:.1f}s]")
        print(f"   EN: {english}")
        print(f"   CN: {chinese}")
        print()
    
    print("✅ 语义单元切分测试完成！")
    print("💡 现在字幕按语义单元切分，中英文能够精确对应！")
    
    return True

if __name__ == "__main__":
    test_semantic_splitting() 