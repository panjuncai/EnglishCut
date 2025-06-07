#!/usr/bin/env python3
"""
测试移动端优化的视频烧制功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from video_subtitle_burner import video_burner
from database import db_manager
from logger import LOG

def test_mobile_subtitle_generation():
    """测试移动端优化的ASS字幕生成"""
    print("\n📱 测试移动端ASS字幕生成...")
    
    # 模拟烧制数据
    test_burn_data = [
        {
            'begin_time': 0.0,
            'end_time': 3.5,
            'keyword': 'technology',
            'phonetic': '/tekˈnɒlədʒi/',
            'explanation': '技术',
            'coca_rank': 15000
        },
        {
            'begin_time': 5.0,
            'end_time': 8.2,
            'keyword': 'revolutionary',
            'phonetic': '/ˌrevəˈluːʃəˌneri/',
            'explanation': '革命性的',
            'coca_rank': 18000
        }
    ]
    
    # 创建临时ASS字幕文件
    subtitle_path = "test_mobile_keywords.ass"
    actual_path = video_burner.create_subtitle_file(test_burn_data, subtitle_path)
    
    # 读取并显示内容
    if os.path.exists(actual_path):
        print(f"✅ ASS字幕文件创建成功: {actual_path}")
        with open(actual_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("ASS字幕内容:")
            print("=" * 50)
            print(content)
            print("=" * 50)
        
        # 清理
        os.remove(actual_path)
        print("🧹 临时文件已清理")
    else:
        print("❌ ASS字幕文件创建失败")

def test_video_filter_chain():
    """测试视频滤镜链"""
    print("\n🎬 测试视频滤镜链...")
    
    test_ass_path = "/tmp/test.ass"
    filter_chain = video_burner._build_video_filter(test_ass_path)
    
    print("生成的FFmpeg滤镜链:")
    print(filter_chain)
    
    # 验证滤镜链包含正确的元素
    expected_elements = [
        "crop=ih*3/4:ih",  # 3:4裁剪
        "ass=",  # ASS字幕
    ]
    
    for element in expected_elements:
        if element in filter_chain:
            print(f"✅ 包含: {element}")
        else:
            print(f"❌ 缺失: {element}")

def test_mobile_optimization_features():
    """测试移动端优化特性"""
    print("\n📱 测试移动端优化特性...")
    
    features = {
        "3:4 竖屏格式": "crop=ih*3/4:ih",
        "ASS字幕支持": "ass=",
        "分层字体大小": "Style: Keyword,Arial,40",
        "橙色背景": "&H0000A5FF",
        "黑色字体": "&H00000000"
    }
    
    # 创建测试字幕文件检查特性
    test_burn_data = [{
        'begin_time': 0.0,
        'end_time': 2.0,
        'keyword': 'test',
        'phonetic': '/test/',
        'explanation': '测试',
        'coca_rank': 10000
    }]
    
    subtitle_path = "feature_test.ass"
    actual_path = video_burner.create_subtitle_file(test_burn_data, subtitle_path)
    
    if os.path.exists(actual_path):
        with open(actual_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for feature_name, pattern in features.items():
            if pattern in content or pattern in video_burner._build_video_filter(actual_path):
                print(f"✅ {feature_name}: 已实现")
            else:
                print(f"❌ {feature_name}: 未找到")
        
        os.remove(actual_path)
    
    print("\n🎨 样式配置:")
    print("- 单词字体: Arial 40pt Bold 黑色")
    print("- 中文字体: Arial 28pt 黑色") 
    print("- 音标字体: Arial 20pt 黑色")
    print("- 背景颜色: 橙色 (#FFA500)")
    print("- 位置: 底部居中，边距80px")

def test_time_conversion():
    """测试时间格式转换"""
    print("\n⏰ 测试时间格式转换...")
    
    test_times = [0.0, 65.5, 3661.25]  # 0秒, 1分5.5秒, 1小时1分1.25秒
    
    for seconds in test_times:
        srt_time = video_burner._seconds_to_srt_time(seconds)
        ass_time = video_burner._seconds_to_ass_time(seconds)
        print(f"⏱️ {seconds}s -> SRT: {srt_time} | ASS: {ass_time}")

def test_output_file_naming():
    """测试输出文件命名"""
    print("\n📁 测试输出文件命名...")
    
    # 模拟文件路径
    test_inputs = [
        "/path/to/video.mp4",
        "news_report.mov",
        "/media/interview_2024.avi"
    ]
    
    for input_path in test_inputs:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{base_name}_keywords_mobile.mp4"
        print(f"📹 {input_path} -> {output_name}")

if __name__ == "__main__":
    print("📱 移动端视频烧制功能测试\n")
    
    try:
        test_mobile_subtitle_generation()
        test_video_filter_chain()
        test_mobile_optimization_features()
        test_time_conversion()
        test_output_file_naming()
        
        print("\n✅ 所有移动端优化测试完成！")
        print("\n📋 新功能特点:")
        print("🎯 3:4 竖屏格式 - 完美适配手机屏幕")
        print("🎨 分层字体设计 - 单词大、中文中、音标小")
        print("🧡 橙色背景黑字 - 高对比度，易阅读")
        print("📍 底部居中显示 - 不遮挡重要内容")
        print("🔄 ASS字幕支持 - 支持复杂样式设置")
        
        print("\n🚀 使用建议:")
        print("1. 最适合新闻类视频 (16:9横屏源)")
        print("2. 手机竖屏观看体验最佳")
        print("3. 重点词汇密度适中，学习效果好")
        print("4. 支持音标、单词、中文三层信息")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 