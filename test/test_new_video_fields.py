#!/usr/bin/env python3
"""
测试 t_series 表新增的视频字段功能
"""

import sys
import os
sys.path.append('src')

def test_new_video_fields():
    """测试系列新增视频字段功能"""
    print("=== 测试 t_series 表新增视频字段功能 ===\n")
    
    try:
        from database import db_manager
        print("✅ 数据库模块导入成功")
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    # 1. 查看当前系列列表
    print("\n📊 当前数据库系列:")
    series_list = db_manager.get_series()
    
    if not series_list:
        print("⚠️ 数据库中没有系列数据")
        return False
    
    for series in series_list[:3]:  # 只显示前3个
        print(f"  ID: {series['id']}")
        print(f"  名称: {series['name']}")
        print(f"  类型: {series.get('file_type', '未知')}")
        print(f"  9:16视频名: {series.get('new_name', '未设置')}")
        print(f"  9:16视频路径: {series.get('new_file_path', '未设置')}")
        print(f"  关键词视频名: {series.get('second_name', '未设置')}")
        print(f"  关键词视频路径: {series.get('second_file_path', '未设置')}")
        print(f"  字幕视频名: {series.get('third_name', '未设置')}")
        print(f"  字幕视频路径: {series.get('third_file_path', '未设置')}")
        print()
    
    # 2. 测试更新功能
    test_series_id = series_list[0]['id']
    print(f"🧪 测试更新系列 {test_series_id} 的所有视频信息...")
    
    # 测试更新所有视频字段
    success = db_manager.update_series_video_info(
        test_series_id,
        new_name="test_9_16_video.mp4",
        new_file_path="input/test_9_16_video.mp4",
        second_name="test_keywords_video.mp4",
        second_file_path="input/test_keywords_video.mp4",
        third_name="test_subtitles_video.mp4",
        third_file_path="input/test_subtitles_video.mp4"
    )
    
    if success:
        print("✅ 更新成功")
        
        # 验证更新结果
        updated_series = db_manager.get_series(test_series_id)
        if updated_series:
            series_info = updated_series[0]
            print(f"📋 更新后的信息:")
            print(f"  9:16视频名: {series_info.get('new_name')}")
            print(f"  9:16视频路径: {series_info.get('new_file_path')}")
            print(f"  关键词视频名: {series_info.get('second_name')}")
            print(f"  关键词视频路径: {series_info.get('second_file_path')}")
            print(f"  字幕视频名: {series_info.get('third_name')}")
            print(f"  字幕视频路径: {series_info.get('third_file_path')}")
        else:
            print("❌ 无法获取更新后的系列信息")
    else:
        print("❌ 更新失败")
    
    # 3. 测试部分更新
    print(f"\n🧪 测试只更新关键词视频信息...")
    success = db_manager.update_series_video_info(
        test_series_id,
        second_name="only_keywords_update.mp4",
        second_file_path="input/only_keywords_update.mp4"
    )
    
    if success:
        print("✅ 部分更新成功")
        
        # 验证更新结果
        updated_series = db_manager.get_series(test_series_id)
        if updated_series:
            series_info = updated_series[0]
            print(f"📋 更新后的关键词视频名: {series_info.get('second_name')}")
            print(f"📋 更新后的关键词视频路径: {series_info.get('second_file_path')}")
            print(f"📋 9:16视频名(未变): {series_info.get('new_name')}")
            print(f"📋 字幕视频名(未变): {series_info.get('third_name')}")
    else:
        print("❌ 部分更新失败")
    
    # 4. 测试数据库表结构
    print(f"\n🔍 验证数据库表结构...")
    
    import sqlite3
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(t_series)")
            columns = cursor.fetchall()
            
            print("📋 t_series 表结构:")
            for col in columns:
                print(f"  {col[1]} - {col[2]} ({'NOT NULL' if col[3] else 'NULL'})")
            
            # 检查新字段是否存在
            column_names = [col[1] for col in columns]
            required_columns = ['new_name', 'new_file_path', 
                               'second_name', 'second_file_path', 
                               'third_name', 'third_file_path']
            
            missing_columns = [col for col in required_columns if col not in column_names]
            if missing_columns:
                print(f"❌ 缺少字段: {', '.join(missing_columns)}")
            else:
                print("✅ 所有新字段已存在")
                
    except Exception as e:
        print(f"❌ 验证表结构失败: {e}")
    
    print("\n✅ 视频字段功能测试完成！")
    print("💡 现在可以在数据库管理界面使用多视频信息管理功能了！")
    print(f"🔗 访问: http://localhost:7861")
    
    return True

if __name__ == "__main__":
    test_new_video_fields() 