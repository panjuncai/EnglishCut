#!/usr/bin/env python3
"""
测试视频烧制功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from video_subtitle_burner import video_burner
from database import db_manager
from logger import LOG

def test_burn_preview():
    """测试烧制预览功能"""
    print("🔍 测试烧制预览功能...")
    
    # 获取第一个系列
    series_list = db_manager.get_series()
    if not series_list:
        print("❌ 没有找到任何系列")
        return
    
    series_id = series_list[0]['id']
    print(f"📹 使用系列ID: {series_id}")
    
    # 获取预览信息
    preview = video_burner.get_burn_preview(series_id)
    
    print("\n📊 预览结果:")
    print(f"- 重点单词数: {preview['total_keywords']}")
    print(f"- 烧制时长: {preview['total_duration']}秒")
    print(f"- 预估大小: {preview['estimated_file_size']}")
    print(f"- 词频分布: {preview['coca_distribution']}")
    
    print("\n🔤 示例单词:")
    for i, kw in enumerate(preview['sample_keywords'][:3], 1):
        print(f"{i}. {kw['keyword']} {kw['phonetic']} - {kw['explanation']} (COCA: {kw['coca_rank']})")

def test_keyword_selection():
    """测试关键词选择逻辑"""
    print("\n🧠 测试关键词选择逻辑...")
    
    # 模拟多个关键词
    test_keywords = [
        {'key_word': 'computer', 'coca': 10000, 'phonetic_symbol': '/kəmˈpjuːtər/', 'explain_text': '计算机'},
        {'key_word': 'technology', 'coca': 15000, 'phonetic_symbol': '/tekˈnɒlədʒi/', 'explain_text': '技术'},
        {'key_word': 'AI', 'coca': 20000, 'phonetic_symbol': '/ˌeɪ ˈaɪ/', 'explain_text': '人工智能'}
    ]
    
    selected = video_burner._select_most_important_keyword(test_keywords)
    print(f"选择的关键词: {selected['key_word']} (COCA: {selected['coca']})")
    
    # 测试相同COCA排名的情况
    test_keywords_same_coca = [
        {'key_word': 'artificial intelligence', 'coca': 20000, 'phonetic_symbol': '/ˌɑːrtɪˈfɪʃl ɪnˈtelɪdʒəns/', 'explain_text': '人工智能'},
        {'key_word': 'AI', 'coca': 20000, 'phonetic_symbol': '/ˌeɪ ˈaɪ/', 'explain_text': '人工智能'}
    ]
    
    selected_same = video_burner._select_most_important_keyword(test_keywords_same_coca)
    print(f"相同COCA排名时选择: {selected_same['key_word']} (长度更短)")

def test_subtitle_generation():
    """测试字幕文件生成"""
    print("\n📝 测试字幕文件生成...")
    
    # 模拟烧制数据
    test_burn_data = [
        {
            'begin_time': 0.0,
            'end_time': 2.5,
            'keyword': 'technology',
            'phonetic': '/tekˈnɒlədʒi/',
            'explanation': '技术',
            'coca_rank': 15000
        },
        {
            'begin_time': 5.0,
            'end_time': 7.2,
            'keyword': 'artificial intelligence',
            'phonetic': '/ˌɑːrtɪˈfɪʃl ɪnˈtelɪdʒəns/',
            'explanation': '人工智能',
            'coca_rank': 20000
        }
    ]
    
    # 创建临时字幕文件
    subtitle_path = "test_keywords.srt"
    video_burner.create_subtitle_file(test_burn_data, subtitle_path)
    
    # 读取并显示内容
    if os.path.exists(subtitle_path):
        print(f"✅ 字幕文件创建成功: {subtitle_path}")
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("字幕内容:")
            print(content)
        
        # 清理
        os.remove(subtitle_path)
        print("🧹 临时文件已清理")
    else:
        print("❌ 字幕文件创建失败")

def test_database_keywords():
    """测试数据库中的关键词数据"""
    print("\n🗄️ 测试数据库关键词数据...")
    
    # 获取第一个系列
    series_list = db_manager.get_series()
    if not series_list:
        print("❌ 没有找到任何系列")
        return
    
    series_id = series_list[0]['id']
    print(f"📹 检查系列ID: {series_id}")
    
    # 获取关键词
    keywords = db_manager.get_keywords(series_id=series_id)
    print(f"📚 总关键词数: {len(keywords)}")
    
    # 筛选符合烧制条件的关键词
    eligible_keywords = []
    for keyword in keywords:
        coca_rank = keyword.get('coca')
        if coca_rank and coca_rank > 5000:
            eligible_keywords.append(keyword)
    
    print(f"🎯 符合烧制条件的关键词数 (COCA > 5000): {len(eligible_keywords)}")
    
    # 显示前5个符合条件的关键词
    print("\n前5个符合条件的关键词:")
    for i, kw in enumerate(eligible_keywords[:5], 1):
        print(f"{i}. {kw['key_word']} (COCA: {kw.get('coca')}) - {kw.get('explain_text', '')}")

if __name__ == "__main__":
    print("🎬 视频烧制功能测试\n")
    
    try:
        test_database_keywords()
        test_keyword_selection()
        test_subtitle_generation()
        test_burn_preview()
        
        print("\n✅ 所有测试完成！")
        print("\n📋 接下来可以尝试:")
        print("1. 在界面中选择一个系列ID")
        print("2. 点击'预览烧制信息'查看统计")
        print("3. 设置输出目录并点击'开始烧制'")
        print("4. 等待FFmpeg处理完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 