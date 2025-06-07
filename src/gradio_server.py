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

# 定义加载视频列表函数
def load_video_list():
    """加载视频列表"""
    try:
        # 从数据库获取所有视频列表
        series_list = db_manager.get_series()
        
        if not series_list:
            LOG.warning("⚠️ 数据库中没有系列数据")
            # 返回空列表，但需要返回两个相同的空列表（两个下拉框）
            return [], []
        
        LOG.info(f"查询到 {len(series_list)} 条系列数据")
        
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
                LOG.info(f"添加有效视频选项: ID={series['id']}, 名称={series['name']}, 路径={path}")
            else:
                # 如果文件不存在，只包含ID和名称
                option = f"{series['id']}-{series['name']}"
                options.append(option)
                LOG.info(f"添加ID-名称选项(无路径): ID={series['id']}, 名称={series['name']}")
        
        LOG.info(f"生成了 {len(options)} 个下拉选项")
        
        # 为调试输出前5个选项
        for i, option in enumerate(options[:5]):
            LOG.info(f"选项 {i+1}: {option}")
        
        # 返回两个相同的选项列表（用于两个下拉框）
        return options, options
    except Exception as e:
        LOG.error(f"加载视频列表失败: {e}")
        import traceback
        LOG.error(traceback.format_exc())
        # 确保即使发生错误也返回两个空列表
        return [], []

# 定义加载带字幕视频列表函数
def load_subtitle_videos():
    """加载已有字幕的视频列表"""
    try:
        # 从数据库获取所有视频列表
        series_list = db_manager.get_series()
        
        if not series_list:
            LOG.warning("⚠️ 数据库中没有系列数据")
            return []
        
        LOG.info(f"为字幕下拉框查询到 {len(series_list)} 条系列数据")
        
        # 准备下拉选项
        options = []
        for series in series_list:
            # 检查是否有字幕
            subtitles = db_manager.get_subtitles(series['id'])
            if subtitles:
                option_text = f"{series['id']}-{series['name']} (字幕数: {len(subtitles)})"
                options.append(option_text)
                LOG.info(f"添加带字幕的选项: {option_text}")
        
        LOG.info(f"生成了 {len(options)} 个带字幕的下拉选项")
        
        # 如果没有带字幕的视频，返回所有视频
        if not options:
            LOG.warning("⚠️ 没有找到带字幕的视频，返回所有视频")
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
            
            LOG.info(f"返回全部视频选项 ({len(options)}个)")
        
        return options
    except Exception as e:
        LOG.error(f"加载视频字幕列表失败: {e}")
        import traceback
        LOG.error(traceback.format_exc())
        return []

