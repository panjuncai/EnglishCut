#!/usr/bin/env python3
"""
测试短字幕切分功能
"""

import sys
import os
sys.path.append('src')

from subtitle_splitter import SubtitleSplitter, split_subtitle_chunks
from logger import LOG

def test_subtitle_splitter():
    """测试字幕切分器"""
    print("=== 测试短字幕切分功能 ===\n")
    
    # 创建切分器（抖音优化参数）
    splitter = SubtitleSplitter(max_chars_per_line=18, max_words_per_line=6)
    
    # 测试英文长句子
    print("🧪 测试英文长句子切分...")
    long_english = "Hello everyone, how are you doing today? The weather is absolutely beautiful and I hope you're having a wonderful time."
    
    english_segments = splitter.split_english_text(long_english, 0.0, 10.0)
    
    print(f"原始文本: {long_english}")
    print(f"切分结果 ({len(english_segments)} 段):")
    for i, segment in enumerate(english_segments, 1):
        start_time = segment['timestamp'][0]
        end_time = segment['timestamp'][1]
        text = segment['text']
        print(f"  {i}. [{start_time:.1f}s - {end_time:.1f}s] {text} ({len(text)} 字符, {len(text.split())} 单词)")
    
    print("\n" + "="*60 + "\n")
    
    # 测试中文长句子
    print("🧪 测试中文长句子切分...")
    long_chinese = "大家好，今天天气非常好，希望大家都能有一个愉快的一天，我们一起来学习新的知识吧。"
    
    chinese_segments = splitter.split_chinese_text(long_chinese, 0.0, 8.0)
    
    print(f"原始文本: {long_chinese}")
    print(f"切分结果 ({len(chinese_segments)} 段):")
    for i, segment in enumerate(chinese_segments, 1):
        start_time = segment['timestamp'][0]
        end_time = segment['timestamp'][1]
        text = segment['text']
        print(f"  {i}. [{start_time:.1f}s - {end_time:.1f}s] {text} ({len(text)} 字符)")
    
    print("\n" + "="*60 + "\n")
    
    # 测试双语切分
    print("🧪 测试双语切分...")
    bilingual_segments = splitter.split_bilingual_text(
        long_english, long_chinese, 0.0, 12.0
    )
    
    print("双语切分结果:")
    for i, segment in enumerate(bilingual_segments, 1):
        start_time = segment['timestamp'][0]
        end_time = segment['timestamp'][1]
        english = segment['english']
        chinese = segment['chinese']
        print(f"  {i}. [{start_time:.1f}s - {end_time:.1f}s]")
        print(f"     英文: {english}")
        print(f"     中文: {chinese}")
    
    print("\n" + "="*60 + "\n")
    
    # 测试实际的字幕块切分
    print("🧪 测试实际字幕块切分...")
    
    # 模拟 Whisper 识别结果
    mock_chunks = [
        {
            "text": "Hello everyone, welcome to our channel. Today we're going to talk about artificial intelligence and machine learning.",
            "timestamp": [0.0, 5.5]
        },
        {
            "text": "First, let's understand what artificial intelligence really means and how it can help us in our daily lives.",
            "timestamp": [6.0, 11.2]
        }
    ]
    
    # 单语模式切分
    split_result = split_subtitle_chunks(
        mock_chunks, 
        is_bilingual=False, 
        max_chars_per_line=20, 
        max_words_per_line=7
    )
    
    print("单语模式切分结果:")
    for i, chunk in enumerate(split_result, 1):
        start_time = chunk['timestamp'][0]
        end_time = chunk['timestamp'][1]
        text = chunk['text']
        print(f"  {i}. [{start_time:.1f}s - {end_time:.1f}s] {text}")
    
    # 双语模式测试
    bilingual_chunks = [
        {
            "english": "Hello everyone, welcome to our channel. Today we're going to talk about AI.",
            "chinese": "大家好，欢迎来到我们的频道。今天我们要讨论人工智能。",
            "timestamp": [0.0, 5.0]
        }
    ]
    
    bilingual_split_result = split_subtitle_chunks(
        bilingual_chunks,
        is_bilingual=True,
        max_chars_per_line=18,
        max_words_per_line=6
    )
    
    print("\n双语模式切分结果:")
    for i, chunk in enumerate(bilingual_split_result, 1):
        start_time = chunk['timestamp'][0]
        end_time = chunk['timestamp'][1]
        english = chunk['english']
        chinese = chunk['chinese']
        print(f"  {i}. [{start_time:.1f}s - {end_time:.1f}s]")
        print(f"     EN: {english}")
        print(f"     CN: {chinese}")
    
    print("\n✅ 短字幕切分功能测试完成！")
    print("💡 现在字幕已经适合在手机屏幕上显示了！")
    
    return True

if __name__ == "__main__":
    test_subtitle_splitter() 