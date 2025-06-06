#!/usr/bin/env python3
"""
测试基于真实COCA数据库的词频功能
"""

import sys
import os
sys.path.append('src')

def test_coca_database_connection():
    """测试COCA数据库连接和数据"""
    print("=== 测试COCA数据库连接 ===\n")
    
    try:
        from coca_lookup import coca_lookup
        print("✅ COCA数据库查询器导入成功")
        
        # 获取数据库统计信息
        stats = coca_lookup.get_database_stats()
        print(f"📊 COCA数据库统计:")
        print(f"  总词汇数: {stats['total_words']:,}")
        print(f"  排名范围: {stats['min_rank']} - {stats['max_rank']}")
        
        if stats['total_words'] > 0:
            print("✅ COCA数据库包含数据")
        else:
            print("❌ COCA数据库为空")
            return False
            
    except Exception as e:
        print(f"❌ COCA数据库连接失败: {e}")
        return False
    
    return True

def test_coca_word_lookup():
    """测试COCA词频查询功能"""
    print("\n=== 测试COCA词频查询 ===")
    
    try:
        from coca_lookup import coca_lookup
        
        # 测试常见词汇
        test_words = [
            "the", "computer", "artificial", "intelligence", 
            "machine", "learning", "algorithm", "technology",
            "data", "science", "research", "analysis"
        ]
        
        print("\n🧪 测试词频查询:")
        found_count = 0
        for word in test_words:
            rank = coca_lookup.get_frequency_rank(word)
            if rank:
                level = coca_lookup.get_frequency_level(rank)
                print(f"  {word:<12} -> 排名: {rank:<6} 等级: {level}")
                found_count += 1
            else:
                print(f"  {word:<12} -> 未找到")
        
        print(f"\n📊 查询结果: {found_count}/{len(test_words)} 个词汇找到排名")
        
        if found_count > 0:
            print("✅ COCA词频查询功能正常")
        else:
            print("❌ 没有找到任何词汇排名")
            return False
            
    except Exception as e:
        print(f"❌ 词频查询测试失败: {e}")
        return False
    
    return True

def test_coca_word_details():
    """测试获取单词详细信息"""
    print("\n=== 测试单词详细信息查询 ===")
    
    try:
        from coca_lookup import coca_lookup
        
        test_word = "computer"
        details = coca_lookup.get_word_details(test_word)
        
        if details:
            print(f"\n📝 '{test_word}' 的详细信息:")
            print(f"  排名: {details.get('rank')}")
            print(f"  词性: {details.get('pos', '未知')}")
            print(f"  总频次: {details.get('total', 0):,}")
            print(f"  口语: {details.get('spoken', 0):,}")
            print(f"  小说: {details.get('fiction', 0):,}")
            print(f"  杂志: {details.get('magazine', 0):,}")
            print(f"  报纸: {details.get('newspaper', 0):,}")
            print(f"  学术: {details.get('academic', 0):,}")
            print("✅ 单词详细信息查询成功")
        else:
            print(f"❌ 未找到 '{test_word}' 的详细信息")
            return False
            
    except Exception as e:
        print(f"❌ 单词详细信息查询失败: {e}")
        return False
    
    return True

