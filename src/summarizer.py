#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
摘要生成器

为每只股票生成 <50 字摘要 + 当日关键新闻链接

摘要格式：
{股票名} {涨跌幅}% 成交额{X}亿 主力净流入{Y}万 [最新新闻标题]

示例：
"协创数据 +5.23% 成交额 12.5 亿 主力净流入 3200 万 业绩增长超预期"

约束：
- 总字数 < 50 字（含标点）
- 数字保留 2 位小数
- 无新闻时省略新闻标题
"""

import logging
import pandas as pd
from typing import List, Dict

from src.llm_service import generate_stock_summary, calculate_news_score

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def format_amount(amount: float) -> str:
    """
    格式化成交额（元 -> 亿/万）
    
    Args:
        amount: 成交额（元）
    
    Returns:
        格式化字符串，如 "12.5 亿" 或 "8500 万"
    """
    if amount >= 1e8:
        return f"{amount / 1e8:.2f}亿"
    elif amount >= 1e4:
        return f"{amount / 1e4:.0f}万"
    else:
        return f"{amount:.0f}"


def format_net_flow(net_flow: float) -> str:
    """
    格式化主力净流入（元 -> 万）
    
    Args:
        net_flow: 主力净流入（元）
    
    Returns:
        格式化字符串，如 "3200 万" 或 "-1500 万"
    """
    return f"{net_flow / 1e4:.0f}万"


def generate_summary(stock_row: pd.Series, news_list: List[Dict] = None) -> str:
    """
    为单只股票生成摘要（<50 字）- 使用千问大模型
    
    Args:
        stock_row: 股票数据行（包含 short_name, change_pct, amount, net_flow）
        news_list: 新闻列表（可选）
    
    Returns:
        摘要字符串，< 50 字
    """
    # 提取数据
    short_name = stock_row.get('short_name', '未知')
    change_pct = float(stock_row.get('change_pct', 0))
    amount = float(stock_row.get('amount', 0))
    net_flow_raw = stock_row.get('net_flow', '0')
    
    # 格式化主力净流入
    if isinstance(net_flow_raw, str):
        net_flow_str = net_flow_raw
    else:
        net_flow_str = format_net_flow(float(net_flow_raw))
    
    # 使用大模型生成摘要
    summary = generate_stock_summary(
        stock_name=short_name,
        change_pct=change_pct,
        amount=amount,
        net_flow=net_flow_str,
        news_list=news_list if news_list else []
    )
    
    logger.info(f"生成摘要 #{stock_row.get('rank', 'N/A')}: {summary}")
    return summary
    
    # 以下为旧版实现（保留作为降级方案）
    # 格式化涨跌幅（带符号）
    if change_pct >= 0:
        change_str = f"+{change_pct:.2f}%"
    else:
        change_str = f"{change_pct:.2f}%"
    
    # 格式化成交额
    amount_str = format_amount(amount)
    
    # 构建摘要（不含新闻）
    # 示例："协创数据 +5.23% 成交额 12.5 亿 主力净流入 3200 万"
    base_summary = f"{short_name} {change_str} 成交额{amount_str} 主力净流入{net_flow_str}"
    
    # 如果有新闻，添加新闻标题（截断到剩余字数）
    if news_list and len(news_list) > 0:
        latest_news = news_list[0]
        news_title = latest_news.get('title', '')
        
        # 计算剩余字数（预留 2 字给空格）
        remaining_chars = 50 - len(base_summary) - 2
        
        if remaining_chars > 5:  # 至少还能放 5 个字
            # 截断新闻标题
            if len(news_title) > remaining_chars:
                news_title = news_title[:remaining_chars-1] + "…"
            
            summary = f"{base_summary} {news_title}"
        else:
            summary = base_summary
    else:
        summary = base_summary
    
    # 最终检查（确保不超过 50 字）
    if len(summary) > 50:
        summary = summary[:49] + "…"
    
    return summary


def generate_news_link(news_list: List[Dict]) -> str:
    """
    提取当日关键新闻链接
    
    Args:
        news_list: 新闻列表
    
    Returns:
        最新一条新闻的链接，无新闻返回 "无可靠新闻链接"
    """
    if not news_list or len(news_list) == 0:
        return "无可靠新闻链接"
    
    latest_news = news_list[0]
    link = latest_news.get('link', '')
    
    if link and link.strip():
        return link
    else:
        return "无可靠新闻链接"


def generate_top_stocks_report(top_stocks_df: pd.DataFrame, news_data: Dict[str, List[Dict]] = None) -> List[Dict]:
    """
    为 Top 10 股票生成完整报告
    
    Args:
        top_stocks_df: Top 10 股票 DataFrame（来自 scorer.get_top_stocks）
        news_data: 每只股票的新闻数据 {stock_code: news_list}
    
    Returns:
        list[dict] 每只股票包含：
        - stock_code: 股票代码
        - short_name: 股票名称
        - summary: 摘要（<50 字）
        - news_link: 新闻链接
        - rank: 排名
        - score: 综合分
    """
    if top_stocks_df is None or len(top_stocks_df) == 0:
        logger.warning("Top 10 股票数据为空")
        return []
    
    if news_data is None:
        news_data = {}
    
    report_list = []
    
    for idx, (_, row) in enumerate(top_stocks_df.iterrows(), start=1):
        stock_code = row.get('stock_code', '')
        
        # 获取该股票的新闻
        news_list = news_data.get(stock_code, [])
        
        # 生成摘要
        summary = generate_summary(row, news_list)
        
        # 生成新闻链接
        news_link = generate_news_link(news_list)
        
        # 构建报告项
        report_item = {
            'rank': idx,
            'stock_code': stock_code,
            'short_name': row.get('short_name', ''),
            'summary': summary,
            'news_link': news_link,
            'score': row.get('score_final', 0)
        }
        
        report_list.append(report_item)
        
        logger.info(f"生成摘要 #{idx}: {summary}")
    
    return report_list
