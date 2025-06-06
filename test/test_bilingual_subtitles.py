#!/usr/bin/env python3
"""
测试双语字幕功能（LRC 和 SRT）
"""

import sys
import os
sys.path.append('src')

from openai_whisper import asr, generate_lrc_content, generate_srt_content
from src.logger import LOG

def test_bilingual_functionality():
    """测试双语字幕功能"""
    print("=== 测试双语字幕功能 ===\n")
    
    # 模拟音频识别结果（用于测试）
    mock_result = {
        "english_text": "Hello, how are you today? The weather is beautiful.",
        "english_chunks": [
            {"text": "Hello, how are you today?", "timestamp": [0.0, 3.5]},
            {"text": "The weather is beautiful.", "timestamp": [4.0, 7.0]}
        ],
        "text": "Hello, how are you today? The weather is beautiful.",
        "chunks": [
            {"text": "Hello, how are you today?", "timestamp": [0.0, 3.5]},
            {"text": "The weather is beautiful.", "timestamp": [4.0, 7.0]}
        ],
        "processing_time": 5.2,
        "is_bilingual": False
    }
    
    print("🧪 模拟双语翻译过程...")
    
    # 导入翻译函数
    from openai_translate import translate_text
    
    # 测试翻译整体文本
    print(f"英文原文: {mock_result['english_text']}")
    try:
        chinese_text = translate_text(mock_result['english_text'])
        print(f"中文翻译: {chinese_text}")
        
        # 更新模拟结果
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
        
        # 生成双语LRC内容
        print("\n📄 生成双语 LRC 字幕...")
        lrc_content = generate_lrc_content(mock_result, "test_audio")
        print("LRC内容预览:")
        print("-" * 50)
        print(lrc_content[:300] + "..." if len(lrc_content) > 300 else lrc_content)
        print("-" * 50)
        
        # 生成双语SRT内容
        print("\n📄 生成双语 SRT 字幕...")
        srt_content = generate_srt_content(mock_result, "test_audio")
        print("SRT内容预览:")
        print("-" * 50)
        print(srt_content[:400] + "..." if len(srt_content) > 400 else srt_content)
        print("-" * 50)
        
        print("\n✅ 双语字幕功能测试成功！")
        print("✅ LRC 和 SRT 格式都已正确生成")
        return True
        
    except Exception as e:
        print(f"❌ 双语字幕功能测试失败: {e}")
        return False

if __name__ == "__main__":
    print("请确保已激活 conda 环境：conda activate englishcut")
    print("请确保 .env 文件中配置了正确的 OpenAI API 密钥\n")
    
    test_bilingual_functionality() 