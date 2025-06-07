#!/usr/bin/env python3
"""
测试视频命名和路径存储功能
"""

import sys
import os
import tempfile
import shutil
sys.path.append('src')

from logger import LOG
from media_processor import MediaProcessor
from video_processor import check_ffmpeg_availability

def test_video_naming_and_paths():
    """测试视频命名和路径存储"""
    print("=== 测试视频命名和路径功能 ===\n")
    
    # 检查ffmpeg可用性
    if not check_ffmpeg_availability():
        print("❌ 未找到ffmpeg，无法进行测试")
        return False
    
    # 创建测试视频
    test_video_path = create_test_video()
    if not test_video_path:
        print("❌ 创建测试视频失败")
        return False
    
    print(f"✅ 创建测试视频成功: {test_video_path}")
    
    try:
        # 确保input和output目录不存在（干净测试）
        for dir_path in ["input", "output"]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                print(f"🧹 清理目录: {dir_path}")
        
        # 创建媒体处理器
        processor = MediaProcessor()
        
        # 执行视频处理
        print("🔄 开始处理视频...")
        result = processor.process_file(
            file_path=test_video_path,
            output_format="SRT",
            enable_translation=True,
            enable_short_subtitles=False
        )
        
        if not result or not result.get('success'):
            print(f"❌ 视频处理失败: {result.get('error', '未知错误')}")
            return False
        
        print("✅ 视频处理成功!")
        
        # 检查预处理视频和字幕文件是否生成
        video_name = os.path.basename(test_video_path)
        base_name = os.path.splitext(video_name)[0]
        
        expected_video_path = f"input/{base_name}_1.mp4"
        expected_srt_path = f"output/{base_name}.srt"
        
        # 检查预处理视频
        if os.path.exists(expected_video_path):
            print(f"✅ 预处理视频生成成功: {expected_video_path}")
            video_size = os.path.getsize(expected_video_path) / (1024 * 1024)  # MB
            print(f"   视频大小: {video_size:.2f} MB")
        else:
            print(f"❌ 预处理视频不存在: {expected_video_path}")
            return False
        
        # 检查字幕文件
        if os.path.exists(expected_srt_path):
            print(f"✅ 字幕文件生成成功: {expected_srt_path}")
            with open(expected_srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
                print(f"   字幕内容预览: {srt_content[:100]}...")
        else:
            print(f"❌ 字幕文件不存在: {expected_srt_path}")
            return False
        
        # 检查数据库中是否更新了路径
        from database import db_manager
        series_list = db_manager.get_series()
        latest_series = series_list[0] if series_list else None
        
        if latest_series:
            print("\n📊 数据库中的最新记录:")
            print(f"  ID: {latest_series['id']}")
            print(f"  名称: {latest_series['name']}")
            print(f"  9:16视频名: {latest_series.get('new_name')}")
            print(f"  9:16视频路径: {latest_series.get('new_file_path')}")
            
            # 验证路径是否正确
            if latest_series.get('new_file_path') == os.path.abspath(expected_video_path):
                print("✅ 数据库中的路径正确")
            else:
                print(f"❌ 数据库中的路径与预期不符:")
                print(f"  预期: {os.path.abspath(expected_video_path)}")
                print(f"  实际: {latest_series.get('new_file_path')}")
        else:
            print("❌ 数据库中没有找到记录")
            return False
        
        print("\n✅ 视频命名和路径功能测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False
    finally:
        # 清理测试视频
        if test_video_path and os.path.exists(test_video_path):
            os.remove(test_video_path)
            print(f"🧹 清理测试视频: {test_video_path}")

def create_test_video():
    """创建一个测试视频文件（使用 ffmpeg 生成）"""
    print("🎬 创建测试视频文件...")
    
    try:
        # 创建临时视频文件路径
        temp_dir = tempfile.gettempdir()
        test_video_path = os.path.join(temp_dir, "test_video.mp4")
        
        # 使用 ffmpeg 创建一个 5 秒的测试视频（含音频）
        import subprocess
        
        cmd = [
            "ffmpeg", "-y",  # 覆盖输出文件
            "-f", "lavfi",   # 使用 lavfi 输入
            "-i", "testsrc2=duration=5:size=640x480:rate=24",  # 5秒测试视频
            "-f", "lavfi",   # 音频输入
            "-i", "sine=frequency=440:duration=5",  # 440Hz 正弦波音频
            "-c:v", "libx264",  # 视频编码器
            "-c:a", "aac",      # 音频编码器
            "-shortest",        # 使用最短的流长度
            test_video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(test_video_path):
            return test_video_path
        else:
            print(f"❌ 创建测试视频失败: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ 创建测试视频时发生错误: {e}")
        return None

if __name__ == "__main__":
    test_video_naming_and_paths() 