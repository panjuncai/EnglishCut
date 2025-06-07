#!/usr/bin/env python3
"""
测试下拉框修复后的逻辑
"""

import sys
import os
# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gradio_server import load_video_list, load_subtitle_videos
from src.logger import LOG

def test_dropdown_functions():
    """测试下拉框相关函数的返回值"""
    print("\n=== 测试下拉框相关函数 ===\n")
    
    # 测试load_video_list函数
    print("测试load_video_list函数:")
    try:
        result = load_video_list()
        
        # 检查返回值类型
        if isinstance(result, tuple) and len(result) == 2:
            video_dropdown, video_dropdown_upload = result
            print(f"✅ 返回值是元组，长度为{len(result)}")
            print(f"✅ 第一个下拉框选项数量: {len(video_dropdown)}")
            print(f"✅ 第二个下拉框选项数量: {len(video_dropdown_upload)}")
            
            # 打印前三个选项(如果有)
            for i, option in enumerate(video_dropdown[:3]):
                print(f"  选项 {i+1}: {option}")
        else:
            print(f"❌ 返回值不是元组或长度不为2: {type(result)}, {result}")
    except Exception as e:
        print(f"❌ 测试load_video_list时出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")
    
    # 测试load_subtitle_videos函数
    print("测试load_subtitle_videos函数:")
    try:
        result = load_subtitle_videos()
        
        # 检查返回值类型
        if isinstance(result, list):
            print(f"✅ 返回值是列表，长度为{len(result)}")
            
            # 打印前三个选项(如果有)
            for i, option in enumerate(result[:3]):
                print(f"  选项 {i+1}: {option}")
        else:
            print(f"❌ 返回值不是列表: {type(result)}, {result}")
    except Exception as e:
        print(f"❌ 测试load_subtitle_videos时出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    test_dropdown_functions() 