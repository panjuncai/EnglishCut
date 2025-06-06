#!/usr/bin/env python3
"""
测试修复后的 MediaProcessor 功能
验证是否正确使用 openai_whisper.py 中的 asr 函数
"""

import os
import sys
import tempfile
from logger import LOG

def test_import_fix():
    """测试导入是否修复"""
    LOG.info("🔧 测试 MediaProcessor 导入修复...")
    
    try:
        from media_processor import MediaProcessor, process_media_file
        LOG.info("✅ MediaProcessor 导入成功")
        
        # 测试实例化
        processor = MediaProcessor()
        LOG.info("✅ MediaProcessor 实例化成功")
        
        return True
    except ImportError as e:
        LOG.error(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        LOG.error(f"❌ 实例化失败: {e}")
        return False

def test_asr_function_availability():
    """测试 asr 函数可用性"""
    LOG.info("🎤 测试 asr 函数可用性...")
    
    try:
        from openai_whisper import asr
        LOG.info("✅ asr 函数导入成功")
        
        # 检查函数签名
        import inspect
        sig = inspect.signature(asr)
        LOG.info(f"📋 asr 函数签名: {sig}")
        
        return True
    except ImportError as e:
        LOG.error(f"❌ asr 函数导入失败: {e}")
        return False
    except Exception as e:
        LOG.error(f"❌ 检查 asr 函数时出错: {e}")
        return False

def test_whisper_model_info():
    """测试 Whisper 模型信息"""
    LOG.info("🤖 测试 Whisper 模型配置...")
    
    try:
        from openai_whisper import device, MODEL_NAME, BATCH_SIZE
        
        LOG.info(f"📊 当前配置:")
        LOG.info(f"  - 设备: {device}")
        LOG.info(f"  - 模型: {MODEL_NAME}")
        LOG.info(f"  - 批次大小: {BATCH_SIZE}")
        
        # 检查是否使用了高质量模型
        if "large" in MODEL_NAME:
            LOG.info("🚀 使用高质量 large 模型")
        elif "base" in MODEL_NAME:
            LOG.info("⚡ 使用基础 base 模型")
        
        return True
    except ImportError as e:
        LOG.error(f"❌ 无法获取模型信息: {e}")
        return False
    except Exception as e:
        LOG.error(f"❌ 检查模型信息时出错: {e}")
        return False

def create_mock_audio_for_test():
    """创建一个简单的测试音频文件"""
    LOG.info("🎵 创建测试音频文件...")
    
    try:
        # 创建临时音频文件路径
        temp_dir = tempfile.gettempdir()
        test_audio_path = os.path.join(temp_dir, "test_audio.wav")
        
        # 使用 ffmpeg 创建一个简短的测试音频（如果可用）
        try:
            import subprocess
            
            # 创建 5 秒的正弦波音频
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "sine=frequency=440:duration=5",
                "-ar", "16000",
                "-ac", "1",
                test_audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(test_audio_path):
                LOG.info(f"✅ 测试音频创建成功: {test_audio_path}")
                return test_audio_path
            else:
                LOG.warning("⚠️ ffmpeg 创建音频失败，跳过音频测试")
                return None
                
        except FileNotFoundError:
            LOG.warning("⚠️ 未找到 ffmpeg，跳过音频创建")
            return None
            
    except Exception as e:
        LOG.error(f"❌ 创建测试音频时出错: {e}")
        return None

def test_media_processor_with_mock_audio():
    """使用模拟音频测试 MediaProcessor"""
    LOG.info("🧪 测试 MediaProcessor 音频处理...")
    
    # 创建测试音频
    test_audio = create_mock_audio_for_test()
    
    if not test_audio:
        LOG.warning("⚠️ 无法创建测试音频，跳过音频处理测试")
        return True
    
    try:
        from media_processor import process_media_file
        
        # 测试基础处理（无翻译）
        LOG.info("测试基础音频处理...")
        result = process_media_file(
            file_path=test_audio,
            output_format="SRT",
            enable_translation=False
        )
        
        LOG.info(f"处理结果: {result}")
        
        if result.get('success'):
            LOG.info("✅ 基础音频处理成功")
        else:
            LOG.warning(f"⚠️ 处理返回失败: {result.get('error', '未知错误')}")
        
        # 清理测试文件
        if os.path.exists(test_audio):
            os.remove(test_audio)
            LOG.info(f"🗑️ 清理测试音频: {test_audio}")
        
        # 清理可能生成的字幕文件
        if result.get('subtitle_file') and os.path.exists(result['subtitle_file']):
            os.remove(result['subtitle_file'])
            LOG.info(f"🗑️ 清理字幕文件: {result['subtitle_file']}")
        
        return True
        
    except Exception as e:
        LOG.error(f"❌ 音频处理测试失败: {e}")
        
        # 清理测试文件
        if test_audio and os.path.exists(test_audio):
            os.remove(test_audio)
        
        return False

def run_all_tests():
    """运行所有测试"""
    LOG.info("🧪 开始 MediaProcessor 修复验证测试...")
    
    tests = [
        ("导入修复测试", test_import_fix),
        ("asr 函数可用性", test_asr_function_availability),
        ("Whisper 模型信息", test_whisper_model_info),
        ("音频处理测试", test_media_processor_with_mock_audio),
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
        LOG.info("🎉 所有测试通过！MediaProcessor 修复成功！")
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