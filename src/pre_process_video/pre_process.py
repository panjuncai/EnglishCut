#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
from pathlib import Path
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
                    top_text="第三遍:完全消化", 
                    bottom_text="This is test 这是测试",
                    keyword_text=None):
        """
        处理视频，创建9:16竖屏视频，添加专业的顶部和底部区域
        
        参数:
        - input_filename: 输入视频文件名
        - output_filename: 输出视频文件名，如果为None则自动生成
        - top_text: 顶部文字
        - bottom_text: 底部文字（可用于关键词或短语介绍）
        - keyword_text: 重点单词信息，格式为 {"word": "test", "phonetic": "[test]", "meaning": "测试"}
        
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
            video_filter = self._build_video_filter(top_text, bottom_text, keyword_text)
            
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
    
    def _build_video_filter(self, top_text, bottom_text, keyword_text=None):
        """
        构建FFmpeg视频滤镜
        
        参数:
        - top_text: 顶部文字
        - bottom_text: 底部文字
        - keyword_text: 重点单词信息，格式为 {"word": "test", "phonetic": "[test]", "meaning": "测试"}
        
        返回:
        - str: FFmpeg滤镜字符串
        """
        # 指定字体路径，优先使用抖音字体，找不到再使用苹方
        douyin_font = '/Users/panjc/Library/Fonts/DouyinSansBold.ttf'
        # 备选字体
        system_fonts = [
            '/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc',  # 苹方
            '/System/Library/Fonts/STHeiti Light.ttc',  # 黑体-简 细体
            '/System/Library/Fonts/Hiragino Sans GB.ttc',  # 冬青黑体
            'Arial.ttf'  # 默认Arial
        ]
        
        # 检查抖音字体是否存在
        if not os.path.exists(douyin_font):
            print(f"警告: 抖音字体文件不存在: {douyin_font}")
            # 找到第一个存在的系统字体
            for font in system_fonts:
                if os.path.exists(font):
                    print(f"使用备选字体: {font}")
                    douyin_font = font
                    break
        else:
            print(f"找到抖音字体: {douyin_font}")
        
        # 视频滤镜：从原视频中挖出9:16比例的部分，不变形，然后添加顶部和底部区域
        # 顶部占10%，主视频占60%，底部占适合4行字幕的高度
        filter_chain = [
            # 第1步：从原16:9视频中央挖出9:16比例的部分，忽略底部1/5的广告字幕
            # 原视频高度的4/5作为有效高度，在此基础上挖取9:16比例
            "crop=ih*4/5*9/16:ih*4/5:iw/2-ih*4/5*9/16/2:0",  # 从中心裁剪9:16比例，避开底部1/5区域
            
            # 第2步：缩放到标准尺寸
            "scale=720:1280",  # 缩放到标准的9:16尺寸
            
            # 第3步：顶部区域 - 创建完全不透明的黑色背景
            "drawbox=x=0:y=0:w=720:h=128:color=black@1.0:t=fill",  # 完全不透明的黑色背景
            
            # 第4步：底部区域 - 创建单一浅米色背景
            # 底部区域从1080像素开始，高度为200像素（适合4行字幕）
            "drawbox=x=0:y=1080:w=720:h=200:color=#fbfbf3@1.0:t=fill",  # 底部区域浅米色不透明背景
            
            # 第5步：添加顶部文字（调大白色字体，使用粗体字体文件）
            f"drawtext=text='{top_text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=64-text_h/2:fontfile='{douyin_font}':shadowcolor=black@0.6:shadowx=1:shadowy=1:box=1:boxcolor=black@0.2:boxborderw=5",
            
            # 第6步：添加底部文字（鲜亮黄色字体带粗黑色描边，模拟图片效果）
            # 使用更亮的黄色(#FFFF00)，增加描边宽度，使用粗体效果
            f"drawtext=text='{bottom_text}':fontcolor=#FFFF00:fontsize=36:x=(w-text_w)/2:y=1180-text_h/2:fontfile='{douyin_font}':bordercolor=black:borderw=4:box=0",
        ]
        
        # 第7步：如果提供了重点单词信息，添加单词展示区域
        if keyword_text and isinstance(keyword_text, dict):
            # 获取单词信息
            word = keyword_text.get('word', '')
            phonetic = keyword_text.get('phonetic', '')
            meaning = keyword_text.get('meaning', '')
            
            if word:
                # 字体大小设置
                word_fontsize = 128     # 英文单词字体大小 - 英文大字
                meaning_fontsize = 48   # 中文释义字体大小 - 中文中字
                phonetic_fontsize = 26  # 音标字体大小 - 音标小字
                
                # 计算文本垂直位置和行间距
                base_y = 830  # 矩形框顶部Y坐标，从900调整到830，往上移
                line_height_1 = 110  # 第一行(英文大字)到第二行(中文小字)的行高
                line_height_2 = 60   # 第二行(中文小字)到第三行(音标小字)的行高
                padding_y = 30  # 垂直内边距
                
                # 计算三行文本的垂直位置
                word_y = base_y + padding_y
                meaning_y = word_y + line_height_1
                phonetic_y = meaning_y + line_height_2
                
                # 根据单词长度调整宽度
                # 更精确地估算字符宽度（考虑更新的字体大小）
                word_width = len(word) * 48      # 128px字体下英文字符约48像素
                meaning_width = len(meaning) * 36 if meaning else 0   # 64px字体下中文字符约36像素
                phonetic_width = len(phonetic) * 10 if phonetic else 0  # 26px字体下音标字符约10像素
                
                # 取最宽的文本长度
                max_text_len = max(word_width, meaning_width, phonetic_width)
                
                # 计算宽度，使用更小的内边距
                padding_x = 40  # 左右各20像素的内边距
                rect_width = max(250, min(max_text_len + padding_x, 700))
                center_x = 360  # 屏幕中心水平坐标
                rect_x = center_x - rect_width/2
                
                # 计算矩形高度，考虑不同行高
                if meaning and phonetic:
                    # 全部三行
                    rect_height = padding_y + line_height_1 + line_height_2 + padding_y + 10
                elif meaning:
                    # 两行：单词+中文
                    rect_height = padding_y + line_height_1 + padding_y
                elif phonetic:
                    # 两行：单词+音标
                    rect_height = padding_y + line_height_1 + padding_y
                else:
                    # 只有单词一行
                    rect_height = padding_y + 90 + padding_y  # 单词行高设为90
                
                # 添加亮黄色背景框 - 使用亮黄色 #FFFF00
                filter_chain.append(f"drawbox=x={rect_x}:y={base_y}:w={rect_width}:h={rect_height}:color=#FFFF00@1.0:t=fill")
                
                # 在背景框上添加文本
                # 添加单词文本（英文单词）
                filter_chain.append(f"drawtext=text='{word}':fontcolor=black:fontsize={word_fontsize}:x={center_x}-text_w/2:y={word_y}:fontfile='{douyin_font}'")
                
                # 如果有中文释义，添加释义文本
                if meaning:
                    filter_chain.append(f"drawtext=text='{meaning}':fontcolor=black:fontsize={meaning_fontsize}:x={center_x}-text_w/2:y={meaning_y}:fontfile='{douyin_font}'")
                
                # 如果有音标，添加音标文本
                if phonetic:
                    filter_chain.append(f"drawtext=text='{phonetic}':fontcolor=black:fontsize={phonetic_fontsize}:x={center_x}-text_w/2:y={phonetic_y}:fontfile='{douyin_font}'")
        
        return ','.join(filter_chain)

def main():
    """主函数"""
    processor = VideoProcessor()
    
    # 示例：处理视频并添加重点单词展示
    keyword = {
        "word": "test",
        "phonetic": "/test/",  # 避免使用方括号，可能导致命令行解析问题
        "meaning": "测试"
    }
    
    # 处理 3.mp4 视频
    success = processor.process_video(
        "3.mp4", 
        keyword_text=keyword
    )
    
    if success:
        LOG.info("✅ 所有视频处理完成")
    else:
        LOG.error("❌ 视频处理失败")

if __name__ == "__main__":
    main()
