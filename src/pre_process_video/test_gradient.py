#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess

def create_style_preview():
    """创建一个样式预览图，展示带亮黄色背景的单词展示效果"""
    
    # 计算文本位置和矩形尺寸
    base_y = 700  # 矩形框顶部Y坐标，从900调整到700，往上移
    line_height_1 = 110  # 第一行(英文大字)到第二行(中文小字)的行高
    line_height_2 = 60   # 第二行(中文小字)到第三行(音标小字)的行高
    padding_y = 30  # 垂直内边距
    
    # 计算三行文本的垂直位置
    word_y = base_y + padding_y
    meaning_y = word_y + line_height_1
    phonetic_y = meaning_y + line_height_2
    
    # 设置字体大小
    word_fontsize = 128     # 英文单词字体大小 - 英文大字
    meaning_fontsize = 48   # 中文释义字体大小 - 中文中字
    phonetic_fontsize = 26  # 音标字体大小 - 音标小字
    
    # 矩形高度
    rect_height = padding_y + line_height_1 + line_height_2 + padding_y + 10  # 加10像素作为底部额外边距
    
    # 模拟根据文本内容计算宽度
    word = "test"
    meaning = "测试"
    phonetic = "/test/"
    
    # 更精确地估算字符宽度（考虑更新的字体大小）
    word_width = len(word) * 48      # 128px字体下英文字符约48像素
    meaning_width = len(meaning) * 28  # 48px字体下中文字符约28像素
    phonetic_width = len(phonetic) * 10  # 26px字体下音标字符约10像素
    
    # 取最宽的文本长度
    max_text_len = max(word_width, meaning_width, phonetic_width)
    
    # 矩形宽度和位置
    center_x = 360  # 屏幕中心水平坐标
    padding_x = 40  # 左右各20像素的内边距
    rect_width = max(250, min(max_text_len + padding_x, 700))
    rect_x = center_x - rect_width/2
    
    # 创建简单的测试图像
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', 
        '-i', 'color=black:s=720x1280',
        '-vf',
        # 背景
        'drawbox=x=0:y=0:w=720:h=1280:color=black@1.0:t=fill,' +
        # 底部区域
        'drawbox=x=0:y=1080:w=720:h=200:color=#fbfbf3@1.0:t=fill,' +
        # 单词展示背景 - 带亮黄色背景
        f'drawbox=x={rect_x}:y={base_y}:w={rect_width}:h={rect_height}:color=#FFFF00@1.0:t=fill,' +
        # 单词文本 - 英文单词
        f'drawtext=text={word}:fontcolor=black:fontsize={word_fontsize}:x={center_x}-text_w/2:y={word_y}:fontfile=/System/Library/Fonts/STHeiti\\ Light.ttc,' +
        # 中文文本
        f'drawtext=text={meaning}:fontcolor=black:fontsize={meaning_fontsize}:x={center_x}-text_w/2:y={meaning_y}:fontfile=/System/Library/Fonts/STHeiti\\ Light.ttc,' +
        # 音标文本
        f'drawtext=text={phonetic}:fontcolor=black:fontsize={phonetic_fontsize}:x={center_x}-text_w/2:y={phonetic_y}:fontfile=/System/Library/Fonts/STHeiti\\ Light.ttc',
        '-frames:v', '1',
        'style_preview.jpg'
    ]
    
    subprocess.run(cmd)
    print("预览图生成成功：style_preview.jpg")

if __name__ == "__main__":
    create_style_preview() 