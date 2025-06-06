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
                            headers=["ID", "名称", "文件类型", "时长(秒)", "创建时间"],
                            datatype=["number", "str", "str", "number", "str"],
                            label="媒体系列列表",
                            interactive=False
                        )
                    
                    with gr.Column(scale=1):
                        refresh_series_btn = gr.Button("🔄 刷新列表", variant="secondary")
                        selected_series_id = gr.Number(label="选择系列ID", value=None, precision=0)
                        view_subtitles_btn = gr.Button("📝 查看字幕", variant="primary")
                        delete_series_btn = gr.Button("🗑️ 删除系列", variant="stop")
            
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
                        load_keywords_btn = gr.Button("📚 加载关键词", variant="secondary")
                
                keywords_table = gr.Dataframe(
                    headers=["ID", "单词", "音标", "解释", "来源系列", "时间段"],
                    datatype=["number", "str", "str", "str", "str", "str"],
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
                    with gr.Column():
                        add_phonetic = gr.Textbox(label="音标（可选）", placeholder="如: /ˈɪntəˌnet/")
                        add_explanation = gr.Textbox(label="解释", placeholder="单词的中文解释")
                
                add_keyword_btn = gr.Button("➕ 添加关键词", variant="primary")
                add_result = gr.Textbox(label="添加结果", interactive=False)

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
                    table_data.append([
                        series['id'],
                        series['name'],
                        series.get('file_type', '未知'),
                        series.get('duration', 0) or 0,
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
                    table_data.append([
                        result['id'],
                        result['key_word'],
                        result.get('phonetic_symbol', ''),
                        result.get('explain_text', ''),
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
                    table_data.append([
                        keyword['id'],
                        keyword['key_word'],
                        keyword.get('phonetic_symbol', ''),
                        keyword.get('explain_text', ''),
                        "",  # 系列名（因为已经按系列筛选）
                        time_range
                    ])
                
                return table_data
            except Exception as e:
                LOG.error(f"加载关键词失败: {e}")
                return []

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

        def add_keyword_func(subtitle_id, keyword, phonetic, explanation):
            """添加关键词"""
            if not subtitle_id or not keyword.strip():
                return "❌ 请填写字幕ID和关键词"
            
            try:
                keyword_data = [{
                    'key_word': keyword.strip(),
                    'phonetic_symbol': phonetic.strip() if phonetic else '',
                    'explain_text': explanation.strip() if explanation else ''
                }]
                
                keyword_ids = db_manager.create_keywords(int(subtitle_id), keyword_data)
                if keyword_ids:
                    return f"✅ 成功添加关键词: {keyword} (ID: {keyword_ids[0]})"
                else:
                    return "❌ 添加失败"
            except Exception as e:
                LOG.error(f"添加关键词失败: {e}")
                return f"❌ 添加失败: {str(e)}"

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
            inputs=[add_subtitle_id, add_keyword, add_phonetic, add_explanation],
            outputs=[add_result]
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