#!/usr/bin/env python3
"""
Gradio服务器
提供分步式视频处理工作流界面
"""

import os
import sys
# 添加当前目录到系统路径，以支持模块导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 设置环境变量以解决 OpenMP 冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# 清除可能干扰 Gradio 启动的代理环境变量
proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
for var in proxy_vars:
    if var in os.environ:
        print(f"🧹 清除代理环境变量: {var}={os.environ[var]}")
        del os.environ[var]

import gradio as gr
from logger import LOG
from media_processor import process_media_file, get_media_formats_info
from file_detector import FileType, get_file_type, validate_file
from database import db_manager
import pandas as pd

# 初始化视频列表
def load_video_list():
    """加载视频列表"""
    try:
        # 从数据库获取所有视频列表
        series_list = db_manager.get_series()
        
        if not series_list:
            LOG.warning("⚠️ 数据库中没有系列数据")
            # 返回空列表
            return []
        
        # LOG.info(f"查询到 {len(series_list)} 条系列数据")
        
        # 准备下拉选项 - Gradio需要这种格式的选项列表
        options = []
        for series in series_list:
            # 检查路径是否存在
            path = series.get('new_file_path', '')
            file_exists = path and os.path.exists(path)
            
            if file_exists:
                # 如果文件存在，包含完整信息
                option = f"{series['id']}-{series['name']}-{path}"
                options.append(option)
                # LOG.info(f"添加有效视频选项: ID={series['id']}, 名称={series['name']}, 路径={path}")
            else:
                # 如果文件不存在，只包含ID和名称
                option = f"{series['id']}-{series['name']}"
                options.append(option)
                # LOG.info(f"添加ID-名称选项(无路径): ID={series['id']}, 名称={series['name']}")
        
        # LOG.info(f"生成了 {len(options)} 个下拉选项")
        
        # 为调试输出前5个选项
        # for i, option in enumerate(options[:5]):
        #     LOG.info(f"选项 {i+1}: {option}")
        
        # 返回选项列表
        return options
    except Exception as e:
        LOG.error(f"加载视频列表失败: {e}")
        import traceback
        LOG.error(traceback.format_exc())
        # 返回空列表
        return []

# 定义加载带字幕视频列表函数
def load_subtitle_videos():
    """加载已有字幕的视频列表"""
    try:
        # 从数据库获取所有视频列表
        series_list = db_manager.get_series()
        
        if not series_list:
            LOG.warning("⚠️ 数据库中没有系列数据")
            return []
        
        # LOG.info(f"实时加载字幕视频列表，查询到 {len(series_list)} 条系列数据")
        
        # 准备下拉选项
        options = []
        for series in series_list:
            # 检查是否有字幕
            subtitles = db_manager.get_subtitles(series['id'])
            if subtitles:
                option_text = f"{series['id']}-{series['name']} (字幕数: {len(subtitles)})"
                options.append(option_text)
                # LOG.info(f"添加带字幕的选项: {option_text}")
        
        # LOG.info(f"生成了 {len(options)} 个带字幕的下拉选项")
        
        # 如果没有带字幕的视频，返回所有视频
        if not options:
            # LOG.warning("⚠️ 没有找到带字幕的视频，返回所有视频")
            # 使用相同的处理逻辑，检查文件是否存在
            for series in series_list:
                path = series.get('new_file_path', '')
                file_exists = path and os.path.exists(path)
                
                if file_exists:
                    option = f"{series['id']}-{series['name']}-{path}"
                    options.append(option)
                else:
                    option = f"{series['id']}-{series['name']}"
                    options.append(option)
            
            # LOG.info(f"返回全部视频选项 ({len(options)}个)")
        
        return options
    except Exception as e:
        LOG.error(f"加载视频字幕列表失败: {e}")
        import traceback
        LOG.error(traceback.format_exc())
        return []

# 获取初始视频列表
video_list = load_video_list()
subtitle_videos = load_subtitle_videos()

LOG.info(f"初始视频列表: {video_list}")
LOG.info(f"初始字幕视频列表: {subtitle_videos}")

