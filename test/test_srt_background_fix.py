#!/usr/bin/env python3
"""
测试SRT + force_style背景色方案
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from video_subtitle_burner import video_burner

def test_srt_background_color():
    """测试SRT字幕背景色方案"""
    print("🔧 测试SRT + force_style背景色方案...")
    
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
    
    # 创建测试SRT字幕文件
    subtitle_path = "test_srt_background.srt"
    actual_path = video_burner.create_subtitle_file(test_burn_data, subtitle_path)
    
    # 读取并显示内容
    if os.path.exists(actual_path):
        print(f"✅ SRT字幕文件创建成功: {actual_path}")
        
        with open(actual_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\n📄 SRT字幕内容:")
        print("=" * 50)
        print(content)
        print("=" * 50)
        
        # 清理
        os.remove(actual_path)
        print("🧹 临时文件已清理")
    else:
        print("❌ SRT字幕文件创建失败")

def test_ffmpeg_force_style():
    """测试FFmpeg force_style参数"""
    print("\n🎬 测试FFmpeg force_style参数...")
    
    test_srt_path = "/tmp/test.srt"
    filter_chain = video_burner._build_video_filter(test_srt_path)
    
    print("生成的FFmpeg滤镜链:")
    print(filter_chain)
    
    # 检查force_style参数
    if "force_style=" in filter_chain:
        print("✅ 包含force_style参数")
        
        # 提取force_style部分
        start = filter_chain.find("force_style='") + len("force_style='")
        end = filter_chain.find("'", start)
        force_style = filter_chain[start:end]
        
        print(f"\n🎨 force_style参数解析:")
        style_params = force_style.split(',')
        for param in style_params:
            print(f"   - {param}")
            
        # 检查关键参数
        key_params = {
            'BackColour=&H0000FFFF': '黄色背景',
            'BorderStyle=4': '背景框样式',
            'PrimaryColour=&H00000000': '黑色文字',
            'Fontsize=24': '24pt字体',
            'Alignment=2': '底部居中',
            'MarginV=20': '底部边距20px'
        }
        
        print(f"\n🔍 参数验证:")
        for param, desc in key_params.items():
            if param in force_style:
                print(f"   ✅ {param} - {desc}")
            else:
                print(f"   ❌ {param} - {desc} (缺失)")
    else:
        print("❌ 未找到force_style参数")

def compare_srt_vs_ass():
    """对比SRT和ASS方案"""
    print("\n⚖️ SRT vs ASS 方案对比:")
    
    comparison = [
        {
            'aspect': '背景色支持',
            'srt': '✅ force_style参数可靠',
            'ass': '❌ BorderStyle复杂，可能不显示'
        },
        {
            'aspect': 'FFmpeg兼容性',
            'srt': '✅ 广泛支持',
            'ass': '⚠️ 版本依赖性强'
        },
        {
            'aspect': '样式复杂度',
            'srt': '⚠️ 相对简单',
            'ass': '✅ 支持复杂样式'
        },
        {
            'aspect': '调试难度',
            'srt': '✅ 简单直观',
            'ass': '❌ 复杂，难调试'
        }
    ]
    
    for item in comparison:
        print(f"\n🎯 {item['aspect']}:")
        print(f"   SRT: {item['srt']}")
        print(f"   ASS: {item['ass']}")

def show_force_style_options():
    """显示force_style可用选项"""
    print("\n📋 force_style可用参数:")
    
    options = {
        'Fontname': 'Arial, Times New Roman, 等',
        'Fontsize': '字体大小 (如: 24)',
        'PrimaryColour': '文字颜色 (&H00000000=黑色)',
        'BackColour': '背景颜色 (&H0000FFFF=黄色)',
        'BorderStyle': '边框样式 (1=轮廓, 3=背景框, 4=背景框+轮廓)',
        'Outline': '轮廓粗细 (如: 2)',
        'Shadow': '阴影 (如: 1)',
        'Alignment': '对齐 (1=左下, 2=中下, 3=右下)',
        'MarginV': '垂直边距 (如: 20)',
        'MarginL': '左边距',
        'MarginR': '右边距',
        'Bold': '粗体 (1=开启, 0=关闭)',
        'Italic': '斜体 (1=开启, 0=关闭)'
    }
    
    for param, desc in options.items():
        print(f"   {param}: {desc}")

if __name__ == "__main__":
    print("🔧 SRT背景色修复方案测试\n")
    
    try:
        test_srt_background_color()
        test_ffmpeg_force_style()
        compare_srt_vs_ass()
        show_force_style_options()
        
        print("\n✅ SRT背景色方案测试完成！")
        print("\n🎯 主要优势:")
        print("✅ 背景色显示可靠")
        print("✅ FFmpeg兼容性好")
        print("✅ 参数调试简单")
        print("✅ 支持分层字体效果")
        
        print("\n💡 使用建议:")
        print("1. SRT格式更适合背景色需求")
        print("2. force_style参数功能强大且可靠")
        print("3. 可以通过调整BorderStyle优化显示效果")
        print("4. 建议使用BorderStyle=4获得最佳背景效果")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 