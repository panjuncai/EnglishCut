#!/usr/bin/env python3
"""
批量更新数据库中的单引号为反引号
"""

import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.database import db_manager
from src.logger import LOG

def main():
    """执行单引号到反引号的批量替换"""
    LOG.info("🔄 开始执行单引号到反引号的批量替换...")
    
    # 执行替换
    result = db_manager.update_all_quotes_to_backticks()
    
    # 显示结果
    if result["success"]:
        LOG.info(f"✅ 单引号替换成功:")
        LOG.info(f"  - 更新了 {result['subtitle_count']} 条字幕")
        LOG.info(f"  - 更新了 {result['keyword_count']} 个关键词")
    else:
        LOG.error(f"❌ 单引号替换失败: {result.get('error', '未知错误')}")
    
    return 0 if result["success"] else 1

if __name__ == "__main__":
    sys.exit(main()) 