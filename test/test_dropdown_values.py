#!/usr/bin/env python3
"""
测试视频下拉框值的生成逻辑
"""

import sys
import os
# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import db_manager
from src.logger import LOG

def test_dropdown_values():
    """测试视频下拉框值的生成逻辑"""
    print("=== 测试视频下拉框值的生成 ===\n")
    
    # 测试直接获取所有系列
    print("\n📊 数据库中的所有系列:")
    series_list = db_manager.get_series()
    
    if not series_list:
        print("⚠️ 数据库中没有系列数据")
        return False
    
    print(f"查询到 {len(series_list)} 条系列数据")
    
    # 打印所有系列的详细信息
    for series in series_list:
        print(f"\n系列ID: {series['id']}")
        print(f"  名称: {series['name']}")
        print(f"  类型: {series.get('file_type', '未知')}")
        print(f"  9:16视频: {series.get('new_name', '未设置')}")
        print(f"  9:16路径: {series.get('new_file_path', '未设置')}")
    
    # 测试下拉框值生成逻辑
    print("\n📋 生成下拉框选项:")
    options = []
    for series in series_list:
        option_value = f"{series['id']}-{series['name']}"
        options.append(option_value)
        print(f"  选项: {option_value}")
    
    # 测试从选项中提取ID
    if options:
        test_option = options[0]
        try:
            extracted_id = int(test_option.split('-')[0])
            print(f"\n✅ 从选项 '{test_option}' 中提取ID成功: {extracted_id}")
            
            # 验证提取的ID是否有效
            test_series = db_manager.get_series(extracted_id)
            if test_series:
                print(f"✅ 通过提取的ID查询到系列: {test_series[0]['name']}")
            else:
                print(f"❌ 通过提取的ID未查询到系列: {extracted_id}")
        except Exception as e:
            print(f"❌ 提取ID失败: {e}")
    
    # 测试load_video_list函数的逻辑
    print("\n📋 测试load_video_list函数逻辑:")
    
    def load_video_list():
        """加载视频列表"""
        try:
            # 从数据库获取所有视频列表
            series_list = db_manager.get_series()
            
            # 准备下拉选项
            options = []
            for series in series_list:
                # 以id-name的形式显示所有视频
                options.append(f"{series['id']}-{series['name']}")
            
            return options
        except Exception as e:
            print(f"❌ 加载视频列表失败: {e}")
            return []
    
    dropdown_values = load_video_list()
    print(f"生成的下拉框值: {dropdown_values}")
    
    print("\n✅ 测试完成!")
    return True

if __name__ == "__main__":
    test_dropdown_values() 