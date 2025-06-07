#!/usr/bin/env python3
"""
测试关键词提取和保存功能
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.append('.')

from src.database import db_manager
from src.logger import LOG

def test_keyword_extraction():
    """测试关键词提取和保存功能"""
    print("\n=== 测试关键词提取和保存功能 ===\n")
    
    # 1. 查找带有字幕的系列
    all_series = db_manager.get_series()
    selected_series = None
    
    for series in all_series:
        series_id = series['id']
        subtitles = db_manager.get_subtitles(series_id)
        if subtitles and len(subtitles) > 0:
            selected_series = series
            print(f"找到带字幕的系列: ID={series_id}, 名称={series['name']}, 字幕数量={len(subtitles)}")
            break
    
    if not selected_series:
        print("❌ 未找到带字幕的系列，无法测试")
        return
    
    series_id = selected_series['id']
    subtitles = db_manager.get_subtitles(series_id)
    
    # 2. 导入关键词提取器
    try:
        from src.keyword_extractor import keyword_extractor
        print("✅ 导入关键词提取器成功")
    except ImportError:
        print("❌ 导入关键词提取器失败")
        return
    
    # 3. 删除现有关键词
    existing_keywords = db_manager.get_keywords(series_id=series_id)
    if existing_keywords:
        print(f"删除 {len(existing_keywords)} 个现有关键词")
        db_manager.delete_keywords_by_series_id(series_id)
    
    # 4. 提取关键词
    print(f"开始从 {len(subtitles)} 条字幕中提取关键词...")
    start_time = time.time()
    
    # 使用批量提取模式
    extracted_keywords = keyword_extractor.batch_extract_with_context(subtitles, batch_size=3)
    
    end_time = time.time()
    extraction_time = end_time - start_time
    
    print(f"✅ 提取完成，耗时 {extraction_time:.2f} 秒，提取了 {len(extracted_keywords)} 个关键词")
    
    # 打印前5个关键词
    print("\n前5个关键词:")
    for i, kw in enumerate(extracted_keywords[:5]):
        print(f"{i+1}. {kw['key_word']} - {kw['explain_text']}")
    
    # 5. 保存关键词到数据库
    # 将每个关键词按照subtitle_id分组
    keywords_by_subtitle = {}
    for kw in extracted_keywords:
        subtitle_id = kw.get('subtitle_id')
        if subtitle_id not in keywords_by_subtitle:
            keywords_by_subtitle[subtitle_id] = []
        keywords_by_subtitle[subtitle_id].append(kw)
    
    # 按照subtitle_id分批保存
    saved_count = 0
    for subtitle_id, keywords in keywords_by_subtitle.items():
        if keywords:
            keyword_ids = db_manager.create_keywords(subtitle_id, keywords)
            saved_count += len(keyword_ids)
    
    print(f"✅ 成功保存 {saved_count}/{len(extracted_keywords)} 个关键词到数据库")
    
    # 6. 验证保存结果
    new_keywords = db_manager.get_keywords(series_id=series_id)
    print(f"✅ 从数据库检索到 {len(new_keywords)} 个关键词")
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    test_keyword_extraction() 