#!/usr/bin/env python3
"""
EnglishCut 服务启动脚本
启动主界面和数据库管理界面
"""

import os
import sys
import subprocess
import time
import webbrowser
from threading import Thread

def start_main_interface():
    """启动主界面"""
    print("🚀 启动主界面 (端口 7860)...")
    subprocess.run([sys.executable, "src/gradio_server.py"])

def start_database_interface():
    """启动数据库管理界面"""
    print("📊 启动数据库管理界面 (端口 7861)...")
    subprocess.run([sys.executable, "src/database_interface.py"])

def main():
    """主函数"""
    print("=== EnglishCut 音视频字幕生成器 ===")
    print("🎵 支持音频/视频转文字和字幕生成")
    print("📊 支持数据库管理和关键词库")
    print("🌐 支持双语字幕和语义单元切分")
    print("=" * 40)
    
    # 创建并启动线程
    main_thread = Thread(target=start_main_interface)
    db_thread = Thread(target=start_database_interface)
    
    print("启动服务中...")
    
    # 启动主界面
    main_thread.daemon = True
    main_thread.start()
    
    # 等待一下再启动数据库界面
    time.sleep(2)
    
    # 启动数据库管理界面
    db_thread.daemon = True
    db_thread.start()
    
    # 等待服务启动
    time.sleep(3)
    
    print("\n✅ 服务启动完成！")
    print("🌐 主界面: http://localhost:7860")
    print("📊 数据库管理: http://localhost:7861")
    print("\n📖 使用说明:")
    print("  1. 访问主界面上传音频/视频文件生成字幕")
    print("  2. 启用'短视频字幕模式'获得语义单元切分")
    print("  3. 启用'中文翻译'生成双语字幕")
    print("  4. 访问数据库管理界面查看已处理的内容")
    print("  5. 在数据库界面可以手动添加重点单词")
    print("\n按 Ctrl+C 退出服务")
    
    try:
        # 自动打开浏览器
        webbrowser.open("http://localhost:7860")
        time.sleep(1)
        webbrowser.open("http://localhost:7861")
        
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 正在关闭服务...")
        sys.exit(0)

if __name__ == "__main__":
    main() 