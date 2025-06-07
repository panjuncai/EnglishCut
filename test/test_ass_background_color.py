#!/usr/bin/env python3
"""
测试ASS字幕背景色显示问题
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from video_subtitle_burner import video_burner

def test_ass_background_color():
    """测试不同的ASS背景色设置方案"""
    print("🎨 测试ASS背景色设置...")
    
    # 创建多种背景色测试方案
    test_styles = [
        {
            'name': '方案1: BorderStyle=3 + BackColour',
            'style': "Style: Test1,Arial,24,&H00000000,&H00000000,&H00000000,&H0000FFFF,1,0,0,0,100,100,0,0,3,0,0,2,20,20,20,1"
        },
        {
            'name': '方案2: BorderStyle=4 + BackColour',
            'style': "Style: Test2,Arial,24,&H00000000,&H00000000,&H00000000,&H0000FFFF,1,0,0,0,100,100,0,0,4,0,0,2,20,20,20,1"
        },
        {
            'name': '方案3: 轮廓+阴影背景',
            'style': "Style: Test3,Arial,24,&H00000000,&H00000000,&H0000FFFF,&H0000FFFF,1,0,0,0,100,100,0,0,1,3,2,2,20,20,20,1"
        },
        {
            'name': '方案4: 纯背景框',
            'style': "Style: Test4,Arial,24,&H00000000,&H00000000,&H00000000,&H0000FFFF,1,0,0,0,100,100,0,0,3,0,0,2,20,20,20,1"
        }
    ]
    
    for i, test in enumerate(test_styles, 1):
        print(f"\n🧪 {test['name']}")
        
        # 创建测试ASS文件
        ass_content = [
            "[Script Info]",
            "Title: Background Color Test",
            "ScriptType: v4.00+",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            test['style'],
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            f"Dialogue: 0,0:00:00.00,0:00:03.00,Test{i},,0,0,0,,测试背景色{i}"
        ]
        
        test_file = f"test_bg_color_{i}.ass"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ass_content))
        
        print(f"   📁 创建测试文件: {test_file}")
        print(f"   🎯 样式设置: {test['style']}")
        
        # 清理
        if os.path.exists(test_file):
            os.remove(test_file)

def analyze_ass_color_format():
    """分析ASS颜色格式"""
    print("\n🔍 ASS颜色格式分析:")
    
    colors = {
        "&H0000FFFF": "纯黄色 (#FFFF00)",
        "&H0000B2FF": "深黄色 (#FFB200)", 
        "&H00FFFF00": "青色 (#00FFFF)",
        "&H000000FF": "红色 (#FF0000)",
        "&H0000FF00": "绿色 (#00FF00)",
        "&H00FF0000": "蓝色 (#0000FF)"
    }
    
    for code, desc in colors.items():
        print(f"   {code} = {desc}")
    
    print("\n💡 ASS颜色格式说明:")
    print("   - 格式: &HAABBGGRR (Alpha, Blue, Green, Red)")
    print("   - &H0000FFFF = A:00 B:00 G:FF R:FF = #FFFF00 (黄色)")

def suggest_solutions():
    """建议解决方案"""
    print("\n🔧 可能的解决方案:")
    
    solutions = [
        {
            'problem': '背景色不显示',
            'solutions': [
                '使用BorderStyle=1，设置Outline和OutlineColour',
                '使用BorderStyle=3，确保BackColour正确',
                '检查FFmpeg是否支持ASS背景色',
                '尝试使用SRT字幕 + force_style参数'
            ]
        }
    ]
    
    for item in solutions:
        print(f"\n❌ 问题: {item['problem']}")
        for i, sol in enumerate(item['solutions'], 1):
            print(f"   {i}. {sol}")

def test_srt_alternative():
    """测试SRT字幕作为替代方案"""
    print("\n🔄 测试SRT字幕替代方案...")
    
    # SRT with force_style可能更可靠
    print("SRT + force_style 参数:")
    print("subtitles='subtitle.srt':force_style='BackColour=&H0000FFFF,BorderStyle=4'")
    
    print("\n💡 建议:")
    print("1. 如果ASS背景色有问题，可以回退到SRT格式")
    print("2. 使用FFmpeg的force_style参数设置背景色")
    print("3. 这样可能更兼容不同的FFmpeg版本")

if __name__ == "__main__":
    print("🔧 ASS背景色调试测试\n")
    
    try:
        test_ass_background_color()
        analyze_ass_color_format()
        suggest_solutions()
        test_srt_alternative()
        
        print("\n📋 调试结论:")
        print("1. ASS背景色设置复杂，可能需要特定参数组合")
        print("2. BorderStyle=3 理论上应该显示背景色")
        print("3. 如果ASS不工作，可以回退到SRT + force_style")
        print("4. 需要测试实际FFmpeg渲染效果")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 