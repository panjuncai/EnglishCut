#!/usr/bin/env python3
"""
更新关键词选择状态工具

此脚本用于批量更新关键词的选择状态，可以按照不同规则选择关键词。
"""

import sys
import os
import argparse

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.database import db_manager
from src.logger import LOG

def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="更新关键词选择状态工具")
    parser.add_argument('series_id', type=int, help="系列ID")
    parser.add_argument(
        '--rule', 
        type=str, 
        choices=['all', 'none', 'coca5000', 'coca10000'], 
        default='coca5000',
        help="选择规则：all=全部选择，none=全部不选，coca5000=选择COCA>5000，coca10000=选择COCA>10000"
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    LOG.info(f"🔄 开始更新系列 {args.series_id} 的关键词选择状态，规则: {args.rule}")
    
    # 获取系列信息
    series_list = db_manager.get_series(args.series_id)
    if not series_list:
        LOG.error(f"❌ 找不到系列 {args.series_id}")
        return 1
    
    series_name = series_list[0]['name']
    LOG.info(f"📋 系列名称: {series_name}")
    
    # 执行批量更新
    result = db_manager.batch_update_keyword_selection(args.series_id, args.rule)
    
    if result['success']:
        LOG.info(f"✅ 成功更新 {result['updated_count']} 个关键词的选择状态")
        
        # 获取更新后的选中关键词数量
        keywords = db_manager.get_keywords(series_id=args.series_id)
        selected_count = sum(1 for kw in keywords if kw.get('is_selected', 0) == 1)
        
        LOG.info(f"📊 统计信息:")
        LOG.info(f"  - 总关键词数: {len(keywords)}")
        LOG.info(f"  - 已选中关键词: {selected_count}")
        LOG.info(f"  - 未选中关键词: {len(keywords) - selected_count}")
        
        return 0
    else:
        LOG.error(f"❌ 更新失败: {result.get('error', '未知错误')}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 