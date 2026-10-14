#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主程序入口 - AI 智能体 Top 10 股票热力榜

功能流程：
1. 获取 AI 智能体概念成分股
2. 阶段 1 粗排：按成交额 + 涨跌幅取前 30 只候选
3. 阶段 2 精选：获取资金流（失败剔除）+ 新闻，计算综合分
4. 生成 Top 10 报告（摘要 + 新闻链接）
5. 推送到 IM 平台（企业微信/飞书/钉钉/Telegram/邮件）

触发方式：
- 手动运行：python main.py
- 定时任务：GitHub Actions 每天 11:00（北京时间）

环境变量配置：
- CONCEPT_KEY: 概念标识（可选，默认"AI 智能体_同花顺"）
- TOP_N: 返回 Top N 只股票（可选，默认 10）
- CANDIDATE_N: 候选股票数量（可选，默认 30）
- 推送平台 Webhook URL（见 pusher.py）
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fetcher import get_trade_date
from src.scorer import get_top_stocks
from src.summarizer import generate_top_stocks_report, generate_news_link
from src.pusher import format_message, push_to_all_platforms

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    主函数
    """
    logger.info("=" * 80)
    logger.info("AI 智能体 Top 10 股票热力榜 - 开始运行")
    logger.info("=" * 80)
    
    # 读取配置
    concept_key = os.getenv('CONCEPT_KEY', 'AI 智能体_同花顺')
    top_n = int(os.getenv('TOP_N', '10'))
    candidate_n = int(os.getenv('CANDIDATE_N', '30'))
    
    logger.info(f"概念标识：{concept_key}")
    logger.info(f"返回 Top: {top_n}")
    logger.info(f"候选数量：{candidate_n}")
    
    try:
        # 步骤 1：获取最近一个交易日
        logger.info("\n[步骤 1] 获取最近一个交易日...")
        trade_date = get_trade_date()
        
        if not trade_date:
            logger.error("获取交易日失败")
            return False
        
        logger.info(f"最近一个交易日：{trade_date}")
        
        # 步骤 2：获取 Top N 股票
        logger.info(f"\n[步骤 2] 获取 Top {top_n} 股票（两阶段筛选）...")
        logger.info(f"  阶段 1：粗排取前 {candidate_n} 只候选")
        logger.info(f"  阶段 2：精选（资金流 + 新闻）")
        
        top_stocks_df = get_top_stocks(
            concept_key=concept_key,
            top_n=top_n,
            candidate_n=candidate_n
        )
        
        if top_stocks_df is None or len(top_stocks_df) == 0:
            logger.error("获取 Top 股票失败")
            return False
        
        logger.info(f"获取到 {len(top_stocks_df)} 只股票")
        
        # 步骤 3：获取新闻数据（用于生成摘要）
        logger.info(f"\n[步骤 3] 获取新闻数据...")
        news_data = {}
        
        for idx, (_, row) in enumerate(top_stocks_df.iterrows(), start=1):
            stock_code = row.get('stock_code', '')
            
            try:
                news_list = get_stock_news(stock_code, date=trade_date)
                news_data[stock_code] = news_list
                
                if news_list and len(news_list) > 0:
                    logger.info(f"  #{idx} {stock_code}: {len(news_list)} 条新闻")
                else:
                    logger.info(f"  #{idx} {stock_code}: 无新闻")
                    
            except Exception as e:
                logger.error(f"  #{idx} {stock_code}: 获取新闻失败 - {type(e).__name__}: {e}")
                news_data[stock_code] = []
        
        # 步骤 4：生成报告
        logger.info(f"\n[步骤 4] 生成报告...")
        report_list = generate_top_stocks_report(top_stocks_df, news_data)
        
        if not report_list or len(report_list) == 0:
            logger.error("生成报告失败")
            return False
        
        logger.info(f"生成 {len(report_list)} 条报告")
        
        # 步骤 5：格式化消息
        logger.info(f"\n[步骤 5] 格式化消息...")
        message = format_message(report_list, trade_date)
        
        logger.info("生成的消息预览：")
        logger.info("-" * 60)
        for line in message.split('\n')[:15]:  # 预览前 15 行
            logger.info(line)
        logger.info("...")
        logger.info("-" * 60)
        
        # 步骤 6：推送到 IM 平台
        logger.info(f"\n[步骤 6] 推送到 IM 平台...")
        push_results = push_to_all_platforms(message, trade_date)
        
        # 输出推送结果
        logger.info("\n推送结果：")
        success_count = 0
        for platform, success in push_results.items():
            status = "✓ 成功" if success else "✗ 失败/未配置"
            logger.info(f"  {platform}: {status}")
            if success:
                success_count += 1
        
        if success_count > 0:
            logger.info(f"\n✓ 推送完成：{success_count} 个平台成功")
        else:
            logger.warning("\n⚠️ 没有平台推送成功（可能都未配置）")
        
        # 完成
        logger.info("\n" + "=" * 80)
        logger.info("AI 智能体 Top 10 股票热力榜 - 运行完成")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n程序异常：{type(e).__name__}: {e}", exc_info=True)
        logger.error("\n" + "=" * 80)
        logger.error("AI 智能体 Top 10 股票热力榜 - 运行失败")
        logger.error("=" * 80)
        return False


# 需要导入 get_stock_news，避免循环导入
from src.fetcher import get_stock_news


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
