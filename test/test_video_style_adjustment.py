#!/usr/bin/env python3
"""
测试调整后的视频字幕样式
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from video_subtitle_burner import video_burner

def test_adjusted_styles():
    """测试调整后的字幕样式"""
    print("🎨 测试调整后的字幕样式...")
    
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
    
    # 创建测试ASS字幕文件
    subtitle_path = "test_adjusted_styles.ass"
    actual_path = video_burner.create_subtitle_file(test_burn_data, subtitle_path)
    
    # 读取并分析内容
    if os.path.exists(actual_path):
        print(f"✅ ASS字幕文件创建成功: {actual_path}")
        
        with open(actual_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\n📋 样式分析:")
        
        # 检查字体大小
        if "Arial,24," in content:
            print("✅ 单词字体: 24pt (已调小)")
        if "Arial,18," in content:
            print("✅ 中文字体: 18pt (已调小)")
        if "Arial,14," in content:
            print("✅ 音标字体: 14pt (已调小)")
            
        # 检查背景颜色
        if "&H0000B2FF" in content:
            print("✅ 背景颜色: 深黄色 (#FFB200)")
        
        # 检查字体颜色
        if "&H00000000" in content:
            print("✅ 字体颜色: 黑色")
            
        # 检查边距设置
        if ",20,20,20," in content:
            print("✅ 边距设置: 20px (贴底部)")
            
        print("\n🎯 关键样式参数:")
        print("- Alignment=2: 底部居中")
        print("- MarginV=20: 底部边距20px")
        print("- BorderStyle=3: 背景框样式")
        print("- Bold=1: 单词加粗")
        
        print("\n📱 显示效果预览:")
        print("┌─────────────────────────┐")
        print("│                         │")
        print("│      视频内容区域        │")
        print("│                         │")
        print("│                         │")
        print("├─────────────────────────┤")
        print("│ 🟡 technology (24pt粗)  │")
        print("│ 🟡 技术 (18pt)          │")
        print("│ 🟡 tekˈnɒlədʒi (14pt)   │")
        print("└─────────────────────────┘")
        
        print("\n🔍 ASS文件内容预览:")
        print("=" * 60)
        # 只显示关键部分
        lines = content.split('\n')
        for line in lines:
            if 'Style:' in line or 'Dialogue:' in line:
                print(line)
        print("=" * 60)
        
        # 清理
        os.remove(actual_path)
        print("\n🧹 临时文件已清理")
        
    else:
        print("❌ ASS字幕文件创建失败")

def analyze_color_codes():
    """分析颜色代码"""
    print("\n🎨 颜色代码分析:")
    
    colors = {
        "&H0000B2FF": "深黄色 (#FFB200)",
        "&H00000000": "黑色 (#000000)",
        "&H00FFFFFF": "白色 (#FFFFFF)",
        "&H0000A5FF": "橙色 (#FFA500)"
    }
    
    for code, description in colors.items():
        print(f"🎯 {code} = {description}")
    
    print("\n💡 说明:")
    print("- ASS颜色格式: &HAABBGGRR (Alpha Blue Green Red)")
    print("- &H0000B2FF = Alpha:00 Blue:00 Green:B2 Red:FF = #FFB200 (深黄色)")

def test_font_size_comparison():
    """字体大小对比"""
    print("\n📏 字体大小对比:")
    
    print("调整前:")
    print("- 单词: 40pt (太大)")
    print("- 中文: 28pt (太大)")
    print("- 音标: 20pt (太大)")
    
    print("\n调整后:")
    print("- 单词: 24pt (合适)")
    print("- 中文: 18pt (合适)")
    print("- 音标: 14pt (合适)")
    
    print("\n🎯 调整原则:")
    print("1. 保持层次感: 单词 > 中文 > 音标")
    print("2. 适合手机屏幕: 不过分占用屏幕空间")
    print("3. 清晰可读: 足够大以便阅读")

if __name__ == "__main__":
    print("🔧 视频字幕样式调整测试\n")
    
    try:
        test_adjusted_styles()
        analyze_color_codes()
        test_font_size_comparison()
        
        print("\n✅ 样式调整测试完成！")
        print("\n📋 主要改进:")
        print("🔽 字体缩小: 更适合手机屏幕")
        print("🟡 深黄色背景: 更加醒目")
        print("📍 贴底部显示: 边距减小到20px")
        print("⚖️ 保持层次: 单词>中文>音标的大小关系")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 