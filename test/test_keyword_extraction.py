#!/usr/bin/env python3
"""
测试AI关键词提取功能
"""

import sys
import os
sys.path.append('src')

def test_keyword_extraction():
    """测试关键词提取功能"""
    print("=== 测试AI关键词提取功能 ===\n")
    
    try:
        from keyword_extractor import keyword_extractor
        print("✅ 关键词提取器导入成功")
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    # 测试单条文本提取
    print("\n🧪 测试单条文本提取...")
    test_text = "Today we will discuss artificial intelligence and machine learning. These technologies are becoming increasingly important in our daily lives."
    
    keywords = keyword_extractor.extract_keywords_from_text(test_text)
    print(f"📝 测试文本: {test_text}")
    print(f"🎯 提取结果: {len(keywords)} 个关键词")
    
    for i, keyword in enumerate(keywords, 1):
        print(f"  {i}. {keyword['key_word']} {keyword.get('phonetic_symbol', '')} - {keyword.get('explain_text', '')}")
    
    # 测试字幕批量提取
    print("\n🧪 测试字幕批量提取...")
    mock_subtitles = [
        {
            'id': 1,
            'english_text': 'Hello everyone, welcome to our artificial intelligence course.',
            'chinese_text': '大家好，欢迎来到我们的人工智能课程。'
        },
        {
            'id': 2,
            'english_text': 'Machine learning is a subset of artificial intelligence.',
            'chinese_text': '机器学习是人工智能的一个子集。'
        },
        {
            'id': 3,
            'english_text': 'Deep learning algorithms can process vast amounts of data.',
            'chinese_text': '深度学习算法可以处理大量数据。'
        }
    ]
    
    print(f"📚 模拟字幕: {len(mock_subtitles)} 条")
    
    # 使用批量提取模式
    batch_keywords = keyword_extractor.batch_extract_with_context(mock_subtitles, batch_size=2)
    print(f"🎉 批量提取结果: {len(batch_keywords)} 个关键词")
    
    for i, keyword in enumerate(batch_keywords, 1):
        print(f"  {i}. [{keyword.get('subtitle_id')}] {keyword['key_word']} {keyword.get('phonetic_symbol', '')} - {keyword.get('explain_text', '')}")
    
    print("\n✅ 关键词提取功能测试完成！")
    print("💡 现在可以在数据库管理界面使用AI提取关键词功能了！")
    
    return True

def test_database_integration():
    """测试数据库集成"""
    print("\n=== 测试数据库集成 ===")
    
    try:
        from database import db_manager
        
        # 检查是否有测试数据
        stats = db_manager.get_statistics()
        print(f"📊 当前数据库状态:")
        print(f"  - 媒体系列: {stats['series_count']}")
        print(f"  - 字幕条目: {stats['subtitle_count']}")
        print(f"  - 关键词数: {stats['keyword_count']}")
        
        if stats['series_count'] > 0:
            # 获取第一个系列的字幕
            all_series = db_manager.get_series()
            first_series = all_series[0]
            series_id = first_series['id']
            
            subtitles = db_manager.get_subtitles(series_id)
            print(f"\n📝 系列 {series_id} 有 {len(subtitles)} 条字幕")
            
            if len(subtitles) > 0:
                print("🎯 可以在数据库管理界面使用AI提取功能")
                print(f"🔗 访问: http://localhost:7861")
                print(f"📋 在关键词库页面输入系列ID: {series_id}")
                print("🤖 点击 'AI提取关键词' 按钮")
            else:
                print("⚠️ 该系列没有字幕数据")
        else:
            print("💡 建议先处理一些音视频文件生成字幕，然后再测试AI提取功能")
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")

if __name__ == "__main__":
    test_keyword_extraction()
    test_database_integration() 