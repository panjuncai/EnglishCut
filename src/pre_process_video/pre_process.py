#!/usr/bin/env python3
"""
视频预处理模块
添加顶部标题和底部文字区域，不占据原视频空间
"""

import os
import subprocess
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
LOG = logging.getLogger(__name__)

class VideoProcessor:
    """视频处理器"""
    
    def __init__(self, input_dir="input", output_dir="output"):
        """初始化处理器"""
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        LOG.info(f"🎬 视频处理器初始化完成")
    
    def process_video(self, 
                    input_filename, 
                    output_filename=None, 
                    top_text="第二遍：词汇与文法分析", 
                    bottom_text="This is test 这是测试"):
        """
        处理视频，创建9:16竖屏视频，添加专业的顶部和底部区域
        
        参数:
        - input_filename: 输入视频文件名
        - output_filename: 输出视频文件名，如果为None则自动生成
        - top_text: 顶部文字
        - bottom_text: 底部文字（可用于关键词或短语介绍）
        
        返回:
        - bool: 处理是否成功
        """
        try:
            # 构建完整文件路径
            input_path = os.path.join(self.input_dir, input_filename)
            
            # 如果未指定输出文件名，自动生成
            if output_filename is None:
                base_name = os.path.splitext(input_filename)[0]
                output_filename = f"{base_name}_out.mp4"
            
            output_path = os.path.join(self.output_dir, output_filename)
            
            LOG.info(f"🔄 开始处理视频: {input_filename}")
            LOG.info(f"📊 顶部文字: {top_text}")
            LOG.info(f"📊 底部文字: {bottom_text}")
            
            # 构建视频过滤器
            video_filter = self._build_video_filter(top_text, bottom_text)
            
            # 构建ffmpeg命令
            cmd = [
                'ffmpeg', '-y',  # 覆盖输出文件
                '-i', input_path,  # 输入视频
                '-vf', video_filter,  # 视频滤镜
                '-aspect', '9:16',  # 设置宽高比为9:16（抖音标准）
                '-c:a', 'copy',  # 音频直接复制
                '-preset', 'medium',  # 编码预设
                '-crf', '23',  # 质量控制
                output_path
            ]
            
            LOG.info(f"🎬 执行FFmpeg命令")
            
            # 执行FFmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                LOG.info(f"✅ 视频处理成功: {output_path}")
                return True
            else:
                LOG.error(f"❌ FFmpeg错误: {stderr}")
                return False
                
        except Exception as e:
            LOG.error(f"❌ 视频处理失败: {str(e)}")
            return False
    
    def _build_video_filter(self, top_text, bottom_text):
        """
        构建FFmpeg视频滤镜
        
        参数:
        - top_text: 顶部文字
        - bottom_text: 底部文字
        
        返回:
        - str: FFmpeg滤镜字符串
        """
        # 视频滤镜：直接从原视频中挖出9:16比例的部分，不变形，然后添加顶部和底部区域
        # 顶部占10%，主视频占60%，底部占30%
        filter_chain = [
            # 第1步：从原16:9视频中央挖出9:16比例的部分
            "crop=ih*9/16:ih:iw/2-ih*9/16/2:0",  # 从中心裁剪9:16比例
            
            # 第2步：缩放到标准尺寸
            "scale=720:1280",  # 缩放到标准的9:16尺寸
            
            # 第3步：顶部区域 - 创建完全不透明的黑色背景
            "drawbox=x=0:y=0:w=720:h=128:color=black@1.0:t=fill",  # 完全不透明的黑色背景
            
            # 第4步：添加顶部文字（调大白色字体，使用粗体字体文件）
            f"drawtext=text='{top_text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=64-text_h/2:fontfile=Microsoft YaHei:shadowcolor=black@0.6:shadowx=1:shadowy=1:box=1:boxcolor=black@0.2:boxborderw=5",  # 使用Heavy字重代替Medium字重
            
            # 第5步：添加底部文字（黄色字体带黑色描边，无背景）
            f"drawtext=text='{bottom_text}':fontcolor=yellow:fontsize=36:x=(w-text_w)/2:y=920-text_h/2:fontfile=Microsoft YaHei:bordercolor=black:borderw=2",  # 黄色字体带黑色描边
        ]
        
        return ','.join(filter_chain)

def main():
    """主函数"""
    processor = VideoProcessor()
    
    # 处理 3.mp4 视频
    success = processor.process_video("3.mp4")
    
    if success:
        LOG.info("✅ 所有视频处理完成")
    else:
        LOG.error("❌ 视频处理失败")

if __name__ == "__main__":
    main()
