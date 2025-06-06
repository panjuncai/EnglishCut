#!/usr/bin/env python3
"""
测试 openai_whisper.py 中的翻译功能
"""

import sys
import os
sys.path.append('src')

from openai_translate import translate_text
from src.logger import LOG

def test_translation():
    """测试翻译功能"""
    print("=== 测试翻译功能集成 ===\n")
    
    # 测试翻译功能
    test_texts = [
        "Hello, how are you today?",
        "The weather is beautiful today.",
        "I love programming and artificial intelligence.",
        "This is a test of the translation function integrated into the Whisper module."
    ]
    
    print("测试翻译功能...")
    for i, english_text in enumerate(test_texts, 1):
        print(f"\n测试 {i}:")
        print(f"英文: {english_text}")
        
        try:
            chinese_text = translate_text(english_text)
            print(f"中文: {chinese_text}")
            
            if chinese_text and not chinese_text.startswith("翻译失败"):
                print("✅ 翻译成功")
            else:
                print("❌ 翻译失败或返回错误信息")
                
        except Exception as e:
            print(f"❌ 翻译过程中出现异常: {e}")
    
    print("\n=== 测试完成 ===")
    return True

if __name__ == "__main__":
    # 设置 conda 环境提示
    print("请确保已激活 conda 环境：conda activate englishcut\n")
    
    # 运行测试
    test_translation() 