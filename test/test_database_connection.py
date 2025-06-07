#!/usr/bin/env python3
"""
测试数据库连接和获取视频列表
"""

import sys
import os
import sqlite3
# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import db_manager
from src.logger import LOG

def test_database_connection():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===\n")
    
    try:
        # 检查数据库是否存在
        db_path = 'data/englishcut.db'
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / 1024  # KB
            print(f"✅ 数据库文件存在: {db_path} ({db_size:.2f} KB)")
        else:
            print(f"❌ 数据库文件不存在: {db_path}")
        
        # 测试数据库连接（直接使用sqlite3连接）
        try:
            conn = sqlite3.connect(db_path)
            print("✅ 数据库连接成功")
            
            # 手动获取表结构
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print(f"\n📊 数据库表结构:")
            for table in tables:
                table_name = table[0]
                print(f"\n表名: {table_name}")
                
                # 获取表的列信息
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                for col in columns:
                    col_id, col_name, col_type = col[0], col[1], col[2]
                    print(f"  - {col_name} ({col_type})")
            
            conn.close()
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
        
        # 获取视频列表
        series_list = db_manager.get_series()
        print(f"\n📋 视频列表查询结果:")
        print(f"查询到 {len(series_list)} 条记录")
        
        if not series_list:
            print("⚠️ 没有找到任何视频记录")
        else:
            # 检查第一条记录
            sample = series_list[0]
            print(f"\n示例记录 (ID: {sample['id']}):")
            for key, value in sample.items():
                print(f"  {key}: {value}")
        
        print("\n✅ 数据库测试完成!")
        return True
    
    except Exception as e:
        print(f"❌ 测试数据库时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_database_connection() 