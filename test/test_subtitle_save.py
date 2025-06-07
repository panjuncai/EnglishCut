#!/usr/bin/env python3
"""
测试字幕保存到数据库
"""

import sys
import os
import json
# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import db_manager
from src.logger import LOG

def test_subtitle_save():
    """测试字幕保存到数据库"""
    print("\n=== 测试字幕保存到数据库 ===\n")
    
    try:
        # 获取所有系列
        series_list = db_manager.get_series()
        if not series_list:
            print("⚠️ 数据库中没有系列数据")
            return False
        
        print(f"查询到 {len(series_list)} 条系列数据")
        
        # 选择第一个系列作为测试对象
        test_series = series_list[0]
        series_id = test_series['id']
        print(f"\n使用系列: ID={series_id}, 名称={test_series['name']}")
        
        # 创建测试字幕数据
        test_subtitles = [
            {
                'begin_time': 0.0,
                'end_time': 5.0,
                'english_text': 'This is a test subtitle 1',
                'chinese_text': '这是测试字幕1'
            },
            {
                'begin_time': 5.0,
                'end_time': 10.0,
                'english_text': 'This is a test subtitle 2',
                'chinese_text': '这是测试字幕2'
            }
        ]
        
        # 保存字幕
        print(f"\n尝试保存 {len(test_subtitles)} 条测试字幕到系列 {series_id}")
        subtitle_ids = db_manager.create_subtitles(series_id, test_subtitles)
        
        if subtitle_ids:
            print(f"✅ 成功保存 {len(subtitle_ids)} 条字幕，ID: {subtitle_ids}")
            
            # 验证保存结果
            saved_subtitles = db_manager.get_subtitles(series_id)
            print(f"\n查询到 {len(saved_subtitles)} 条字幕")
            
            # 打印前2条字幕内容
            for i, subtitle in enumerate(saved_subtitles[:2]):
                print(f"\n字幕 {i+1}:")
                for key, value in subtitle.items():
                    print(f"  {key}: {value}")
        else:
            print("❌ 保存字幕失败")
        
        print("\n✅ 测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_subtitle_save() 