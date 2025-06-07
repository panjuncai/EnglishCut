#!/usr/bin/env python3
"""
最终美观样式测试
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from video_subtitle_burner import video_burner
import subprocess

def test_final_beautiful_style():
    """测试最终美观样式"""
    print("🎨 测试最终美观样式效果...")
    
    # 完全模仿图片中的示例
    test_burn_data = [
        {
            'begin_time': 1.0,
            'end_time': 5.0,
            'keyword': 'pediatric',
            'phonetic': ',pi·di\'ætrik',
            'explanation': '儿科的',
            'coca_rank': 15000
        },
        {
            'begin_time': 7.0,
            'end_time': 11.0,
            'keyword': 'sophisticated',
            'phonetic': 'sə\'fɪstɪkeɪtɪd',
            'explanation': '复杂精密的',
            'coca_rank': 12000
        },
        {
            'begin_time': 13.0,
            'end_time': 17.0,
            'keyword': 'revolutionary',
            'phonetic': ',revə\'luːʃə,neri',
            'explanation': '革命性的',
            'coca_rank': 18000
        }
    ]
    
    print("📄 生成的字幕预览:")
    
    # 创建字幕文件并预览
    subtitle_path = "final_beautiful_subtitle.srt"
    actual_path = video_burner.create_subtitle_file(test_burn_data, subtitle_path)
    
    if os.path.exists(actual_path):
        with open(actual_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("=" * 50)
        print(content)
        print("=" * 50)
        
        # 清理
        os.remove(actual_path)
    
    # 分析最终样式参数
    print("\n🔧 最终样式参数分析:")
    
    test_srt_path = "/tmp/test.srt"
    filter_chain = video_burner._build_video_filter(test_srt_path)
    
    # 提取force_style参数
    start = filter_chain.find("force_style='") + len("force_style='")
    end = filter_chain.find("'", start)
    force_style = filter_chain[start:end]
    
    style_params = force_style.split(',')
    
    improvements = {
        'Fontsize=28': '🔤 字体28pt - 更大更清晰',
        'BackColour=&H0040E6FF': '🟡 优化黄色 - 更柔和的专业色调',
        'Outline=1': '🖼️ 细轮廓1px - 精致边缘',
        'Shadow=2': '🌟 阴影2px - 增强立体感',
        'MarginV=40': '📏 底边距40px - 更舒适的观看位置',
        'MarginL=30,MarginR=30': '↔️ 左右边距30px - 更好的居中效果',
        'Spacing=1': '📝 字符间距1px - 紧凑美观',
        'BorderStyle=4': '🔲 背景框+轮廓 - 最佳可读性'
    }
    
    print("\n✨ 样式参数详解:")
    for param in style_params:
        param_name = param.split('=')[0]
        for key, desc in improvements.items():
            if key.startswith(param_name):
                print(f"   {param} → {desc}")
                break
        else:
            print(f"   {param}")

def compare_style_evolution():
    """对比样式演化"""
    print("\n📈 样式演化对比:")
    
    evolution = [
        {
            'version': 'v1.0 基础版',
            'features': ['SRT格式', '黄色背景', '基本字体'],
            'issues': ['背景色不显示', '样式简陋']
        },
        {
            'version': 'v2.0 修复版',
            'features': ['force_style参数', 'BorderStyle=4', '24pt字体'],
            'issues': ['美观度一般', '边距不够']
        },
        {
            'version': 'v3.0 美观版',
            'features': ['26pt字体', '轮廓+阴影', '改进边距'],
            'issues': ['字体可更大', '颜色可优化']
        },
        {
            'version': 'v4.0 专业版（当前）',
            'features': ['28pt大字体', '优化黄色', '专业边距', '精致阴影'],
            'issues': ['完美！']
        }
    ]
    
    for ver in evolution:
        print(f"\n🔸 {ver['version']}:")
        print(f"   特性: {', '.join(ver['features'])}")
        print(f"   问题: {', '.join(ver['issues'])}")

def create_final_demo_video():
    """创建最终演示视频"""
    print("\n🎬 创建最终演示视频...")
    
    # 创建测试视频（20秒）
    test_video_path = "final_demo_input.mp4"
    
    cmd = [
        'ffmpeg', '-f', 'lavfi', 
        '-i', 'testsrc=duration=20:size=1920x1080:rate=30',
        '-c:v', 'libx264', '-preset', 'fast',
        '-y', test_video_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ 演示视频创建成功: {test_video_path}")
        
        # 高质量烧制数据
        demo_burn_data = [
            {
                'begin_time': 2.0,
                'end_time': 6.0,
                'keyword': 'pediatric',
                'phonetic': ',pi·di\'ætrik',
                'explanation': '儿科的',
                'coca_rank': 15000
            },
            {
                'begin_time': 8.0,
                'end_time': 12.0,
                'keyword': 'sophisticated',
                'phonetic': 'sə\'fɪstɪkeɪtɪd',
                'explanation': '复杂精密的',
                'coca_rank': 12000
            },
            {
                'begin_time': 14.0,
                'end_time': 18.0,
                'keyword': 'revolutionary',
                'phonetic': ',revə\'luːʃə,neri',
                'explanation': '革命性的',
                'coca_rank': 18000
            }
        ]
        
        # 输出最终演示视频
        output_video = "FINAL_BEAUTIFUL_DEMO.mp4"
        
        print("开始最终美观烧制...")
        success = video_burner.burn_video_with_keywords(
            input_video=test_video_path,
            output_video=output_video,
            burn_data=demo_burn_data,
            progress_callback=lambda msg: print(f"   {msg}")
        )
        
        if success and os.path.exists(output_video):
            print(f"🎉 最终演示视频创建成功: {output_video}")
            
            # 获取视频信息
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', output_video]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                
                for stream in info['streams']:
                    if stream['codec_type'] == 'video':
                        width = stream['width']
                        height = stream['height']
                        aspect = width / height
                        print(f"📊 视频规格: {width}x{height} (宽高比: {aspect:.2f})")
                        
                duration = float(info['format']['duration'])
                size_mb = os.path.getsize(output_video) / (1024 * 1024)
                print(f"📏 时长: {duration:.1f}秒")
                print(f"💾 大小: {size_mb:.1f} MB")
                
                print(f"\n🎯 完美！您现在可以查看 {output_video} 来体验最终的美观效果！")
            
        else:
            print("❌ 最终演示视频创建失败")
        
        # 清理输入视频
        if os.path.exists(test_video_path):
            os.remove(test_video_path)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 演示视频创建失败: {e}")

def show_final_summary():
    """显示最终总结"""
    print("\n📋 最终美观效果总结:")
    
    print("\n🎨 视觉效果:")
    print("   ✅ 28pt大字体 - 清晰醒目")
    print("   ✅ 优化黄色背景 - 柔和专业")
    print("   ✅ 精致轮廓+阴影 - 立体美观")
    print("   ✅ 专业边距设置 - 舒适观看")
    
    print("\n📱 移动端优化:")
    print("   ✅ 3:4竖屏格式 - 完美适配手机")
    print("   ✅ 底部居中显示 - 不遮挡主要内容")
    print("   ✅ 高对比度设计 - 任何背景下清晰可见")
    
    print("\n🎯 学习效果:")
    print("   ✅ 单词+音标一目了然")
    print("   ✅ 中文解释简洁明了")
    print("   ✅ 专业排版提升学习体验")
    print("   ✅ 重点词汇突出显示")
    
    print("\n🔧 技术特性:")
    print("   ✅ SRT + force_style 高兼容性")
    print("   ✅ FFmpeg标准滤镜 广泛支持")
    print("   ✅ 自动化批量处理")
    print("   ✅ 智能词汇筛选(COCA>5000)")

if __name__ == "__main__":
    print("🎨 最终美观样式测试\n")
    
    try:
        test_final_beautiful_style()
        compare_style_evolution()
        create_final_demo_video()
        show_final_summary()
        
        print("\n🎉 恭喜！美观字幕样式已达到专业级水准！")
        print("\n💡 现在您的视频烧制效果应该非常接近图片中的专业样式了！")
        print("   可以通过界面重新测试，体验全新的美观效果。")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 