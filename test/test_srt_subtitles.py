#!/usr/bin/env python3
"""
测试 SRT 字幕功能
"""

import sys
import os
sys.path.append('src')

from openai_whisper import generate_srt_content, save_srt_file
from openai_translate import translate_text
from src.logger import LOG

def test_srt_functionality():
    """测试 SRT 字幕功能"""
    print("=== 测试 SRT 字幕功能 ===\n")
    
    # 模拟音频识别结果（用于测试）
    mock_result = {
        "english_text": "Hello, how are you today? The weather is beautiful today.",
        "english_chunks": [
            {"text": "Hello, how are you today?", "timestamp": [0.0, 3.5]},
            {"text": "The weather is beautiful today.", "timestamp": [4.0, 7.8]}
        ],
        "text": "Hello, how are you today? The weather is beautiful today.",
        "chunks": [
            {"text": "Hello, how are you today?", "timestamp": [0.0, 3.5]},
            {"text": "The weather is beautiful today.", "timestamp": [4.0, 7.8]}
        ],
        "processing_time": 5.2,
        "is_bilingual": False
    }
    
    print("🧪 测试单语 SRT 字幕生成...")
    
    # 测试单语 SRT
    srt_content_mono = generate_srt_content(mock_result, "test_audio")
    print("单语 SRT 内容:")
    print("-" * 50)
    print(srt_content_mono)
    print("-" * 50)
    
    print("\n🧪 测试双语 SRT 字幕生成...")
    
    # 测试双语翻译
    try:
        chinese_text = translate_text(mock_result['english_text'])
        print(f"整体翻译: {chinese_text}")
        
        # 更新模拟结果为双语
        mock_result['chinese_text'] = chinese_text
        mock_result['is_bilingual'] = True
        
        # 翻译分段
        chinese_chunks = []
        for chunk in mock_result['english_chunks']:
            english_chunk = chunk['text']
            chinese_chunk = translate_text(english_chunk)
            chinese_chunks.append({
                "text": chinese_chunk,
                "timestamp": chunk['timestamp']
            })
            print(f"分段翻译: {english_chunk} -> {chinese_chunk}")
        
        mock_result['chinese_chunks'] = chinese_chunks
        
        # 生成双语 SRT 内容
        print("\n📄 生成双语 SRT 字幕...")
        srt_content_bilingual = generate_srt_content(mock_result, "test_audio")
        print("双语 SRT 内容:")
        print("-" * 50)
        print(srt_content_bilingual)
        print("-" * 50)
        
        # 测试保存文件
        print("\n💾 测试保存 SRT 文件...")
        temp_audio_path = "test_audio.mp3"  # 模拟音频文件路径
        srt_file_path = save_srt_file(mock_result, temp_audio_path)
        
        if srt_file_path and os.path.exists(srt_file_path):
            print(f"✅ SRT 文件已保存到: {srt_file_path}")
            
            # 读取并显示文件内容
            with open(srt_file_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            print("\n保存的文件内容预览:")
            print(saved_content[:300] + "..." if len(saved_content) > 300 else saved_content)
        else:
            print("❌ SRT 文件保存失败")
        
        print("\n✅ SRT 字幕功能测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ SRT 字幕功能测试失败: {e}")
        return False

def test_srt_time_format():
    """测试 SRT 时间格式"""
    print("\n=== 测试 SRT 时间格式 ===")
    
    from openai_whisper import format_time_srt
    
    test_times = [0.0, 3.5, 65.123, 3661.456, None]
    
    for time_val in test_times:
        formatted = format_time_srt(time_val)
        print(f"时间 {time_val} -> SRT格式: {formatted}")

if __name__ == "__main__":
    print("请确保已激活 conda 环境：conda activate englishcut")
    print("请确保 .env 文件中配置了正确的 OpenAI API 密钥\n")
    
    # 测试时间格式
    test_srt_time_format()
    
    # 测试 SRT 功能
    test_srt_functionality() 