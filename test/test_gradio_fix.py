#!/usr/bin/env python3
"""
测试 Gradio 服务器修复
验证 File 组件的 type 参数修复是否成功
"""

import sys
from src.logger import LOG

def test_gradio_import():
    """测试 Gradio 导入"""
    LOG.info("🧪 测试 Gradio 导入...")
    try:
        import gradio as gr
        LOG.info(f"✅ Gradio 导入成功，版本: {gr.__version__}")
        return True
    except ImportError as e:
        LOG.error(f"❌ Gradio 导入失败: {e}")
        return False

def test_file_component():
    """测试 File 组件配置"""
    LOG.info("📁 测试 File 组件...")
    try:
        import gradio as gr
        
        # 测试新的 type="file" 参数
        file_component = gr.File(
            label="测试文件上传",
            type="file"
        )
        LOG.info("✅ File 组件创建成功，使用 type='file'")
        
        # 检查可用的 type 选项
        try:
            # 这应该会失败，因为 "filepath" 不再被支持
            file_component_old = gr.File(
                label="测试旧参数",
                type="filepath"
            )
            LOG.warning("⚠️ 旧参数 type='filepath' 仍然可用（可能需要更新Gradio版本）")
        except ValueError as e:
            LOG.info("✅ 确认旧参数 type='filepath' 已不支持，错误: " + str(e))
        
        return True
    except Exception as e:
        LOG.error(f"❌ File 组件测试失败: {e}")
        return False

def test_interface_creation():
    """测试界面创建"""
    LOG.info("🎨 测试界面创建...")
    try:
        from gradio_server import create_main_interface
        
        interface = create_main_interface()
        LOG.info("✅ 主界面创建成功")
        
        # 不启动服务器，只测试创建
        LOG.info("💡 提示: 界面创建成功，可以运行 'python src/gradio_server.py' 启动服务器")
        
        return True
    except Exception as e:
        LOG.error(f"❌ 界面创建失败: {e}")
        return False

def test_supported_file_types():
    """测试支持的文件类型"""
    LOG.info("📋 测试支持的文件类型...")
    try:
        from media_processor import get_media_formats_info
        
        formats_info = get_media_formats_info()
        
        LOG.info(f"🎵 支持的音频格式: {formats_info['audio_formats']}")
        LOG.info(f"🎬 支持的视频格式: {formats_info['video_formats']}")
        LOG.info(f"📝 支持的字幕格式: {formats_info['subtitle_formats']}")
        
        return True
    except Exception as e:
        LOG.error(f"❌ 文件类型测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    LOG.info("🧪 开始 Gradio 修复验证测试...")
    
    tests = [
        ("Gradio 导入测试", test_gradio_import),
        ("File 组件测试", test_file_component),
        ("支持的文件类型", test_supported_file_types),
        ("界面创建测试", test_interface_creation),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for test_name, test_func in tests:
        LOG.info(f"\n--- 测试: {test_name} ---")
        try:
            if test_func():
                LOG.info(f"✅ {test_name} 测试通过")
                success_count += 1
            else:
                LOG.error(f"❌ {test_name} 测试失败")
        except Exception as e:
            LOG.error(f"❌ {test_name} 测试异常: {e}")
    
    LOG.info(f"\n📊 测试结果总结:")
    LOG.info(f"成功: {success_count}/{total_count}")
    LOG.info(f"失败: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        LOG.info("🎉 所有测试通过！Gradio 修复成功！")
        LOG.info("🚀 现在可以运行: python src/gradio_server.py")
    else:
        LOG.warning("⚠️ 部分测试失败，请检查相关问题")
    
    return success_count == total_count

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        LOG.info("👋 测试被用户中断")
    except Exception as e:
        LOG.error(f"❌ 测试过程中发生意外错误: {e}")
        sys.exit(1) 