def create_main_interface():
    """创建主界面"""
    
    # 获取支持的格式信息
    formats_info = get_media_formats_info()
    
    # 创建必要的目录
    for directory in ["input", "output"]:
        os.makedirs(directory, exist_ok=True)
    
    # 初始化视频列表
    video_list = load_video_list()
    subtitle_videos = load_subtitle_videos()

    # LOG.info(f"初始视频列表: {video_list}")
    # LOG.info(f"初始字幕视频列表: {subtitle_videos}")
    
    # 自定义CSS样式
    custom_css = """
    #burn_preview_panel {
        height: 500px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        background-color: #f9f9f9;
    }
    
    #burn_progress_panel {
        height: 500px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background-color: #f7f7f7;
        font-family: monospace;
    }
    
    #burn_result_panel {
        height: 500px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        background-color: #f5f5f5;
    }
    
    /* 美化烧制按钮 */
    .burn-button {
        font-weight: bold !important;
        font-size: 1.1em !important;
    }
    """

    with gr.Blocks(title="视频处理工作流", theme=gr.themes.Soft(), css=custom_css) as interface:
        gr.Markdown("# 🎬 视频处理工作流")
        
        # 全局状态显示
        status_md = gr.Markdown("## ℹ️ 系统状态\n系统已就绪，请开始工作流程")
        
        # 添加调试显示
        # debug_md = gr.Markdown(f"## 🔍 调试信息\n- 视频列表: {len(video_list)}个\n- 字幕视频: {len(subtitle_videos)}个")
        
        with gr.Tabs() as tabs:
            # 步骤1: 上传文件并9:16裁剪
            with gr.TabItem("📤 步骤1: 上传视频") as tab1:
                with gr.Row():
                    with gr.Column(scale=2):
                        # 文件上传
                        file_input = gr.File(
                            label="📁 上传视频文件",
                            file_types=formats_info['video_formats'],
                            type="filepath"
                        )
                        
                        upload_button = gr.Button(
                            "🚀 上传并处理",
                            variant="primary",
                            size="lg"
                        )
                    
                    with gr.Column(scale=1):
                        # 文件信息显示
                        file_info = gr.Markdown("## 📋 文件信息\n暂未选择文件")
                
                with gr.Row():
                    upload_result = gr.Markdown("### 处理结果\n等待上传...")
            
            # 步骤2: 字幕生成或上传
            with gr.TabItem("🔤 步骤2: 字幕处理") as tab2:
                
                with gr.Tabs() as subtitle_tabs:
                    # 字幕生成选项卡
                    with gr.TabItem("🎙️ 生成字幕"):
                        with gr.Row():
                            with gr.Column(scale=3):
                                with gr.Row():
                                    # 选择视频下拉框
                                    video_dropdown = gr.Dropdown(
                                        label="📋 选择已上传的视频",
                                        choices=video_list,  # 直接使用初始化好的列表
                                        value=None,
                                        interactive=True
                                    )   
                                
                                with gr.Row():
                                    # 字幕选项
                                    translation_checkbox = gr.Checkbox(
                                        label="🌐 启用中文翻译",
                                        value=True,
                                    )
                                    generate_button = gr.Button(
                                        "🎬 生成字幕",
                                        variant="primary",
                                        size="lg"
                                    )
                                    # 添加刷新按钮
                                    refresh_videos_btn = gr.Button(
                                        "🔄 刷新列表",
                                        variant="secondary",
                                        size="lg"
                                    )
                        
                        with gr.Row():
                            with gr.Column():
                                result_text = gr.Textbox(
                                    label="📄 识别结果",
                                    lines=6,
                                    placeholder="处理完成后这里将显示识别的文本内容..."
                                )
                            
                            with gr.Column():
                                translation_text = gr.Textbox(
                                    label="🌐 翻译结果",
                                    lines=6,
                                    placeholder="启用翻译后这里将显示中文翻译..."
                                )
                        
                        # 字幕内容预览
                        with gr.Row():
                            with gr.Column():
                                subtitle_preview = gr.Textbox(
                                    label="🎬 字幕预览",
                                    lines=8,
                                    placeholder="生成的字幕内容将在这里预览..."
                                )
                        
                        with gr.Row():
                            subtitle_gen_result = gr.Markdown("### 处理结果\n等待生成...")
                    
                    # 上传字幕选项卡
                    with gr.TabItem("📑 上传字幕"):
                        with gr.Row():
                            with gr.Column(scale=3):
                                with gr.Row():
                                    # 选择视频
                                    video_dropdown_upload = gr.Dropdown(
                                        label="📋 选择视频",
                                        choices=video_list,  # 直接使用初始化好的列表
                                        value=None,
                                        interactive=True
                                    )
                                    
                                    # 添加刷新按钮
                                    refresh_videos_upload_btn = gr.Button(
                                        "🔄 刷新列表",
                                        variant="secondary",
                                        size="sm"
                                    )
                                
                                with gr.Row():
                                    # 上传字幕文件
                                    subtitle_file_input = gr.File(
                                        label="📝 上传SRT字幕文件",
                                        file_types=[".srt"],
                                        type="filepath"
                                    )
                                
                                with gr.Row():
                                    subtitle_upload_btn = gr.Button(
                                        "📤 上传字幕",
                                        variant="primary",
                                        size="lg"
                                    )
                        
                        with gr.Row():
                            subtitle_upload_result = gr.Markdown("### 上传结果\n等待上传...")
            
            # 步骤3: 关键词AI筛查提取
            with gr.TabItem("🔑 步骤3: 关键词提取") as tab3:
                
                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Row():
                            # 选择带字幕的视频
                            subtitle_video_dropdown = gr.Dropdown(
                                label="📋 选择已有字幕的视频",
                                choices=subtitle_videos,  # 直接使用初始化好的字幕视频列表
                                value=None,
                                interactive=True
                            )
                            
                            
                        
                        with gr.Row():
                            # 提取选项
                            coca_checkbox = gr.Checkbox(
                                label="📚 自动更新COCA频率",
                                value=True,
                            )
                            extract_button = gr.Button(
                                "🔍 提取关键词",
                                variant="secondary"
                            )
                            # 添加查询按钮
                            query_keywords_btn = gr.Button(
                                "🔎 查询关键词",
                                variant="primary"
                            )
                            # 添加刷新按钮
                            refresh_subtitle_videos_btn = gr.Button(
                                "🔄 刷新视频列表",
                                variant="secondary",
                                size="lg"
                            )
                            
                        
                    with gr.Column(scale=1):
                        keywords_result = gr.Markdown("### 提取结果\n等待提取...")
                
                # 关键词预览表格
                keywords_table = gr.Dataframe(
                    headers=["ID", "字幕ID","单词", "音标", "释义", "COCA频率", "是否选中"],
                    datatype=["number", "number","str", "str", "str", "number", "number"],
                    label="提取的关键词",
                    interactive=True,  # 设置为可交互
                    visible=False
                )
                
                # 添加保存关键词选择状态的按钮
                save_keywords_btn = gr.Button(
                    "💾 保存关键词选择",
                    variant="primary",
                    visible=False  # 初始隐藏，只有在表格显示后才显示
                )
            
            # 步骤4: 视频烧制
            with gr.TabItem("🔥 步骤4: 视频烧制") as tab4:
                
                # 顶部控制区域
                with gr.Row():
                    # 左侧控制面板
                    with gr.Column():
                        # 选择带字幕的视频
                        with gr.Row():
                            burn_video_dropdown = gr.Dropdown(
                                label="选择已有字幕和关键词的视频",
                                choices=subtitle_videos,
                                value=None,
                                interactive=True,
                                container=True
                            )
                # 功能按钮行
                with gr.Row():
                    with gr.Column():
                        refresh_burn_videos_btn = gr.Button(
                                "刷新视频列表",
                                variant="secondary",
                                size="lg",
                                elem_classes="burn-button"
                            )
                    with gr.Column():
                        preview_btn = gr.Button("预览烧制信息", variant="secondary", size="lg", elem_classes="burn-button")
                    with gr.Column():
                        burn_no_subtitle_btn = gr.Button("烧制无字幕", variant="primary", size="lg", elem_classes="burn-button")
                    with gr.Column():
                        burn_keywords_btn = gr.Button("烧制关键词", variant="primary", size="lg", elem_classes="burn-button")
                    with gr.Column():
                        burn_btn = gr.Button("烧制关键词+字幕视频", variant="primary", size="lg", elem_classes="burn-button")
                
                # 输出目录设置
                with gr.Row(visible=False):
                    output_dir_input = gr.Textbox(
                        label="输出目录", 
                        value="input", 
                        placeholder="烧制视频的保存目录"
                    )
                
                # 主要内容区域 - 三栏布局
                with gr.Row():
                    # 烧制预览
                    with gr.Column():
                        gr.Markdown("### 烧制预览")
                        burn_preview = gr.Markdown(
                            "请先选择视频并点击预览按钮查看烧制信息", 
                            elem_id="burn_preview_panel"
                        )
                    
                    # 烧制进度
                    with gr.Column():
                        gr.Markdown("### 烧制进度")
                        burn_progress = gr.Textbox(
                            label="", 
                            interactive=False, 
                            placeholder="等待开始烧制...",
                            lines=20,
                            elem_id="burn_progress_panel"
                        )
                    
                    # 烧制结果
                    with gr.Column():
                        gr.Markdown("### 烧制结果")
                        burn_result = gr.Markdown(
                            "点击烧制按钮开始处理视频",
                            elem_id="burn_result_panel"
                        )
                
                # 视频预览（隐藏）
                video_preview = gr.Video(
                    label="预览视频",
                    visible=False,
                    height=480,
                    width=270,
                    autoplay=False,
                    show_label=True,
                    elem_id="video_preview_element"
                )
        
        # 辅助函数
        def update_file_info(file_path):
            """更新文件信息显示"""
            if not file_path:
                return "## 📋 文件信息\n暂未选择文件"
            
            # 在新版Gradio中，file_path是一个文件对象，需要获取其name属性
            actual_file_path = file_path.name if hasattr(file_path, 'name') else file_path
            
            # 验证文件
            is_valid, file_type, error_msg = validate_file(actual_file_path)
            
            if not is_valid:
                return f"## 📋 文件信息\n❌ {error_msg}"
            
            # 获取文件信息
            file_size = os.path.getsize(actual_file_path) / (1024 * 1024)  # MB
            file_name = os.path.basename(actual_file_path)
            file_ext = os.path.splitext(file_name)[1].upper()
            
            info_text = f"""## 📋 文件信息
- **文件名**: {file_name}
- **类型**: {file_type.upper()} 文件
- **格式**: {file_ext}
- **大小**: {file_size:.1f} MB
- **状态**: ✅ 格式支持
"""
            return info_text
        
        def process_upload(file_path):
            """处理文件上传和9:16裁剪"""
            if not file_path:
                return "### ❌ 错误\n请先上传文件", "## ℹ️ 系统状态\n等待上传文件"
            
            try:
                # 在新版Gradio中，file_path是一个文件对象，需要获取其name属性
                actual_file_path = file_path.name if hasattr(file_path, 'name') else file_path
                
                # 获取文件类型
                file_type = get_file_type(actual_file_path)
                
                # 判断是否为视频文件
                is_video = file_type == FileType.VIDEO
                
                if not is_video:
                    return (
                        "### ❌ 错误\n只支持视频文件",
                        "## ℹ️ 系统状态\n上传失败，请选择视频文件"
                    )
                
                # 调用统一处理器(不生成字幕，只进行9:16裁剪和保存)
                result = process_media_file(
                    file_path=actual_file_path,
                    output_format="SRT",
                    enable_translation=False,
                    only_preprocess=True  # 只进行预处理，不生成字幕
                )
                
                if result['success']:
                    file_name = os.path.basename(actual_file_path)
                    processed_path = result.get('processed_video_path', '')
                    processed_name = os.path.basename(processed_path)
                    video_duration = result.get('duration', 0)
                    
                    return (
                        f"""### ✅ 上传成功
- **原始文件**: {file_name}
- **处理后文件**: {processed_name}
- **保存位置**: {processed_path}
- **视频时长**: {video_duration:.2f} 秒
- **状态**: 已保存到数据库
                        """,
                        f"""## ℹ️ 系统状态
视频已上传并处理完成，请继续下一步"""
                    )
                else:
                    error_msg = result.get('error', '未知错误')
                    return (
                        f"### ❌ 处理失败\n{error_msg}",
                        f"## ℹ️ 系统状态\n视频处理失败: {error_msg}"
                    )
            
            except Exception as e:
                LOG.error(f"处理上传文件时发生错误: {str(e)}")
                return (
                    f"### ❌ 发生错误\n{str(e)}",
                    f"## ℹ️ 系统状态\n处理失败: {str(e)}"
                )
        
        def generate_subtitles(video_selection, enable_translation):
            """为选定的视频生成字幕"""
            LOG.info(f"选择的视频: {video_selection}, 类型: {type(video_selection)}")
            
            if not video_selection:
                return "请选择视频", "", "", "### ❌ 错误\n请先选择视频", "## ℹ️ 系统状态\n等待选择视频"
            
            try:
                # 从id-name-filepath格式或id-name格式中提取ID
                parts = video_selection.split('-')
                if len(parts) >= 1:
                    video_id_str = parts[0].strip()
                    try:
                        video_id = int(video_id_str)
                        LOG.info(f"提取的视频ID: {video_id}")
                    except ValueError:
                        LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                        return (
                            "ID格式错误",
                            "",
                            "",
                            f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID",
                            "## ℹ️ 系统状态\n视频ID格式错误"
                        )
                    
                    # 从选择中提取视频路径(如果存在)
                    video_path = None
                    if len(parts) > 2:  # 如果有至少3部分，说明可能包含路径
                        video_path = '-'.join(parts[2:])
                        if video_path:
                            LOG.info(f"从选择中提取的视频路径: {video_path}")
                else:
                    return (
                        "格式错误",
                        "",
                        "",
                        "### ❌ 错误\n视频选择格式错误",
                        "## ℹ️ 系统状态\n视频选择格式错误"
                    )
                
                # 获取视频信息
                series_list = db_manager.get_series(video_id)
                if not series_list:
                    LOG.error(f"未找到ID为 {video_id} 的视频")
                    return (
                        "未找到视频",
                        "",
                        "",
                        "### ❌ 错误\n未找到选择的视频",
                        "## ℹ️ 系统状态\n无法找到选择的视频"
                    )
                
                series = series_list[0]
                # 优先使用下拉框中提取的路径，如果没有，才使用数据库中的路径
                processed_path = video_path if video_path else series.get('new_file_path')
                
                if not processed_path or not os.path.exists(processed_path):
                    LOG.error(f"预处理视频不存在: {processed_path}")
                    return (
                        "预处理视频不存在",
                        "",
                        "",
                        "### ❌ 错误\n预处理视频不存在或路径无效",
                        "## ℹ️ 系统状态\n无法找到预处理视频文件"
                    )
                
                # 调用处理器生成字幕
                result = process_media_file(
                    file_path=processed_path,
                    output_format="SRT",
                    enable_translation=enable_translation,
                    skip_preprocess=True  # 跳过预处理，直接生成字幕
                )
                
                if result['success']:
                    # 处理成功
                    recognized_text = result.get('text', '')
                    translated_text = result.get('chinese_text', '') if enable_translation else ''
                    subtitle_content = result.get('subtitle_content', '')
                    subtitle_file = result.get('subtitle_file', '')
                    
                    success_msg = f"""### ✅ 字幕生成成功
- **视频**: {series['name']}
- **字幕文件**: {os.path.basename(subtitle_file)}
- **保存位置**: {subtitle_file}
- **分段数量**: {result.get('chunks_count', 0)}
- **处理时间**: {result.get('processing_time', 0):.1f} 秒
- **双语模式**: {'是' if enable_translation else '否'}
"""
                    
                    return (
                        recognized_text,
                        translated_text,
                        subtitle_content,
                        success_msg,
                        "## ℹ️ 系统状态\n字幕生成完成，请继续下一步"
                    )
                else:
                    error_msg = result.get('error', '未知错误')
                    LOG.error(f"字幕生成失败: {error_msg}")
                    return (
                        "",
                        "",
                        "",
                        f"### ❌ 生成失败\n{error_msg}",
                        f"## ℹ️ 系统状态\n字幕生成失败: {error_msg}"
                    )
            
            except Exception as e:
                LOG.error(f"生成字幕时发生错误: {str(e)}")
                return (
                    "",
                    "",
                    "",
                    f"### ❌ 发生错误\n{str(e)}",
                    f"## ℹ️ 系统状态\n字幕生成失败: {str(e)}"
                )
        
        def upload_subtitle_file(video_selection, subtitle_file):
            """上传字幕文件并关联到视频"""
            LOG.info(f"上传字幕 - 选择的视频: {video_selection}, 类型: {type(video_selection)}")
            
            if not video_selection:
                return "### ❌ 错误\n请先选择视频", "## ℹ️ 系统状态\n等待选择视频"
            
            if not subtitle_file:
                return "### ❌ 错误\n请上传字幕文件", "## ℹ️ 系统状态\n等待上传字幕文件"
            
            try:
                # 从id-name-filepath格式或id-name格式中提取ID
                parts = video_selection.split('-')
                if len(parts) >= 1:
                    video_id_str = parts[0].strip()
                    try:
                        video_id = int(video_id_str)
                        LOG.info(f"上传字幕 - 提取的视频ID: {video_id}")
                    except ValueError:
                        LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                        return (
                            f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID",
                            "## ℹ️ 系统状态\n视频ID格式错误"
                        )
                    
                    # 从选择中提取视频路径(如果存在)
                    video_path = None
                    if len(parts) > 2:
                        video_path = '-'.join(parts[2:])
                        if video_path:
                            LOG.info(f"从选择中提取的视频路径: {video_path}")
                else:
                    return (
                        "### ❌ 错误\n视频选择格式错误",
                        "## ℹ️ 系统状态\n视频选择格式错误"
                    )
                
                # 获取视频信息
                series_list = db_manager.get_series(video_id)
                if not series_list:
                    LOG.error(f"未找到ID为 {video_id} 的视频")
                    return (
                        "### ❌ 错误\n未找到选择的视频",
                        "## ℹ️ 系统状态\n无法找到选择的视频"
                    )
                
                series = series_list[0]
                
                # 处理上传的字幕文件
                actual_file_path = subtitle_file.name if hasattr(subtitle_file, 'name') else subtitle_file
                file_name = os.path.basename(actual_file_path)
                
                # 确保output目录存在
                os.makedirs("output", exist_ok=True)
                
                # 构建目标路径 (使用视频的原始名称，而不是subtitle_file的名称)
                video_name = os.path.splitext(series['name'])[0]
                target_path = os.path.abspath(os.path.join("output", f"{video_name}.srt"))
                
                # 复制字幕文件到output目录
                import shutil
                shutil.copy2(actual_file_path, target_path)
                LOG.info(f"已将字幕文件 {file_name} 复制到 {target_path}")
                
                # TODO: 将字幕内容解析并保存到数据库
                # 这部分需要另外实现，暂时只完成文件复制
                
                return (
                    f"""### ✅ 字幕上传成功
- **视频**: {series['name']}
- **字幕文件**: {os.path.basename(target_path)}
- **保存位置**: {target_path}
- **状态**: 已保存到output目录
                    """,
                    "## ℹ️ 系统状态\n字幕文件已上传，请继续下一步"
                )
            
            except Exception as e:
                LOG.error(f"上传字幕文件时发生错误: {str(e)}")
                return (
                    f"### ❌ 发生错误\n{str(e)}",
                    f"## ℹ️ 系统状态\n字幕上传失败: {str(e)}"
                )
        
        def extract_keywords(video_selection, update_coca):
            """从字幕中提取关键词"""
            LOG.info(f"提取关键词 - 选择的视频: {video_selection}, 类型: {type(video_selection)}")
            
            if not video_selection:
                return "### ❌ 错误\n请先选择视频", "## ℹ️ 系统状态\n等待选择视频", gr.update(visible=False), gr.update(visible=False)
            
            try:
                # 多种格式可能性:
                # 1. ID-NAME-PATH (普通选项)
                # 2. ID-NAME (简单选项)
                # 3. ID-NAME (字幕数: N) (带字幕数量的选项)
                
                video_id = None
                
                # 处理包含字幕数量的选项
                if '(' in video_selection:
                    # 先提取ID部分
                    video_id_part = video_selection.split('(')[0].strip()
                    parts = video_id_part.split('-')
                    if len(parts) >= 1:
                        video_id_str = parts[0].strip()
                        try:
                            video_id = int(video_id_str)
                            LOG.info(f"提取关键词 - 从带字幕数量选项中提取的视频ID: {video_id}")
                        except ValueError:
                            LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                            return (
                                f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID",
                                "## ℹ️ 系统状态\n视频ID格式错误",
                                gr.update(visible=False),
                                gr.update(visible=False)
                            )
                    else:
                        return (
                            "### ❌ 错误\n视频选择格式错误",
                            "## ℹ️ 系统状态\n视频选择格式错误",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )
                else:
                    # 从id-name-filepath格式或id-name格式中提取ID
                    parts = video_selection.split('-')
                    if len(parts) >= 1:
                        video_id_str = parts[0].strip()
                        try:
                            video_id = int(video_id_str)
                            LOG.info(f"提取关键词 - 提取的视频ID: {video_id}")
                        except ValueError:
                            LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                            return (
                                f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID",
                                "## ℹ️ 系统状态\n视频ID格式错误",
                                gr.update(visible=False),
                                gr.update(visible=False)
                            )
                    else:
                        return (
                            "### ❌ 错误\n视频选择格式错误",
                            "## ℹ️ 系统状态\n视频选择格式错误",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )
                
                # 获取视频信息
                series_list = db_manager.get_series(video_id)
                if not series_list:
                    LOG.error(f"未找到ID为 {video_id} 的视频")
                    return (
                        "### ❌ 错误\n未找到选择的视频",
                        "## ℹ️ 系统状态\n无法找到选择的视频",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )
                
                series = series_list[0]
                
                # 获取字幕
                subtitles = db_manager.get_subtitles(video_id)
                if not subtitles:
                    LOG.error(f"所选视频没有字幕: {video_id}")
                    return (
                        "### ❌ 错误\n所选视频没有字幕",
                        "## ℹ️ 系统状态\n所选视频没有字幕数据",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )
                
                # 使用KeywordExtractor提取关键词
                try:
                    # 导入关键词提取模块
                    LOG.info("开始导入关键词提取模块...")
                    from keyword_extractor import keyword_extractor
                    LOG.info("导入关键词提取模块成功")
                    
                    # 开始处理
                    LOG.info(f"开始提取关键词，系列ID: {video_id}，字幕数量: {len(subtitles)}")
                    
                    # 首先检查是否有现有的关键词，如果有则删除
                    existing_keywords = db_manager.get_keywords(series_id=video_id)
                    if existing_keywords:
                        LOG.info(f"发现 {len(existing_keywords)} 个现有关键词，将删除并重新提取")
                        db_manager.delete_keywords_by_series_id(video_id)
                    
                    # 使用batch_extract_with_context可以更有效地提取关键词
                    extracted_keywords = keyword_extractor.batch_extract_with_context(subtitles, batch_size=3)
                    
                    # 如果没有提取到关键词
                    if not extracted_keywords:
                        LOG.warning("没有提取到关键词")
                        return (
                            "### ⚠️ 没有提取到关键词",
                            "## ℹ️ 系统状态\n提取关键词过程完成，但没有找到关键词",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )
                    
                    LOG.info(f"提取到 {len(extracted_keywords)} 个关键词")
                    
                    # 保存关键词到数据库
                    # 将每个关键词按照subtitle_id分组
                    keywords_by_subtitle = {}
                    for kw in extracted_keywords:
                        subtitle_id = kw.get('subtitle_id')
                        if subtitle_id not in keywords_by_subtitle:
                            keywords_by_subtitle[subtitle_id] = []
                        keywords_by_subtitle[subtitle_id].append(kw)
                    
                    # 按照subtitle_id分批保存
                    saved_count = 0
                    for subtitle_id, keywords in keywords_by_subtitle.items():
                        if keywords:
                            keyword_ids = db_manager.create_keywords(subtitle_id, keywords)
                            saved_count += len(keyword_ids)
                    
                    LOG.info(f"成功保存 {saved_count} 个关键词到数据库")
                    
                    # 获取保存后的关键词，确保使用正确的ID
                    updated_keywords = db_manager.get_keywords(series_id=video_id)
                    if not updated_keywords:
                        LOG.warning("无法获取保存后的关键词")
                        return (
                            "### ⚠️ 关键词保存异常\n提取成功但无法获取保存后的关键词",
                            "## ℹ️ 系统状态\n关键词提取过程遇到问题",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )
                    
                    # 记录关键词ID列表，便于调试
                    keyword_ids = [kw.get('id') for kw in updated_keywords if 'id' in kw]
                    LOG.info(f"保存后的关键词ID列表（主键）: {keyword_ids}")
                    
                    # 准备表格数据 - 使用从数据库获取的关键词，而不是提取的关键词
                    table_data = []
                    for kw in updated_keywords:
                        # 重要：确保ID是t_keywords表的主键，不是subtitle_id
                        if 'id' not in kw:
                            LOG.warning(f"关键词缺少ID字段: {kw}")
                            continue
                            
                        # 确保所有字段都存在，如果不存在则使用默认值
                        table_data.append([
                            kw.get('id', 0),                # 主键ID
                            kw.get('subtitle_id', 0),       # 字幕ID
                            kw.get('key_word', ''),         # 单词
                            kw.get('phonetic_symbol', ''),  # 音标
                            kw.get('explain_text', ''),     # 释义
                            kw.get('coca', 0),              # COCA频率
                            kw.get('is_selected', 0)        # 是否选中
                        ])
                    
                    # 更新表格和保存按钮
                    return (
                        f"""### ✅ 关键词提取完成
- **视频**: {series['name']}
- **字幕数**: {len(subtitles)}
- **提取单词数**: {len(extracted_keywords)}
- **成功保存**: {saved_count}
- **COCA更新**: {'已更新' if update_coca else '未更新'}
                        """,
                        "## ℹ️ 系统状态\n关键词提取完成，可以编辑并保存选中状态",
                        gr.update(visible=True, value=table_data),  # 显示关键词表格并更新数据
                        gr.update(visible=True)  # 显示保存按钮
                    )
                
                except ImportError:
                    LOG.error("关键词提取模块未找到")
                    return (
                        "### ❌ 错误\n关键词提取模块未找到",
                        "## ℹ️ 系统状态\n缺少关键词提取功能模块",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )
                except Exception as e:
                    LOG.error(f"提取关键词时出错: {e}")
                    import traceback
                    LOG.error(traceback.format_exc())
                    return (
                        f"### ❌ 提取失败\n{str(e)}",
                        f"## ℹ️ 系统状态\n关键词提取失败: {str(e)}",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )
            
            except Exception as e:
                LOG.error(f"提取关键词时发生错误: {str(e)}")
                return (
                    f"### ❌ 发生错误\n{str(e)}",
                    f"## ℹ️ 系统状态\n关键词提取失败: {str(e)}",
                    gr.update(visible=False),
                    gr.update(visible=False)
                )
        
        def query_keywords(video_selection):
            """查询视频已有的关键词"""
            LOG.info(f"查询关键词 - 选择的视频: {video_selection}")
            
            if not video_selection:
                return "### ❌ 错误\n请先选择视频", "## ℹ️ 系统状态\n等待选择视频", gr.update(visible=False), gr.update(visible=False)
            
            try:
                # 多种格式可能性:
                # 1. ID-NAME-PATH (普通选项)
                # 2. ID-NAME (简单选项)
                # 3. ID-NAME (字幕数: N) (带字幕数量的选项)
                
                video_id = None
                
                # 处理包含字幕数量的选项
                if '(' in video_selection:
                    # 先提取ID部分
                    video_id_part = video_selection.split('(')[0].strip()
                    parts = video_id_part.split('-')
                    if len(parts) >= 1:
                        video_id_str = parts[0].strip()
                        try:
                            video_id = int(video_id_str)
                            LOG.info(f"查询关键词 - 从带字幕数量选项中提取的视频ID: {video_id}")
                        except ValueError:
                            LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                            return (
                                f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID",
                                "## ℹ️ 系统状态\n视频ID格式错误",
                                gr.update(visible=False),
                                gr.update(visible=False)
                            )
                    else:
                        return (
                            "### ❌ 错误\n视频选择格式错误",
                            "## ℹ️ 系统状态\n视频选择格式错误",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )
                else:
                    # 从id-name-filepath格式或id-name格式中提取ID
                    parts = video_selection.split('-')
                    if len(parts) >= 1:
                        video_id_str = parts[0].strip()
                        try:
                            video_id = int(video_id_str)
                            LOG.info(f"查询关键词 - 提取的视频ID: {video_id}")
                        except ValueError:
                            LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                            return (
                                f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID",
                                "## ℹ️ 系统状态\n视频ID格式错误",
                                gr.update(visible=False),
                                gr.update(visible=False)
                            )
                    else:
                        return (
                            "### ❌ 错误\n视频选择格式错误",
                            "## ℹ️ 系统状态\n视频选择格式错误",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )
                
                # 获取视频信息
                series_list = db_manager.get_series(video_id)
                if not series_list:
                    LOG.error(f"未找到ID为 {video_id} 的视频")
                    return (
                        "### ❌ 错误\n未找到选择的视频",
                        "## ℹ️ 系统状态\n无法找到选择的视频",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )
                
                series = series_list[0]
                
                # 获取字幕
                subtitles = db_manager.get_subtitles(video_id)
                if not subtitles:
                    LOG.error(f"所选视频没有字幕: {video_id}")
                    return (
                        "### ❌ 错误\n所选视频没有字幕",
                        "## ℹ️ 系统状态\n所选视频没有字幕数据",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )
                
                # 获取关键词
                keywords = db_manager.get_keywords(series_id=video_id)
                if not keywords:
                    LOG.warning(f"所选视频没有关键词: {video_id}")
                    return (
                        "### ⚠️ 没有找到关键词\n请先点击\"提取关键词\"按钮提取关键词",
                        "## ℹ️ 系统状态\n所选视频没有关键词数据",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )
                
                LOG.info(f"查询到 {len(keywords)} 个关键词")
                
                # 记录所有关键词ID（主键），确保前端显示正确的ID
                keyword_ids = [kw.get('id') for kw in keywords if 'id' in kw]
                LOG.info(f"关键词ID列表（主键）: {keyword_ids}")
                
                # 准备表格数据
                table_data = []
                for kw in keywords:
                    # 重要：确保ID是t_keywords表的主键，不是subtitle_id
                    if 'id' not in kw:
                        LOG.warning(f"关键词缺少ID字段: {kw}")
                        continue
                        
                    # 确保所有字段都存在，如果不存在则使用默认值
                    table_data.append([
                        kw.get('id', 0),                # 主键ID
                        kw.get('subtitle_id', 0),       # 字幕ID
                        kw.get('key_word', ''),         # 单词
                        kw.get('phonetic_symbol', ''),  # 音标
                        kw.get('explain_text', ''),     # 释义
                        kw.get('coca', 0),              # COCA频率
                        kw.get('is_selected', 0)        # 是否选中
                    ])
                
                # 更新表格和保存按钮
                return (
                    f"""### ✅ 关键词查询完成
- **视频**: {series['name']}
- **字幕数**: {len(subtitles)}
- **关键词数**: {len(keywords)}
                    """,
                    "## ℹ️ 系统状态\n关键词查询完成，可以编辑并保存选中状态",
                    gr.update(visible=True, value=table_data),  # 显示关键词表格并更新数据
                    gr.update(visible=True)  # 显示保存按钮
                )
                
            except Exception as e:
                LOG.error(f"查询关键词时发生错误: {str(e)}")
                import traceback
                LOG.error(traceback.format_exc())
                return (
                    f"### ❌ 查询失败\n{str(e)}",
                    f"## ℹ️ 系统状态\n关键词查询失败: {str(e)}",
                    gr.update(visible=False),
                    gr.update(visible=False)
                )
        
        def save_keywords_selection(edited_data, video_selection):
            """保存关键词选中状态"""
            LOG.info(f"保存关键词选中状态 - 选择的视频: {video_selection}")
            LOG.info(f"接收到的数据类型: {type(edited_data)}, 长度: {len(edited_data)}")
            
            if not video_selection:
                return "### ❌ 错误\n无法确定要保存的视频", "## ℹ️ 系统状态\n保存失败，无法确定视频"
            
            try:
                # 从选择中提取视频ID
                video_id = None
                
                # 处理包含字幕数量的选项
                if '(' in video_selection:
                    video_id_part = video_selection.split('(')[0].strip()
                    parts = video_id_part.split('-')
                    if len(parts) >= 1:
                        video_id_str = parts[0].strip()
                        try:
                            video_id = int(video_id_str)
                        except ValueError:
                            return f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID", "## ℹ️ 系统状态\n保存失败，视频ID格式错误"
                else:
                    parts = video_selection.split('-')
                    if len(parts) >= 1:
                        video_id_str = parts[0].strip()
                        try:
                            video_id = int(video_id_str)
                        except ValueError:
                            return f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID", "## ℹ️ 系统状态\n保存失败，视频ID格式错误"
                
                if not video_id:
                    return "### ❌ 错误\n无法确定视频ID", "## ℹ️ 系统状态\n保存失败，无法确定视频ID"
                
                # 获取关键词数据 - 用于验证ID
                keywords = db_manager.get_keywords(series_id=video_id)
                if not keywords:
                    return "### ⚠️ 没有关键词数据\n无法更新关键词状态", "## ℹ️ 系统状态\n未找到关键词数据"
                
                LOG.info(f"从数据库获取到 {len(keywords)} 个关键词")
                
                # 创建关键词ID映射表，方便后续查询
                keyword_id_map = {kw.get('id'): kw for kw in keywords if 'id' in kw}
                valid_keyword_ids = set(keyword_id_map.keys())
                LOG.info(f"有效的关键词ID列表: {valid_keyword_ids}")
                
                # 检查和记录数据格式
                if hasattr(edited_data, 'columns'):
                    LOG.info(f"DataFrame列名: {list(edited_data.columns)}")
                
                # 处理编辑后的数据
                success_count = 0
                processed_count = 0
                
                # 针对Pandas DataFrame的处理
                if hasattr(edited_data, 'iloc') and hasattr(edited_data, 'columns'):
                    LOG.info("检测到Pandas DataFrame")
                    
                    # 获取列名
                    columns = list(edited_data.columns)
                    LOG.info(f"表格列名: {columns}")
                    
                    # 查找ID列和是否选中列
                    id_col = None
                    selected_col = None
                    
                    # 假设列名中含有"ID"和"是否选中"
                    for col in columns:
                        if col == "ID":  # 确保精确匹配主键ID列
                            id_col = col
                            LOG.info(f"找到主键ID列: {col}")
                        elif "选中" in col:
                            selected_col = col
                            LOG.info(f"找到选中状态列: {col}")
                    
                    # 如果找到了这两列，则进行处理
                    if id_col is not None and selected_col is not None:
                        # 输出所有ID用于调试
                        all_ids = []
                        for index, row in edited_data.iterrows():
                            try:
                                id_value = row[id_col]
                                if isinstance(id_value, (int, float)) and not pd.isna(id_value):
                                    all_ids.append(int(id_value))
                            except:
                                pass
                        
                        LOG.info(f"表格中的所有ID: {all_ids}")
                        
                        # 遍历每一行
                        for index, row in edited_data.iterrows():
                            try:
                                # 使用列名安全地访问值
                                id_value = row[id_col]
                                selected_value = row[selected_col]
                                
                                # 检查ID是否为有效的数字
                                if not isinstance(id_value, (int, float)) or pd.isna(id_value):
                                    LOG.info(f"跳过非数字ID行: {id_value}")
                                    continue
                                
                                # 转换为整数
                                keyword_id = int(id_value)
                                
                                # 验证关键词ID是否在数据库中存在
                                if keyword_id not in valid_keyword_ids:
                                    LOG.warning(f"跳过无效关键词ID: {keyword_id}，该ID在数据库中不存在")
                                    continue
                                
                                # 处理是否选中值
                                is_selected = None
                                
                                if isinstance(selected_value, (int, float)) and not pd.isna(selected_value):
                                    is_selected = int(selected_value)
                                elif isinstance(selected_value, str) and selected_value.isdigit():
                                    is_selected = int(selected_value)
                                elif isinstance(selected_value, bool):
                                    is_selected = 1 if selected_value else 0
                                
                                if is_selected is not None:
                                    processed_count += 1
                                    LOG.info(f"尝试更新关键词 ID={keyword_id} 的选中状态为 {is_selected}")
                                    # 更新数据库
                                    if db_manager.update_keyword_selection(keyword_id, bool(is_selected)):
                                        success_count += 1
                                        LOG.info(f"✅ 成功更新关键词 ID={keyword_id} 的选中状态为 {is_selected}")
                                    else:
                                        LOG.warning(f"❌ 更新关键词 ID={keyword_id} 失败")
                                else:
                                    LOG.warning(f"无法解析选中状态: {selected_value}")
                            except Exception as e:
                                LOG.error(f"处理行时出错: {e}, 行数据: {row}")
                    else:
                        LOG.warning(f"未找到必要的列: ID列={id_col}, 选中状态列={selected_col}")
                else:
                    LOG.warning("数据不是Pandas DataFrame或不包含预期的方法")
                
                # 返回结果
                if success_count > 0:
                    return (
                        f"### ✅ 保存成功\n已更新 {success_count}/{processed_count} 个关键词的选中状态",
                        "## ℹ️ 系统状态\n关键词选中状态已保存"
                    )
                else:
                    return (
                        f"### ⚠️ 没有更新\n处理了 {processed_count} 行，但没有关键词被更新。可能是ID不存在于数据库中，请先提取关键词。",
                        "## ℹ️ 系统状态\n没有关键词状态被更改"
                    )
                
            except Exception as e:
                LOG.error(f"保存关键词选中状态时出错: {e}")
                import traceback
                LOG.error(traceback.format_exc())
                return (
                    f"### ❌ 保存失败\n{str(e)}",
                    f"## ℹ️ 系统状态\n关键词选中状态保存失败: {str(e)}"
                )
        
        def preview_burn_video(video_selection):
            """预览烧制视频信息"""
            LOG.info(f"预览烧制 - 选择的视频: {video_selection}")
            
            if not video_selection:
                return "### ❌ 错误\n请先选择视频", gr.update(visible=False)
            
            try:
                # 从选择中提取系列ID
                # 处理不同格式：ID-NAME-PATH, ID-NAME, ID-NAME (字幕数: N)
                if '(' in video_selection:
                    video_id_part = video_selection.split('(')[0].strip()
                    parts = video_id_part.split('-')
                else:
                    parts = video_selection.split('-')
                
                if len(parts) >= 1:
                    video_id_str = parts[0].strip()
                    try:
                        video_id = int(video_id_str)
                        LOG.info(f"提取的视频ID: {video_id}")
                    except ValueError:
                        LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                        return f"### ❌ 错误\n'{video_id_str}' 不是有效的视频ID", gr.update(visible=False)
                else:
                    return "### ❌ 错误\n视频选择格式错误", gr.update(visible=False)
                
                # 获取系列信息
                series_list = db_manager.get_series(video_id)
                if not series_list:
                    LOG.error(f"未找到ID为 {video_id} 的视频")
                    return "### ❌ 错误\n未找到选择的视频", gr.update(visible=False)
                
                series = series_list[0]
                
                # 获取字幕和关键词信息
                subtitles = db_manager.get_subtitles(video_id)
                keywords = db_manager.get_keywords(series_id=video_id)
                
                if not subtitles:
                    return "### ❌ 错误\n所选视频没有字幕", gr.update(visible=False)
                
                if not keywords:
                    return "### ❌ 错误\n所选视频没有关键词", gr.update(visible=False)
                
                # 导入视频烧制模块
                from video_subtitle_burner import video_burner
                
                # 获取预览信息
                preview = video_burner.get_burn_preview(video_id)
                
                # 检查是否有预处理视频可预览
                video_preview_path = None
                if 'new_file_path' in series and series['new_file_path'] and os.path.exists(series['new_file_path']):
                    video_preview_path = series['new_file_path']
                
                # 构建预览信息
                preview_text = f"""#### 系列信息
**ID**: {series['id']}  
**名称**: {series['name']}  
**类型**: {series.get('file_type', '未知')}  
**时长**: {series.get('duration', 0):.1f}秒  

#### 烧制统计
**字幕总数**: {len(subtitles)} 条  
**可用关键词**: {preview['total_available_keywords']} 个  
**已选中关键词**: {preview['selected_keywords']} 个  
**烧制时长**: {preview['total_duration']:.1f} 秒  
**预估文件大小**: {preview['estimated_file_size']}  

#### 词频分布
**500-5000**: {preview['coca_distribution'].get('500-5000', 0)} 个  
**5000-10000**: {preview['coca_distribution'].get('5000-10000', 0)} 个  
**10000+**: {preview['coca_distribution'].get('10000+', 0)} 个  
"""

                if preview['sample_keywords']:
                    preview_text += "\n#### 示例单词\n"
                    for i, kw in enumerate(preview['sample_keywords'], 1):
                        if i > 5:  # 只显示前5个示例
                            break
                        preview_text += f"{i}. **{kw['keyword']}** {kw.get('phonetic', '')}  \n   {kw.get('explanation', '')}  \n   (COCA: {kw.get('coca_rank', 'N/A')})\n\n"
                else:
                    preview_text += "\n#### 暂无符合条件的重点单词"
                
                # 返回预览信息和视频预览更新
                if video_preview_path:
                    # 返回添加了视频预览路径的更新
                    return preview_text, gr.update(
                        visible=True, 
                        value=video_preview_path
                    )
                else:
                    return preview_text, gr.update(visible=False)
                    
            except Exception as e:
                LOG.error(f"预览烧制信息失败: {e}")
                import traceback
                LOG.error(traceback.format_exc())
                return f"### ❌ 错误\n预览失败: {str(e)}", gr.update(visible=False)

        def burn_video_with_progress(video_selection, output_dir):
            """烧制视频（带进度显示）"""
            if not video_selection:
                yield "❌ 请先选择视频", "### ❌ 错误\n请先选择视频"
                return
            
            try:
                # 从选择中提取系列ID
                if '(' in video_selection:
                    video_id_part = video_selection.split('(')[0].strip()
                    parts = video_id_part.split('-')
                else:
                    parts = video_selection.split('-')
                
                if len(parts) >= 1:
                    video_id_str = parts[0].strip()
                    try:
                        video_id = int(video_id_str)
                        LOG.info(f"提取的视频ID: {video_id}")
                    except ValueError:
                        LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                        yield f"❌ '{video_id_str}' 不是有效的视频ID", f"### ❌ 错误\n无效的视频ID"
                        return
                else:
                    yield "❌ 视频选择格式错误", "### ❌ 错误\n视频选择格式错误"
                    return
                
                # 导入视频烧制模块
                from video_subtitle_burner import video_burner
                
                progress_log = []
                
                def progress_callback(message):
                    # 特殊处理进度消息，保留处理状态和成功率统计信息
                    if message.startswith("🎬 进度:") or message.startswith("📊 成功处理"):
                        # 查找并替换之前的相同类型消息
                        for i, log in enumerate(progress_log):
                            if log.startswith("🎬 进度:") and message.startswith("🎬 进度:"):
                                progress_log[i] = message
                                break
                            elif log.startswith("📊 成功处理") and message.startswith("📊 成功处理"):
                                progress_log[i] = message
                                break
                        else:
                            # 如果没有找到相同类型的消息，就添加新消息
                            progress_log.append(message)
                    else:
                        # 其他消息直接添加
                        progress_log.append(message)
                    
                    # 返回格式化的日志，最近20条消息
                    return '\n'.join(progress_log[-20:])
                
                # 开始烧制
                yield "🔄 准备烧制...", "### ⏳ 处理中\n正在准备烧制视频..."
                
                # 获取系列信息以显示更详细的进度
                series_list = db_manager.get_series(video_id)
                if series_list:
                    series = series_list[0]
                    input_video = series.get('new_file_path', '')
                    if input_video:
                        input_basename = os.path.basename(input_video)
                        yield f"🔄 正在烧制：基于 {input_basename}", "### ⏳ 处理中\n正在处理视频文件..."
                
                # 执行烧制
                output_video = video_burner.process_series_video(
                    video_id,
                    output_dir,
                    title_text="第三遍：完全消化",
                    progress_callback=progress_callback
                )
                
                if output_video:
                    # 将烧制视频路径保存到third_name和third_file_path
                    db_manager.update_series_video_info(
                        video_id,
                        third_name=os.path.basename(output_video),
                        third_file_path=output_video
                    )
                    
                    final_message = "✅ 烧制完成！"
                    progress_log.append(final_message)
                    yield '\n'.join(progress_log), f"""### ✅ 烧制成功

**输出文件**：{os.path.basename(output_video)}  
**保存路径**：{output_video}  
**状态**：已更新到数据库  

**说明**：基于输入视频生成带关键词和字幕的输出视频，存放在input文件夹下。

**点击刷新按钮**可以重新选择视频进行烧制。
"""
                else:
                    final_message = "❌ 烧制失败"
                    progress_log.append(final_message)
                    yield '\n'.join(progress_log), """### ❌ 烧制失败

处理过程中发生错误，请检查日志获取详细信息。

可能的原因：
- 视频文件不存在或已损坏
- 关键词数据不完整
- 系统资源不足

请尝试刷新视频列表，选择其他视频或重试。
"""
            except Exception as e:
                error_msg = f"烧制过程失败: {str(e)}"
                LOG.error(error_msg)
                yield error_msg, f"""### ❌ 烧制失败

处理过程中发生错误: {str(e)}

请检查日志获取详细信息，或联系技术支持。
"""
        
        def burn_keywords_only_video(video_selection, output_dir):
            """只烧制关键词视频（不带字幕）"""
            if not video_selection:
                yield "❌ 请先选择视频", "### ❌ 错误\n请先选择视频"
                return
            
            try:
                # 从选择中提取系列ID
                if '(' in video_selection:
                    video_id_part = video_selection.split('(')[0].strip()
                    parts = video_id_part.split('-')
                else:
                    parts = video_selection.split('-')
                
                if len(parts) >= 1:
                    video_id_str = parts[0].strip()
                    try:
                        video_id = int(video_id_str)
                        LOG.info(f"提取的视频ID: {video_id}")
                    except ValueError:
                        LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                        yield f"❌ '{video_id_str}' 不是有效的视频ID", f"### ❌ 错误\n无效的视频ID"
                        return
                else:
                    yield "❌ 视频选择格式错误", "### ❌ 错误\n视频选择格式错误"
                    return
                
                # 导入视频烧制模块
                from video_subtitle_burner import video_burner
                
                progress_log = []
                
                def progress_callback(message):
                    # 特殊处理进度消息，保留处理状态和成功率统计信息
                    if message.startswith("🎬 进度:") or message.startswith("📊 成功处理"):
                        # 查找并替换之前的相同类型消息
                        for i, log in enumerate(progress_log):
                            if log.startswith("🎬 进度:") and message.startswith("🎬 进度:"):
                                progress_log[i] = message
                                break
                            elif log.startswith("📊 成功处理") and message.startswith("📊 成功处理"):
                                progress_log[i] = message
                                break
                        else:
                            # 如果没有找到相同类型的消息，就添加新消息
                            progress_log.append(message)
                    else:
                        # 其他消息直接添加
                        progress_log.append(message)
                    
                    # 返回格式化的日志，最近20条消息
                    return '\n'.join(progress_log[-20:])
                
                # 开始烧制
                yield "🔄 准备烧制...", "### ⏳ 处理中\n正在准备烧制关键词视频..."
                
                # 获取系列信息以显示更详细的进度
                series_list = db_manager.get_series(video_id)
                if series_list:
                    series = series_list[0]
                    input_video = series.get('new_file_path', '')
                    if input_video:
                        input_basename = os.path.basename(input_video)
                        yield f"🔄 正在烧制：基于 {input_basename}", "### ⏳ 处理中\n正在处理视频文件..."
                
                # 执行只烧制关键词的处理
                output_video = video_burner.process_keywords_only_video(
                    video_id,
                    output_dir,
                    title_text="第二遍：重点词汇",
                    progress_callback=progress_callback
                )
                
                if output_video:
                    # 将烧制视频路径保存到second_name和second_file_path
                    db_manager.update_series_video_info(
                        video_id,
                        second_name=os.path.basename(output_video),
                        second_file_path=output_video
                    )
                    
                    final_message = "✅ 关键词烧制完成！"
                    progress_log.append(final_message)
                    yield '\n'.join(progress_log), f"""### ✅ 关键词烧制成功

**输出文件**：{os.path.basename(output_video)}  
**保存路径**：{output_video}  
**状态**：已更新到数据库  

**说明**：基于输入视频生成只有关键词的视频（无字幕），存放在input文件夹下。
    
**点击刷新按钮**可以重新选择视频进行烧制。
"""
                else:
                    final_message = "❌ 关键词烧制失败"
                    progress_log.append(final_message)
                    yield '\n'.join(progress_log), """### ❌ 关键词烧制失败

处理过程中发生错误，请检查日志获取详细信息。

可能的原因：
- 视频文件不存在或已损坏
- 关键词数据不完整
- 系统资源不足

请尝试刷新视频列表，选择其他视频或重试。
"""
            except Exception as e:
                error_msg = f"关键词烧制过程失败: {str(e)}"
                LOG.error(error_msg)
                yield error_msg, f"""### ❌ 关键词烧制失败

处理过程中发生错误: {str(e)}

请检查日志获取详细信息，或联系技术支持。
"""
        
        def burn_no_subtitle_video(video_selection, output_dir):
            """烧制无字幕视频，只有顶部标题"""
            if not video_selection:
                yield "❌ 请先选择视频", "### ❌ 错误\n请先选择视频"
                return
            
            try:
                # 从选择中提取系列ID
                if '(' in video_selection:
                    video_id_part = video_selection.split('(')[0].strip()
                    parts = video_id_part.split('-')
                else:
                    parts = video_selection.split('-')
                
                if len(parts) >= 1:
                    video_id_str = parts[0].strip()
                    try:
                        video_id = int(video_id_str)
                        LOG.info(f"提取的视频ID: {video_id}")
                    except ValueError:
                        LOG.error(f"无法将 '{video_id_str}' 转换为有效的ID")
                        yield f"❌ '{video_id_str}' 不是有效的视频ID", f"### ❌ 错误\n无效的视频ID"
                        return
                else:
                    yield "❌ 视频选择格式错误", "### ❌ 错误\n视频选择格式错误"
                    return
                
                # 导入视频烧制模块
                from video_subtitle_burner import video_burner
                
                progress_log = []
                
                def progress_callback(message):
                    # 添加消息到日志列表
                    progress_log.append(message)
                    # 返回格式化的日志，最近20条消息
                    return '\n'.join(progress_log[-20:])
                
                # 开始烧制
                yield "🔄 准备烧制无字幕视频...", "### ⏳ 处理中\n正在准备烧制无字幕视频..."
                
                # 获取系列信息以显示更详细的进度
                series_list = db_manager.get_series(video_id)
                if series_list:
                    series = series_list[0]
                    input_video = series.get('new_file_path', '')
                    if input_video:
                        input_basename = os.path.basename(input_video)
                        yield f"🔄 正在烧制：基于 {input_basename}", "### ⏳ 处理中\n正在处理视频文件..."
                
                # 执行无字幕视频处理
                output_video = video_burner.process_no_subtitle_video(
                    video_id,
                    output_dir,
                    title_text="第一遍：无字幕",
                    progress_callback=progress_callback
                )
                
                if output_video:
                    final_message = "✅ 无字幕视频烧制完成！"
                    progress_log.append(final_message)
                    yield '\n'.join(progress_log), f"""### ✅ 无字幕视频烧制成功

**输出文件**：{os.path.basename(output_video)}  
**保存路径**：{output_video}  
**状态**：已更新到数据库  

**说明**：基于输入视频生成只有顶部标题的无字幕视频，存放在input文件夹下。
    
**点击刷新按钮**可以重新选择视频进行烧制。
"""
                else:
                    final_message = "❌ 无字幕视频烧制失败"
                    progress_log.append(final_message)
                    yield '\n'.join(progress_log), """### ❌ 无字幕视频烧制失败

处理过程中发生错误，请检查日志获取详细信息。

可能的原因：
- 视频文件不存在或已损坏
- 系统资源不足

请尝试刷新视频列表，选择其他视频或重试。
"""
            except Exception as e:
                error_msg = f"无字幕视频烧制过程失败: {str(e)}"
                LOG.error(error_msg)
                yield error_msg, f"""### ❌ 无字幕视频烧制失败

处理过程中发生错误: {str(e)}

请检查日志获取详细信息，或联系技术支持。
"""
        
        # 实时刷新视频列表的函数
        def refresh_video_list():
            """在用户点击下拉框时刷新视频列表"""
            try:
                video_list = load_video_list()
                LOG.info(f"实时刷新视频列表，获取到 {len(video_list)} 个视频")
                
                # 详细输出前3个选项，用于调试
                for i, option in enumerate(video_list[:3]):
                    LOG.info(f"更新后选项 {i+1}: {option}")
                
                # 返回更新后的列表 - 使用gr.update()
                return gr.update(choices=video_list)
            except Exception as e:
                LOG.error(f"刷新视频列表失败: {e}")
                import traceback
                LOG.error(traceback.format_exc())
                # 出错时返回空更新
                return gr.update(choices=[])
        
        # 为字幕视频下拉框添加刷新功能
        def refresh_subtitle_videos():
            """在用户点击字幕视频下拉框时刷新列表"""
            try:
                subtitle_list = load_subtitle_videos()
                LOG.info(f"实时刷新字幕视频列表，获取到 {len(subtitle_list)} 个视频")
                
                # 详细输出前3个选项，用于调试
                for i, option in enumerate(subtitle_list[:3]):
                    LOG.info(f"更新后字幕视频选项 {i+1}: {option}")
                
                # 返回更新后的列表 - 使用gr.update()
                return gr.update(choices=subtitle_list)
            except Exception as e:
                LOG.error(f"刷新字幕视频列表失败: {e}")
                import traceback
                LOG.error(traceback.format_exc())
                # 出错时返回空更新
                return gr.update(choices=[])
        
        # 绑定事件
        # 步骤1: 上传文件
        file_input.change(
            update_file_info,
            inputs=[file_input],
            outputs=[file_info]
        )
        
        # 创建更新下拉框的函数
        def update_dropdowns(video_list):
            """更新所有下拉框"""
            return video_list, video_list
        
        upload_button.click(
            process_upload,
            inputs=[file_input],
            outputs=[upload_result, status_md]
        ).then(
            # 更新所有视频下拉框
            fn=lambda: gr.update(choices=load_video_list()),
            inputs=[],
            outputs=[video_dropdown]
        ).then(
            # 更新字幕上传的视频下拉框
            fn=lambda: gr.update(choices=load_video_list()),
            inputs=[],
            outputs=[video_dropdown_upload]
        ).then(
            # 更新带字幕的视频下拉框
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[subtitle_video_dropdown]
        ).then(
            # 更新烧制视频的下拉框
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[burn_video_dropdown]
        )
        
        # 步骤2: 字幕生成
        # 设置tab切换时的事件，确保下拉框选项是最新的
        tab2.select(
            fn=lambda: gr.update(choices=load_video_list()),
            inputs=[],
            outputs=[video_dropdown]
        ).then(
            fn=lambda: gr.update(choices=load_video_list()),
            inputs=[],
            outputs=[video_dropdown_upload]
        )
        
        # 绑定刷新按钮事件
        refresh_videos_btn.click(
            fn=refresh_video_list,
            inputs=[],
            outputs=[video_dropdown]
        )
        
        refresh_videos_upload_btn.click(
            fn=refresh_video_list,
            inputs=[],
            outputs=[video_dropdown_upload]
        )
        
        # 绑定生成按钮事件
        generate_button.click(
            generate_subtitles,
            inputs=[video_dropdown, translation_checkbox],
            outputs=[result_text, translation_text, subtitle_preview, subtitle_gen_result, status_md]
        ).then(
            # 更新带字幕的视频下拉框
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[subtitle_video_dropdown]
        ).then(
            # 同时更新烧制视频的下拉框
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[burn_video_dropdown]
        )
        
        # 上传字幕
        subtitle_upload_btn.click(
            upload_subtitle_file,
            inputs=[video_dropdown_upload, subtitle_file_input],
            outputs=[subtitle_upload_result, status_md]
        ).then(
            # 更新带字幕的视频下拉框
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[subtitle_video_dropdown]
        ).then(
            # 同时更新烧制视频的下拉框
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[burn_video_dropdown]
        )
        
        # 步骤3: 关键词提取
        # 设置tab切换时的事件，确保下拉框选项是最新的
        tab3.select(
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[subtitle_video_dropdown]
        )
        
        # 绑定刷新字幕视频按钮事件
        refresh_subtitle_videos_btn.click(
            fn=refresh_subtitle_videos,
            inputs=[],
            outputs=[subtitle_video_dropdown]
        )
        
        # 提取关键词
        extract_button.click(
            extract_keywords,
            inputs=[subtitle_video_dropdown, coca_checkbox],
            outputs=[keywords_result, status_md, keywords_table, save_keywords_btn]
        )
        
        # 查询关键词
        query_keywords_btn.click(
            query_keywords,
            inputs=[subtitle_video_dropdown],
            outputs=[keywords_result, status_md, keywords_table, save_keywords_btn]
        )
        
        # 保存关键词选中状态
        save_keywords_btn.click(
            save_keywords_selection,
            inputs=[keywords_table, subtitle_video_dropdown],
            outputs=[keywords_result, status_md]
        )
        
        # 步骤4: 视频烧制
        # 设置tab切换时的事件，确保下拉框选项是最新的
        tab4.select(
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[burn_video_dropdown]
        )
        
        # 绑定刷新烧制视频按钮事件
        refresh_burn_videos_btn.click(
            fn=refresh_subtitle_videos,
            inputs=[],
            outputs=[burn_video_dropdown]
        )
        
        # 预览视频
        preview_btn.click(
            preview_burn_video,
            inputs=[burn_video_dropdown],
            outputs=[burn_preview, video_preview]
        )
        
        # 烧制视频
        burn_no_subtitle_btn.click(
            burn_no_subtitle_video,
            inputs=[burn_video_dropdown, output_dir_input],
            outputs=[burn_progress, burn_result]
        )
        
        burn_keywords_btn.click(
            burn_keywords_only_video,
            inputs=[burn_video_dropdown, output_dir_input],
            outputs=[burn_progress, burn_result]
        )
        
        burn_btn.click(
            burn_video_with_progress,
            inputs=[burn_video_dropdown, output_dir_input],
            outputs=[burn_progress, burn_result]
        )

        # 添加界面加载事件，确保在界面加载时就加载所有下拉框选项
        interface.load(
            fn=lambda: gr.update(choices=load_video_list()),
            inputs=[],
            outputs=[video_dropdown]
        ).then(
            fn=lambda: gr.update(choices=load_video_list()),
            inputs=[],
            outputs=[video_dropdown_upload]
        ).then(
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[subtitle_video_dropdown]
        ).then(
            fn=lambda: gr.update(choices=load_subtitle_videos()),
            inputs=[],
            outputs=[burn_video_dropdown]
        )
    
    return interface

if __name__ == "__main__":
    LOG.info("🚀 启动视频处理工作流服务器...")
    
    # 检查必要组件
    try:
        from video_processor import check_ffmpeg_availability
        if not check_ffmpeg_availability():
            LOG.warning("⚠️ 未检测到 ffmpeg，视频处理功能可能不可用")
        else:
            LOG.info("✅ ffmpeg 可用，支持视频处理")
    except Exception as e:
        LOG.warning(f"⚠️ 检查 ffmpeg 时发生错误: {e}")
    
    # 创建并启动界面
    interface = create_main_interface()
    interface.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=False
    )