def create_main_interface():
    """创建主界面"""
    
    # 获取支持的格式信息
    formats_info = get_media_formats_info()
    
    # 创建必要的目录
    for directory in ["input", "output"]:
        os.makedirs(directory, exist_ok=True)
    
    # 初始化视频列表
    video_list, _ = load_video_list()
    subtitle_videos = load_subtitle_videos()
    
    with gr.Blocks(title="视频处理工作流", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🎬 视频处理工作流")
        
        # 全局状态显示
        status_md = gr.Markdown("## ℹ️ 系统状态\n系统已就绪，请开始工作流程")
        
        with gr.Tabs() as tabs:
            # 步骤1: 上传文件并9:16裁剪
            with gr.TabItem("📤 步骤1: 上传视频") as tab1:
                gr.Markdown("""
                ## 📤 上传视频文件
                
                此步骤将完成:
                1. 上传原始视频文件
                2. 自动进行9:16裁剪
                3. 保存到input文件夹
                4. 信息存入数据库
                """)
                
                with gr.Row():
                    with gr.Column(scale=2):
                        # 文件上传
                        file_input = gr.File(
                            label="📁 上传视频文件",
                            file_types=formats_info['video_formats'],
                            type="file"
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
                gr.Markdown("""
                ## 🔤 字幕生成或上传
                
                此步骤将完成:
                1. 为视频生成字幕，或上传已有字幕
                2. 可选进行翻译
                3. 保存到output文件夹
                4. 信息存入数据库
                """)
                
                with gr.Tabs() as subtitle_tabs:
                    # 字幕生成选项卡
                    with gr.TabItem("🎙️ 生成字幕"):
                        with gr.Row():
                            with gr.Column():
                                # 选择视频下拉框
                                video_dropdown = gr.Dropdown(
                                    label="📋 选择已上传的视频",
                                    choices=video_list,
                                    value=None,
                                    interactive=True
                                )
                                
                                with gr.Row():
                                    # 字幕选项
                                    translation_checkbox = gr.Checkbox(
                                        label="🌐 启用中文翻译",
                                        value=True,
                                        info="生成英中双语字幕"
                                    )
                                    
                                    short_subtitle_checkbox = gr.Checkbox(
                                        label="📱 短视频字幕模式",
                                        value=False,
                                        info="针对抖音等平台优化，生成适合手机屏幕的短句字幕"
                                    )
                                
                                generate_button = gr.Button(
                                    "🎬 生成字幕",
                                    variant="primary"
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
                        subtitle_preview = gr.Textbox(
                            label="🎬 字幕预览",
                            lines=8,
                            placeholder="生成的字幕内容将在这里预览..."
                        )
                        
                        subtitle_gen_result = gr.Markdown("### 处理结果\n等待生成...")
                    
                    # 上传字幕选项卡
                    with gr.TabItem("📑 上传字幕"):
                        with gr.Row():
                            with gr.Column(scale=2):
                                # 选择视频
                                video_dropdown_upload = gr.Dropdown(
                                    label="📋 选择视频",
                                    choices=video_list,
                                    value=None,
                                    interactive=True
                                )
                                
                                # 上传字幕文件
                                subtitle_file_input = gr.File(
                                    label="📝 上传SRT字幕文件",
                                    file_types=[".srt"],
                                    type="file"
                                )
                                
                                subtitle_upload_btn = gr.Button(
                                    "📤 上传字幕",
                                    variant="primary"
                                )
                            
                            with gr.Column(scale=1):
                                subtitle_upload_result = gr.Markdown("### 上传结果\n等待上传...")
            
            # 步骤3: 关键词AI筛查提取
            with gr.TabItem("🔑 步骤3: 关键词提取") as tab3:
                gr.Markdown("""
                ## 🔑 关键词AI筛查提取
                
                此步骤将完成:
                1. 从字幕中提取重点单词
                2. 自动更新COCA频率
                3. 信息存入数据库
                """)
                
                with gr.Row():
                    with gr.Column(scale=2):
                        # 选择带字幕的视频
                        subtitle_video_dropdown = gr.Dropdown(
                            label="📋 选择已有字幕的视频",
                            choices=subtitle_videos,
                            value=None,
                            interactive=True
                        )
                        
                        with gr.Row():
                            # 提取选项
                            coca_checkbox = gr.Checkbox(
                                label="📚 自动更新COCA频率",
                                value=True,
                                info="自动查询并更新单词的COCA频率"
                            )
                        
                        extract_button = gr.Button(
                            "🔍 提取关键词",
                            variant="primary"
                        )
                    
                    with gr.Column(scale=1):
                        keywords_result = gr.Markdown("### 提取结果\n等待提取...")
                
                # 关键词预览表格
                keywords_table = gr.Dataframe(
                    headers=["ID", "单词", "音标", "释义", "COCA频率", "字幕ID"],
                    datatype=["number", "str", "str", "str", "number", "number"],
                    label="提取的关键词",
                    interactive=False,
                    visible=False
                )
            
            # 步骤4: 视频烧制(预留)
            with gr.TabItem("🔥 步骤4: 视频烧制") as tab4:
                gr.Markdown("""
                ## 🔥 视频烧制
                
                此步骤将在后续开发中实现...
                """)
                
                burn_info = gr.Markdown("### 功能开发中\n此功能将在后续版本中实现...")
        
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
                    enable_short_subtitles=False,
                    only_preprocess=True  # 只进行预处理，不生成字幕
                )
                
                if result['success']:
                    file_name = os.path.basename(actual_file_path)
                    processed_path = result.get('processed_video_path', '')
                    processed_name = os.path.basename(processed_path)
                    
                    return (
                        f"""### ✅ 上传成功
- **原始文件**: {file_name}
- **处理后文件**: {processed_name}
- **保存位置**: {processed_path}
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
        
        def generate_subtitles(video_selection, enable_translation, enable_short_subtitles):
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
                    enable_short_subtitles=enable_short_subtitles,
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
- **短字幕模式**: {'是' if enable_short_subtitles else '否'}
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
                return "### ❌ 错误\n请先选择视频", "## ℹ️ 系统状态\n等待选择视频", gr.update(visible=False)
            
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
                                gr.update(visible=False)
                            )
                    else:
                        return (
                            "### ❌ 错误\n视频选择格式错误",
                            "## ℹ️ 系统状态\n视频选择格式错误",
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
                                gr.update(visible=False)
                            )
                    else:
                        return (
                            "### ❌ 错误\n视频选择格式错误",
                            "## ℹ️ 系统状态\n视频选择格式错误",
                            gr.update(visible=False)
                        )
                
                # 获取视频信息
                series_list = db_manager.get_series(video_id)
                if not series_list:
                    LOG.error(f"未找到ID为 {video_id} 的视频")
                    return (
                        "### ❌ 错误\n未找到选择的视频",
                        "## ℹ️ 系统状态\n无法找到选择的视频",
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
                    
                    # 准备表格数据
                    table_data = []
                    for kw in extracted_keywords:
                        table_data.append([
                            kw.get('id', 0),
                            kw.get('key_word', ''),
                            kw.get('phonetic_symbol', ''),
                            kw.get('explain_text', ''),
                            kw.get('coca', 0),
                            kw.get('subtitle_id', 0)
                        ])
                    
                    # 更新表格
                    return (
                        f"""### ✅ 关键词提取完成
- **视频**: {series['name']}
- **字幕数**: {len(subtitles)}
- **提取单词数**: {len(extracted_keywords)}
- **成功保存**: {saved_count}
- **COCA更新**: {'已更新' if update_coca else '未更新'}
                        """,
                        "## ℹ️ 系统状态\n关键词提取完成，可以进行下一步",
                        gr.update(visible=True, value=table_data)  # 显示关键词表格并更新数据
                    )
                
                except ImportError:
                    LOG.error("关键词提取模块未找到")
                    return (
                        "### ❌ 错误\n关键词提取模块未找到",
                        "## ℹ️ 系统状态\n缺少关键词提取功能模块",
                        gr.update(visible=False)
                    )
                except Exception as e:
                    LOG.error(f"提取关键词时出错: {e}")
                    import traceback
                    LOG.error(traceback.format_exc())
                    return (
                        f"### ❌ 提取失败\n{str(e)}",
                        f"## ℹ️ 系统状态\n关键词提取失败: {str(e)}",
                        gr.update(visible=False)
                    )
            
            except Exception as e:
                LOG.error(f"提取关键词时发生错误: {str(e)}")
                return (
                    f"### ❌ 发生错误\n{str(e)}",
                    f"## ℹ️ 系统状态\n关键词提取失败: {str(e)}",
                    gr.update(visible=False)
                )
        
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
            load_video_list,
            inputs=[],
            outputs=[video_dropdown, video_dropdown_upload]
        ).then(
            # 更新带字幕的视频下拉框
            load_subtitle_videos,
            inputs=[],
            outputs=[subtitle_video_dropdown]
        )
        
        # 步骤2: 字幕生成
        # 设置tab切换时的事件，确保下拉框选项是最新的
        tab2.select(
            load_video_list,
            inputs=[],
            outputs=[video_dropdown, video_dropdown_upload]
        )
        
        generate_button.click(
            generate_subtitles,
            inputs=[video_dropdown, translation_checkbox, short_subtitle_checkbox],
            outputs=[result_text, translation_text, subtitle_preview, subtitle_gen_result, status_md]
        ).then(
            # 更新带字幕的视频下拉框
            load_subtitle_videos,
            inputs=[],
            outputs=[subtitle_video_dropdown]
        )
        
        # 上传字幕
        subtitle_upload_btn.click(
            upload_subtitle_file,
            inputs=[video_dropdown_upload, subtitle_file_input],
            outputs=[subtitle_upload_result, status_md]
        ).then(
            # 更新带字幕的视频下拉框
            load_subtitle_videos,
            inputs=[],
            outputs=[subtitle_video_dropdown]
        )
        
        # 步骤3: 关键词提取
        # 设置tab切换时的事件，确保下拉框选项是最新的
        tab3.select(
            load_subtitle_videos,
            inputs=[],
            outputs=[subtitle_video_dropdown]
        )
        
        extract_button.click(
            extract_keywords,
            inputs=[subtitle_video_dropdown, coca_checkbox],
            outputs=[keywords_result, status_md, keywords_table]
        )
        
        # 添加界面加载事件，确保在界面加载时就加载所有下拉框选项
        interface.load(
            load_video_list,
            inputs=[],
            outputs=[video_dropdown, video_dropdown_upload]
        ).then(
            load_subtitle_videos,
            inputs=[],
            outputs=[subtitle_video_dropdown]
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
    interface.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )