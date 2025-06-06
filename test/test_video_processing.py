#!/usr/bin/env python3
"""
视频处理功能测试脚本
测试视频文件的音频提取、语音识别和字幕生成功能
"""

import os
import sys
import tempfile
from src.logger import LOG
from media_processor import process_media_file, get_media_formats_info
from file_detector import validate_file, get_file_info, FileType
from video_processor import check_ffmpeg_availability, extract_audio_from_video, get_video_info

def test_ffmpeg_availability():
    """测试 ffmpeg 可用性"""
    LOG.info("🔧 测试 ffmpeg 可用性...")
    
    if check_ffmpeg_availability():
        LOG.info("✅ ffmpeg 可用")
        return True
    else:
        LOG.error("❌ ffmpeg 不可用，无法处理视频文件")
        return False

def test_supported_formats():
    """测试支持的格式信息"""
    LOG.info("📋 测试支持的格式信息...")
    
    try:
        formats_info = get_media_formats_info()
        
        LOG.info(f"📁 支持的音频格式: {formats_info['audio_formats']}")
        LOG.info(f"🎬 支持的视频格式: {formats_info['video_formats']}")
        LOG.info(f"📝 支持的字幕格式: {formats_info['subtitle_formats']}")
        LOG.info(f"📄 格式描述: {formats_info['description']}")
        
        return True
    except Exception as e:
        LOG.error(f"❌ 获取格式信息失败: {e}")
        return False

def test_file_validation():
    """测试文件验证功能"""
    LOG.info("🔍 测试文件验证功能...")
    
    # 测试不存在的文件
    is_valid, file_type, error_msg = validate_file("nonexistent.mp4")
    LOG.info(f"测试不存在文件: valid={is_valid}, type={file_type}, error='{error_msg}'")
    
    # 测试空路径
    is_valid, file_type, error_msg = validate_file("")
    LOG.info(f"测试空路径: valid={is_valid}, type={file_type}, error='{error_msg}'")
    
    # 测试不支持的格式
    test_file = "test.xyz"
    with open(test_file, 'w') as f:
        f.write("test")
    
    is_valid, file_type, error_msg = validate_file(test_file)
    LOG.info(f"测试不支持格式: valid={is_valid}, type={file_type}, error='{error_msg}'")
    
    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
    
    return True

def create_test_video():
    """创建一个测试视频文件（使用 ffmpeg 生成）"""
    LOG.info("🎬 创建测试视频文件...")
    
    if not check_ffmpeg_availability():
        LOG.error("❌ 需要 ffmpeg 来创建测试视频")
        return None
    
    try:
        # 创建临时视频文件路径
        temp_dir = tempfile.gettempdir()
        test_video_path = os.path.join(temp_dir, "test_video.mp4")
        
        # 使用 ffmpeg 创建一个 10 秒的测试视频（含音频）
        import subprocess
        
        cmd = [
            "ffmpeg", "-y",  # 覆盖输出文件
            "-f", "lavfi",   # 使用 lavfi 输入
            "-i", "testsrc2=duration=10:size=320x240:rate=1",  # 10秒测试视频
            "-f", "lavfi",   # 音频输入
            "-i", "sine=frequency=1000:duration=10",  # 1000Hz 正弦波音频
            "-c:v", "libx264",  # 视频编码器
            "-c:a", "aac",      # 音频编码器
            "-shortest",        # 使用最短的流长度
            test_video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(test_video_path):
            LOG.info(f"✅ 测试视频创建成功: {test_video_path}")
            return test_video_path
        else:
            LOG.error(f"❌ 创建测试视频失败: {result.stderr}")
            return None
            
    except Exception as e:
        LOG.error(f"❌ 创建测试视频时发生错误: {e}")
        return None

def test_video_info(video_path):
    """测试视频信息获取"""
    LOG.info(f"📊 测试视频信息获取: {video_path}")
    
    try:
        # 获取文件信息
        file_info = get_file_info(video_path)
        if file_info:
            LOG.info(f"文件信息: {file_info}")
        
        # 获取视频详细信息
        video_info = get_video_info(video_path)
        if video_info:
            LOG.info(f"视频信息: {video_info}")
        
        return True
    except Exception as e:
        LOG.error(f"❌ 获取视频信息失败: {e}")
        return False

def test_audio_extraction(video_path):
    """测试音频提取功能"""
    LOG.info(f"🎵 测试音频提取: {video_path}")
    
    try:
        # 创建临时音频文件路径
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, "extracted_audio.wav")
        
        # 提取音频
        success = extract_audio_from_video(video_path, audio_path)
        
        if success and os.path.exists(audio_path):
            LOG.info(f"✅ 音频提取成功: {audio_path}")
            
            # 检查音频文件大小
            audio_size = os.path.getsize(audio_path)
            LOG.info(f"音频文件大小: {audio_size} 字节")
            
            # 清理临时音频文件
            os.remove(audio_path)
            return True
        else:
            LOG.error("❌ 音频提取失败")
            return False
            
    except Exception as e:
        LOG.error(f"❌ 音频提取测试失败: {e}")
        return False

def test_complete_video_processing(video_path):
    """测试完整的视频处理流程"""
    LOG.info(f"🚀 测试完整视频处理流程: {video_path}")
    
    try:
        # 测试 SRT 格式
        LOG.info("测试 SRT 格式字幕生成...")
        result_srt = process_media_file(
            file_path=video_path,
            output_format="SRT",
            enable_translation=False
        )
        
        LOG.info(f"SRT 处理结果: {result_srt}")
        
        # 测试双语 SRT 格式
        LOG.info("测试双语 SRT 格式字幕生成...")
        result_bilingual = process_media_file(
            file_path=video_path,
            output_format="SRT",
            enable_translation=True
        )
        
        LOG.info(f"双语 SRT 处理结果: {result_bilingual}")
        
        # 清理生成的文件
        for result in [result_srt, result_bilingual]:
            if result.get('success') and result.get('subtitle_file'):
                subtitle_file = result['subtitle_file']
                if os.path.exists(subtitle_file):
                    os.remove(subtitle_file)
                    LOG.info(f"🗑️ 清理字幕文件: {subtitle_file}")
        
        return True
        
    except Exception as e:
        LOG.error(f"❌ 完整处理测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    LOG.info("🧪 开始视频处理功能测试...")
    
    tests = [
        ("ffmpeg 可用性", test_ffmpeg_availability),
        ("支持格式信息", test_supported_formats),
        ("文件验证功能", test_file_validation),
    ]
    
    # 基础测试
    for test_name, test_func in tests:
        LOG.info(f"\n--- 测试: {test_name} ---")
        try:
            if test_func():
                LOG.info(f"✅ {test_name} 测试通过")
            else:
                LOG.error(f"❌ {test_name} 测试失败")
                return False
        except Exception as e:
            LOG.error(f"❌ {test_name} 测试异常: {e}")
            return False
    
    # 如果 ffmpeg 可用，进行视频相关测试
    if check_ffmpeg_availability():
        LOG.info("\n--- 创建测试视频 ---")
        test_video = create_test_video()
        
        if test_video:
            video_tests = [
                ("视频信息获取", lambda: test_video_info(test_video)),
                ("音频提取", lambda: test_audio_extraction(test_video)),
                ("完整处理流程", lambda: test_complete_video_processing(test_video)),
            ]
            
            for test_name, test_func in video_tests:
                LOG.info(f"\n--- 测试: {test_name} ---")
                try:
                    if test_func():
                        LOG.info(f"✅ {test_name} 测试通过")
                    else:
                        LOG.error(f"❌ {test_name} 测试失败")
                except Exception as e:
                    LOG.error(f"❌ {test_name} 测试异常: {e}")
            
            # 清理测试视频
            if os.path.exists(test_video):
                os.remove(test_video)
                LOG.info(f"🗑️ 清理测试视频: {test_video}")
        
        else:
            LOG.warning("⚠️ 无法创建测试视频，跳过视频相关测试")
    
    else:
        LOG.warning("⚠️ ffmpeg 不可用，跳过视频相关测试")
    
    LOG.info("\n🎉 视频处理功能测试完成！")
    return True

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        LOG.info("👋 测试被用户中断")
    except Exception as e:
        LOG.error(f"❌ 测试过程中发生意外错误: {e}")
        sys.exit(1) 