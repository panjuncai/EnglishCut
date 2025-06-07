#!/usr/bin/env python3
"""
测试Gradio下拉框组件的行为
"""

import sys
import os
import gradio as gr
sys.path.append('.')

from src.database import db_manager
from src.logger import LOG

def create_dropdown_test():
    """创建测试Gradio下拉框的小界面"""
    
    # 加载视频列表
    def load_video_list():
        """加载视频列表"""
        try:
            # 从数据库获取所有视频列表
            series_list = db_manager.get_series()
            
            if not series_list:
                print("⚠️ 数据库中没有系列数据")
                return []
            
            print(f"查询到 {len(series_list)} 条系列数据")
            
            # 以id-name的形式返回视频列表
            return [f"{series['id']}-{series['name']}" for series in series_list]
        except Exception as e:
            print(f"❌ 加载视频列表失败: {e}")
            return []
    
    # 处理下拉框选择
    def handle_selection(selection):
        """处理下拉框选择"""
        print(f"选择的值: {selection}, 类型: {type(selection)}")
        
        if not selection:
            return "请选择一个视频"
        
        try:
            # 从id-name格式中提取ID
            video_id = int(selection.split('-')[0])
            
            # 获取视频信息
            series_list = db_manager.get_series(video_id)
            if not series_list:
                return f"未找到ID为 {video_id} 的视频"
            
            series = series_list[0]
            
            return f"""
选择的视频信息:
- ID: {series['id']}
- 名称: {series['name']}
- 路径: {series['file_path']}
- 9:16视频: {series.get('new_name', '未设置')}
- 9:16路径: {series.get('new_file_path', '未设置')}
"""
        except Exception as e:
            return f"处理选择时发生错误: {e}"
    
    # 创建简单的界面
    with gr.Blocks(title="测试下拉框") as demo:
        gr.Markdown("# 测试Gradio下拉框组件")
        
        # 加载视频列表
        options = load_video_list()
        print(f"加载了 {len(options)} 个选项")
        
        # 创建下拉框
        dropdown = gr.Dropdown(
            label="选择视频",
            choices=options,
            value=None,
            interactive=True
        )
        
        # 显示选择结果
        result = gr.Markdown("请从上方下拉框中选择视频...")
        
        # 更新按钮
        refresh_btn = gr.Button("刷新选项")
        
        # 事件绑定
        dropdown.change(
            handle_selection,
            inputs=[dropdown],
            outputs=[result]
        )
        
        refresh_btn.click(
            load_video_list,
            inputs=[],
            outputs=[dropdown]
        )
    
    return demo

if __name__ == "__main__":
    LOG.info("🚀 启动测试Gradio下拉框的界面...")
    
    # 创建并启动界面
    demo = create_dropdown_test()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True
    ) 