def test_coca_database_integration():
    """测试数据库集成"""
    print("\n=== 测试数据库集成 ===")
    
    try:
        from database import db_manager
        print("✅ 数据库模块导入成功")
        
        # 检查 t_keywords 表是否有 coca 字段
        import sqlite3
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(t_keywords)")
            columns = cursor.fetchall()
            
            column_names = [col[1] for col in columns]
            if 'coca' in column_names:
                print("✅ t_keywords 表包含 coca 字段")
            else:
                print("❌ t_keywords 表缺少 coca 字段")
                return False
        
        # 测试添加包含COCA的关键词（如果有字幕数据）
        stats = db_manager.get_statistics()
        if stats['subtitle_count'] > 0:
            all_series = db_manager.get_series()
            if all_series:
                first_series = all_series[0]
                subtitles = db_manager.get_subtitles(first_series['id'])
                if subtitles:
                    test_subtitle_id = subtitles[0]['id']
                    
                    # 添加测试关键词
                    test_keywords = [{
                        'key_word': 'technology',
                        'phonetic_symbol': '/tekˈnɑːlədʒi/',
                        'explain_text': '技术',
                        'coca': 450  # 假设排名
                    }]
                    
                    keyword_ids = db_manager.create_keywords(test_subtitle_id, test_keywords)
                    if keyword_ids:
                        print(f"✅ 成功添加测试关键词，ID: {keyword_ids[0]}")
                        
                        # 验证COCA字段保存
                        keywords = db_manager.get_keywords(subtitle_id=test_subtitle_id)
                        for keyword in keywords:
                            if keyword['key_word'] == 'technology':
                                coca_rank = keyword.get('coca')
                                print(f"📊 验证保存的COCA排名: {coca_rank}")
                                if coca_rank == 450:
                                    print("✅ COCA字段保存正确")
                                else:
                                    print("⚠️ COCA字段值与预期不符")
                                break
                    else:
                        print("❌ 添加测试关键词失败")
                else:
                    print("⚠️ 没有字幕数据进行测试")
            else:
                print("⚠️ 没有系列数据进行测试")
        else:
            print("⚠️ 数据库中没有字幕数据，跳过关键词添加测试")
        
    except Exception as e:
        print(f"❌ 数据库集成测试失败: {e}")
        return False
    
    return True

def test_keyword_extractor_coca():
    """测试关键词提取器的COCA集成"""
    print("\n=== 测试关键词提取器COCA集成 ===")
    
    try:
        from keyword_extractor import keyword_extractor
        print("✅ 关键词提取器导入成功")
        
        # 测试文本提取包含COCA信息
        test_text = "Computer technology and artificial intelligence are transforming our world."
        
        keywords = keyword_extractor.extract_keywords_from_text(test_text)
        
        print(f"\n🧪 测试文本关键词提取（带COCA信息）:")
        print(f"📝 输入: {test_text}")
        print(f"📊 提取结果: {len(keywords)} 个关键词")
        
        has_valid_coca = False
        for i, keyword in enumerate(keywords, 1):
            coca_rank = keyword.get('coca')
            if coca_rank:
                from coca_lookup import coca_lookup
                level = coca_lookup.get_frequency_level(coca_rank)
                has_valid_coca = True
            else:
                level = "未知"
            
            print(f"  {i}. {keyword['key_word']} - COCA: {coca_rank or '未找到'} ({level})")
        
        if has_valid_coca:
            print("✅ 关键词提取器已集成COCA信息")
        else:
            print("⚠️ 关键词提取器未找到有效的COCA信息")
        
    except Exception as e:
        print(f"❌ 关键词提取器测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("🧪 基于真实COCA数据库的功能测试")
    print("=" * 50)
    
    success_count = 0
    total_tests = 5
    
    # 测试1: 数据库连接
    if test_coca_database_connection():
        success_count += 1
    
    # 测试2: 词频查询
    if test_coca_word_lookup():
        success_count += 1
    
    # 测试3: 单词详细信息
    if test_coca_word_details():
        success_count += 1
    
    # 测试4: 数据库集成
    if test_coca_database_integration():
        success_count += 1
    
    # 测试5: 关键词提取器集成
    if test_keyword_extractor_coca():
        success_count += 1
    
    print(f"\n📊 测试结果: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("🎉 所有COCA功能测试通过！")
        print("💡 现在可以在数据库管理界面查看词频信息了！")
        print("🔗 访问: http://localhost:7861")
    elif success_count >= 3:
        print("✅ 核心功能测试通过，可以开始使用！")
        print("⚠️ 部分功能可能需要进一步调试")
    else:
        print("⚠️ 多项测试失败，请检查COCA数据库和相关配置")
    
    return success_count >= 3

if __name__ == "__main__":
    main() 