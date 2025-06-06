#!/usr/bin/env python3
"""
数据库管理界面
提供查看和管理保存的媒体、字幕和关键词的Web界面
"""

import os
# 清除可能干扰 Gradio 启动的代理环境变量
proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
for var in proxy_vars:
    if var in os.environ:
        print(f"🧹 清除代理环境变量: {var}={os.environ[var]}")
        del os.environ[var]

import gradio as gr
import pandas as pd
from database import db_manager
from logger import LOG
from typing import List, Dict

def create_database_interface():
    """创建数据库管理界面"""
    
    with gr.Blocks(title="数据库管理", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 📊 数据库管理界面")
        
        # 统计信息面板
        with gr.Row():
            with gr.Column():
                stats_display = gr.Markdown("## 📈 数据统计\n加载中...")
        
        # 选项卡界面
        with gr.Tabs():
            # 媒体系列管理
            with gr.TabItem("🎬 媒体系列"):
                with gr.Row():
                    with gr.Column(scale=3):
                        series_table = gr.Dataframe(
                            headers=["ID", "名称", "文件类型", "时长(秒)", "烧制视频名", "烧制路径", "创建时间"],
                            datatype=["number", "str", "str", "number", "str", "str", "str"],
                            label="媒体系列列表",
                            interactive=False,
                            wrap=True
                        )
                    
                    with gr.Column(scale=1):
                        refresh_series_btn = gr.Button("🔄 刷新列表", variant="secondary")
                        selected_series_id = gr.Number(label="选择系列ID", value=None, precision=0)
                        view_subtitles_btn = gr.Button("📝 查看字幕", variant="primary")
                        delete_series_btn = gr.Button("🗑️ 删除系列", variant="stop")
                        
                        # 烧制视频信息更新
                        with gr.Group():
                            gr.Markdown("### 🎬 更新烧制视频信息")
                            update_series_id = gr.Number(label="系列ID", precision=0)
                            update_new_name = gr.Textbox(label="烧制视频名称", placeholder="例: output_with_subtitles.mp4")
                            update_new_path = gr.Textbox(label="烧制视频路径", placeholder="例: /path/to/output_video.mp4")
                            update_video_btn = gr.Button("💾 更新信息", variant="primary")
                            update_result = gr.Textbox(label="更新结果", interactive=False)
            
            # 字幕管理
            with gr.TabItem("📝 字幕管理"):
                with gr.Row():
                    series_id_input = gr.Number(label="系列ID", value=None, precision=0)
                    load_subtitles_btn = gr.Button("加载字幕", variant="primary")
                
                subtitles_table = gr.Dataframe(
                    headers=["ID", "开始时间", "结束时间", "英文文本", "中文文本"],
                    datatype=["number", "number", "number", "str", "str"],
                    label="字幕列表",
                    interactive=False,
                    wrap=True
                )
            
            # 关键词管理
            with gr.TabItem("📚 关键词库"):
                with gr.Row():
                    with gr.Column():
                        search_keyword_input = gr.Textbox(label="搜索关键词", placeholder="输入要搜索的单词...")
                        search_btn = gr.Button("🔍 搜索", variant="primary")
                    
                    with gr.Column():
                        keyword_series_id = gr.Number(label="按系列ID查看", value=None, precision=0)
                        with gr.Row():
                            load_keywords_btn = gr.Button("📚 加载关键词", variant="secondary")
                            extract_keywords_btn = gr.Button("🤖 AI提取关键词", variant="primary")
                        with gr.Row():
                            update_coca_btn = gr.Button("🔄 更新COCA", variant="secondary", size="sm")
                            coca_update_status = gr.Textbox(label="更新状态", interactive=False, placeholder="等待更新...")
                
                keywords_table = gr.Dataframe(
                    headers=["ID", "单词", "音标", "解释", "COCA排名", "频率等级", "来源系列", "时间段"],
                    datatype=["number", "str", "str", "str", "number", "str", "str", "str"],
                    label="关键词列表",
                    interactive=False,
                    wrap=True
                )
                
                # 手动添加关键词
                with gr.Row():
                    gr.Markdown("### ➕ 手动添加关键词")
                
                with gr.Row():
                    with gr.Column():
                        add_subtitle_id = gr.Number(label="字幕ID", precision=0)
                        add_keyword = gr.Textbox(label="单词")
                        add_coca = gr.Number(label="COCA排名（可选）", precision=0, placeholder="留空自动查询")
                    with gr.Column():
                        add_phonetic = gr.Textbox(label="音标（可选）", placeholder="如: /ˈɪntəˌnet/")
                        add_explanation = gr.Textbox(label="解释", placeholder="单词的中文解释")
                
                add_keyword_btn = gr.Button("➕ 添加关键词", variant="primary")
                add_result = gr.Textbox(label="添加结果", interactive=False)
                
                # AI提取关键词状态
                with gr.Row():
                    gr.Markdown("### 🤖 AI关键词提取")
                
                extract_status = gr.Textbox(label="提取状态", interactive=False, placeholder="等待开始...")
                extract_progress = gr.Textbox(label="提取进度", interactive=False)

        def update_statistics():
            """更新统计信息"""
            try:
                stats = db_manager.get_statistics()
                
                stats_text = f"""## 📈 数据统计

📁 **媒体系列**: {stats['series_count']} 个
📝 **字幕条目**: {stats['subtitle_count']} 条  
📚 **关键词数**: {stats['keyword_count']} 个
🔤 **独特单词**: {stats['unique_words']} 个
⏱️ **总时长**: {stats['total_duration']:.1f} 秒 ({stats['total_duration']/60:.1f} 分钟)
"""
                return stats_text
            except Exception as e:
                LOG.error(f"获取统计信息失败: {e}")
                return "## 📈 数据统计\n❌ 加载失败"

        def load_series_list():
            """加载媒体系列列表"""
            try:
                series_list = db_manager.get_series()
                
                if not series_list:
                    return []
                
                # 转换为表格数据
                table_data = []
                for series in series_list:
                    # 处理烧制视频信息的显示
                    new_name = series.get('new_name', '') or '未烧制'
                    new_path = series.get('new_file_path', '') or '未设置'
                    
                    # 截断过长的路径显示
                    if len(new_path) > 50:
                        new_path = new_path[:47] + '...'
                    
                    table_data.append([
                        series['id'],
                        series['name'],
                        series.get('file_type', '未知'),
                        series.get('duration', 0) or 0,
                        new_name,
                        new_path,
                        series['created_at']
                    ])
                
                return table_data
            except Exception as e:
                LOG.error(f"加载系列列表失败: {e}")
                return []

        def load_subtitles_by_series(series_id):
            """根据系列ID加载字幕"""
            if not series_id:
                return []
            
            try:
                subtitles = db_manager.get_subtitles(int(series_id))
                
                if not subtitles:
                    return []
                
                # 转换为表格数据
                table_data = []
                for subtitle in subtitles:
                    table_data.append([
                        subtitle['id'],
                        round(subtitle['begin_time'], 2),
                        round(subtitle['end_time'], 2),
                        subtitle.get('english_text', '')[:100] + ('...' if len(subtitle.get('english_text', '')) > 100 else ''),
                        subtitle.get('chinese_text', '')[:100] + ('...' if len(subtitle.get('chinese_text', '')) > 100 else '')
                    ])
                
                return table_data
            except Exception as e:
                LOG.error(f"加载字幕失败: {e}")
                return []

        def search_keywords_func(keyword):
            """搜索关键词"""
            if not keyword.strip():
                return []
            
            try:
                results = db_manager.search_keywords(keyword.strip())
                
                if not results:
                    return []
                
                # 转换为表格数据
                table_data = []
                for result in results:
                    time_range = f"{result.get('begin_time', 0):.1f}s - {result.get('end_time', 0):.1f}s"
                    coca_rank = result.get('coca', None)
                    
                    # 获取频率等级
                    if coca_rank:
                        from coca_lookup import coca_lookup
                        frequency_level = coca_lookup.get_frequency_level(coca_rank)
                    else:
                        frequency_level = "未知"
                    
                    table_data.append([
                        result['id'],
                        result['key_word'],
                        result.get('phonetic_symbol', ''),
                        result.get('explain_text', ''),
                        coca_rank or '',
                        frequency_level,
                        result.get('series_name', ''),
                        time_range
                    ])
                
                return table_data
            except Exception as e:
                LOG.error(f"搜索关键词失败: {e}")
                return []

        def load_keywords_by_series(series_id):
            """根据系列ID加载关键词"""
            if not series_id:
                return []
            
            try:
                keywords = db_manager.get_keywords(series_id=int(series_id))
                
                if not keywords:
                    return []
                
                # 转换为表格数据
                table_data = []
                for keyword in keywords:
                    time_range = f"{keyword.get('begin_time', 0):.1f}s - {keyword.get('end_time', 0):.1f}s"
                    coca_rank = keyword.get('coca', None)
                    
                    # 获取频率等级
                    if coca_rank:
                        from coca_lookup import coca_lookup
                        frequency_level = coca_lookup.get_frequency_level(coca_rank)
                    else:
                        frequency_level = "未知"
                    
                    table_data.append([
                        keyword['id'],
                        keyword['key_word'],
                        keyword.get('phonetic_symbol', ''),
                        keyword.get('explain_text', ''),
                        coca_rank or '',
                        frequency_level,
                        "",  # 系列名（因为已经按系列筛选）
                        time_range
                    ])
                
                return table_data
            except Exception as e:
                LOG.error(f"加载关键词失败: {e}")
                return []

        def update_video_info_func(series_id, new_name, new_path):
            """更新系列的烧制视频信息"""
            if not series_id:
                return "❌ 请输入有效的系列ID"
            
            if not new_name.strip() and not new_path.strip():
                return "❌ 请至少输入视频名称或路径中的一个"
            
            try:
                success = db_manager.update_series_video_info(
                    int(series_id),
                    new_name=new_name.strip() if new_name.strip() else None,
                    new_file_path=new_path.strip() if new_path.strip() else None
                )
                
                if success:
                    return f"✅ 系列 {series_id} 的烧制视频信息已更新"
                else:
                    return f"❌ 更新失败，请检查系列ID是否存在"
                    
            except Exception as e:
                LOG.error(f"更新烧制视频信息失败: {e}")
                return f"❌ 更新失败: {str(e)}"

        def delete_series_func(series_id):
            """删除系列"""
            if not series_id:
                return "请输入有效的系列ID"
            
            try:
                success = db_manager.delete_series(int(series_id))
                if success:
                    return f"✅ 成功删除系列 {series_id}"
                else:
                    return f"❌ 删除失败，系列 {series_id} 不存在"
            except Exception as e:
                LOG.error(f"删除系列失败: {e}")
                return f"❌ 删除失败: {str(e)}"

        def add_keyword_func(subtitle_id, keyword, coca_rank, phonetic, explanation):
            """添加关键词"""
            if not subtitle_id or not keyword.strip():
                return "❌ 请填写字幕ID和关键词"
            
            try:
                # 如果未提供COCA排名，自动从数据库查询
                if not coca_rank:
                    from coca_lookup import coca_lookup
                    coca_rank = coca_lookup.get_frequency_rank(keyword.strip())
                
                keyword_data = [{
                    'key_word': keyword.strip(),
                    'phonetic_symbol': phonetic.strip() if phonetic else '',
                    'explain_text': explanation.strip() if explanation else '',
                    'coca': int(coca_rank) if coca_rank else None
                }]
                
                keyword_ids = db_manager.create_keywords(int(subtitle_id), keyword_data)
                if keyword_ids:
                    coca_info = f" (COCA: {coca_rank})" if coca_rank else ""
                    return f"✅ 成功添加关键词: {keyword}{coca_info} (ID: {keyword_ids[0]})"
                else:
                    return "❌ 添加失败"
            except Exception as e:
                LOG.error(f"添加关键词失败: {e}")
                return f"❌ 添加失败: {str(e)}"

        def update_coca_for_series(series_id):
            """更新指定系列的COCA信息"""
            if not series_id:
                yield "❌ 请输入有效的系列ID"
                return
            
            try:
                series_id = int(series_id)
                
                # 检查系列是否存在
                series_list = db_manager.get_series()
                target_series = None
                for series in series_list:
                    if series['id'] == series_id:
                        target_series = series
                        break
                
                if not target_series:
                    yield "❌ 找不到指定的系列"
                    return
                
                yield f"🔍 开始更新系列 '{target_series['name']}' 的COCA信息..."
                
                # 获取该系列的所有关键词
                keywords = db_manager.get_keywords(series_id=series_id)
                if not keywords:
                    yield "❌ 该系列没有关键词数据"
                    return
                
                yield f"📚 找到 {len(keywords)} 个关键词，开始更新COCA排名..."
                
                from coca_lookup import coca_lookup
                import sqlite3
                
                updated_count = 0
                skipped_count = 0
                failed_count = 0
                
                with sqlite3.connect(db_manager.db_path) as conn:
                    cursor = conn.cursor()
                    
                    for i, keyword in enumerate(keywords):
                        try:
                            word = keyword['key_word']
                            is_phrase = ' ' in word  # 判断是否为短语
                            
                            # 检查是否已有COCA信息
                            if keyword.get('coca') is not None and not is_phrase:
                                # 单词有COCA排名就跳过，但短语需要强制更新
                                skipped_count += 1
                                progress = f"处理中: {i+1}/{len(keywords)} (已更新: {updated_count}, 跳过: {skipped_count}, 失败: {failed_count})"
                                yield f"⏭️ '{word}' 已有COCA排名 {keyword['coca']}，跳过\n{progress}"
                                continue
                            elif keyword.get('coca') is not None and is_phrase:
                                # 短语需要强制更新到20000+
                                progress = f"处理中: {i+1}/{len(keywords)} (已更新: {updated_count}, 跳过: {skipped_count}, 失败: {failed_count})"
                                yield f"🔄 '{word}' 是短语，强制更新COCA排名（旧值: {keyword['coca']}）\n{progress}"
                            
                            # 查询COCA排名
                            coca_rank = coca_lookup.get_frequency_rank(word)
                            
                            if coca_rank:
                                # 更新数据库
                                cursor.execute(
                                    "UPDATE t_keywords SET coca = ? WHERE id = ?",
                                    (coca_rank, keyword['id'])
                                )
                                updated_count += 1
                                
                                freq_level = coca_lookup.get_frequency_level(coca_rank)
                                progress = f"处理中: {i+1}/{len(keywords)} (已更新: {updated_count}, 跳过: {skipped_count}, 失败: {failed_count})"
                                update_type = "强制更新" if is_phrase and keyword.get('coca') is not None else "新增"
                                yield f"✅ '{word}' → COCA排名: {coca_rank} ({freq_level}) [{update_type}]\n{progress}"
                            else:
                                failed_count += 1
                                progress = f"处理中: {i+1}/{len(keywords)} (已更新: {updated_count}, 跳过: {skipped_count}, 失败: {failed_count})"
                                yield f"⚠️ '{word}' 未找到COCA排名\n{progress}"
                            
                        except Exception as e:
                            failed_count += 1
                            progress = f"处理中: {i+1}/{len(keywords)} (已更新: {updated_count}, 跳过: {skipped_count}, 失败: {failed_count})"
                            yield f"❌ '{word}' 更新失败: {str(e)}\n{progress}"
                    
                    conn.commit()
                
                # 最终报告
                final_result = f"""🎉 COCA更新完成！

📊 **更新统计**:
- ✅ 成功更新: {updated_count} 个
- ⏭️ 已有排名: {skipped_count} 个  
- ❌ 查询失败: {failed_count} 个
- 📚 总计处理: {len(keywords)} 个关键词

💡 提示: 刷新关键词列表查看更新结果"""

                yield final_result
                
            except Exception as e:
                LOG.error(f"更新COCA信息失败: {e}")
                yield f"❌ 更新失败: {str(e)}"

        def extract_keywords_ai(series_id):
            """使用AI提取关键词"""
            if not series_id:
                return "❌ 请输入有效的系列ID", "❌ 请输入系列ID"
            
            try:
                # 导入关键词提取器
                from keyword_extractor import keyword_extractor
                
                # 获取系列字幕
                subtitles = db_manager.get_subtitles(int(series_id))
                if not subtitles:
                    return "❌ 该系列没有字幕数据", "未找到字幕"
                
                # 过滤有英文文本的字幕
                english_subtitles = [sub for sub in subtitles if sub.get('english_text', '').strip()]
                if not english_subtitles:
                    return "❌ 该系列没有英文字幕文本", "没有英文文本"
                
                yield f"🔄 开始AI分析...", f"准备分析 {len(english_subtitles)} 条字幕"
                
                # 使用批量提取模式（更高效）
                extracted_keywords = keyword_extractor.batch_extract_with_context(
                    english_subtitles, batch_size=3
                )
                
                if not extracted_keywords:
                    yield "⚠️ AI未提取到关键词", "分析完成，但未找到重点词汇"
                    return
                
                yield f"💾 保存到数据库...", f"提取到 {len(extracted_keywords)} 个关键词"
                
                # 分组保存到数据库
                saved_count = 0
                for keyword in extracted_keywords:
                    subtitle_id = keyword['subtitle_id']
                    if subtitle_id:
                        keyword_data = [{
                            'key_word': keyword['key_word'],
                            'phonetic_symbol': keyword.get('phonetic_symbol', ''),
                            'explain_text': keyword.get('explain_text', '')
                        }]
                        
                        try:
                            db_manager.create_keywords(subtitle_id, keyword_data)
                            saved_count += 1
                        except Exception as e:
                            LOG.error(f"保存关键词失败: {e}")
                
                yield f"✅ AI提取完成！", f"成功保存 {saved_count} 个关键词到数据库"
                
            except Exception as e:
                LOG.error(f"AI提取关键词失败: {e}")
                yield f"❌ 提取失败: {str(e)}", "发生错误"

        # 绑定事件
        interface.load(
            fn=lambda: (update_statistics(), load_series_list()),
            outputs=[stats_display, series_table]
        )
        
        refresh_series_btn.click(
            fn=lambda: (update_statistics(), load_series_list()),
            outputs=[stats_display, series_table]
        )
        
        view_subtitles_btn.click(
            fn=load_subtitles_by_series,
            inputs=[selected_series_id],
            outputs=[subtitles_table]
        )
        
        load_subtitles_btn.click(
            fn=load_subtitles_by_series,
            inputs=[series_id_input],
            outputs=[subtitles_table]
        )
        
        search_btn.click(
            fn=search_keywords_func,
            inputs=[search_keyword_input],
            outputs=[keywords_table]
        )
        
        load_keywords_btn.click(
            fn=load_keywords_by_series,
            inputs=[keyword_series_id],
            outputs=[keywords_table]
        )
        
        delete_series_btn.click(
            fn=delete_series_func,
            inputs=[selected_series_id],
            outputs=[gr.Textbox(label="删除结果", interactive=False)]
        )
        
        add_keyword_btn.click(
            fn=add_keyword_func,
            inputs=[add_subtitle_id, add_keyword, add_coca, add_phonetic, add_explanation],
            outputs=[add_result]
        )
        
        extract_keywords_btn.click(
            fn=extract_keywords_ai,
            inputs=[keyword_series_id],
            outputs=[extract_status, extract_progress]
        )
        
        update_coca_btn.click(
            fn=update_coca_for_series,
            inputs=[keyword_series_id],
            outputs=[coca_update_status]
        )
        
        update_video_btn.click(
            fn=update_video_info_func,
            inputs=[update_series_id, update_new_name, update_new_path],
            outputs=[update_result]
        )
    
    return interface

if __name__ == "__main__":
    LOG.info("🚀 启动数据库管理界面...")
    interface = create_database_interface()
    interface.queue().launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True
    ) 