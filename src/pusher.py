#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
推送模块 - 仅支持飞书

支持的平台：
1. 飞书机器人（支持签名验证）

使用方式：
- 通过环境变量 FEISHU_WEBHOOK_URL 配置 Webhook URL
- 调用 push_feishu() 推送

消息格式：
🔥 AI 智能体 Top 10 股票热力榜
日期：2026-10-14

#1 协创数据 (300857)
+5.23% 成交额 12.50 亿 主力净流入 3200 万
协创数据业绩增长超预期
🔗 http://example.com/news/300857

#2 金山办公 (688111)
...
"""

import logging
import os
import requests
from typing import List, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 从环境变量读取飞书 Webhook URL
FEISHU_WEBHOOK_URL = os.getenv('FEISHU_WEBHOOK_URL')


def format_message(report_list: List[Dict], trade_date: str) -> str:
    """
    格式化推送消息（Markdown 格式）
    
    Args:
        report_list: 报告列表（来自 summarizer.generate_top_stocks_report）
        trade_date: 交易日期
    
    Returns:
        格式化后的消息字符串
    """
    lines = []
    
    # 标题
    lines.append("🔥 AI 智能体 Top 10 股票热力榜")
    lines.append(f"日期：{trade_date}")
    lines.append("")
    
    # 股票列表
    for item in report_list:
        rank = item['rank']
        short_name = item['short_name']
        stock_code = item['stock_code']
        summary = item['summary']
        news_link = item['news_link']
        
        # 格式：#1 协创数据 (300857)
        lines.append(f"#{rank} {short_name} ({stock_code})")
        
        # 摘要
        lines.append(summary)
        
        # 新闻链接
        if news_link and news_link != "无可靠新闻链接":
            lines.append(f"🔗 {news_link}")
        
        lines.append("")
    
    # 尾部
    lines.append("---")
    lines.append("数据源：同花顺/东方财富/AKShare")
    lines.append("⚠️ 投资有风险，入市需谨慎")
    
    return "\n".join(lines)


def push_feishu(message: str) -> bool:
    """
    推送到飞书机器人（支持签名验证）
    
    Args:
        message: Markdown 格式消息
    
    Returns:
        是否成功
    
    注意：
        - 如果 Webhook URL 包含 sign 和 timestamp 参数，使用签名验证
        - 如果不包含，直接推送（无签名模式）
    """
    webhook_url = WEBHOOKS.get('feishu')
    
    if not webhook_url:
        logger.warning("飞书 Webhook URL 未配置")
        return False
    
    try:
        # 检查 URL 是否包含签名参数
        if 'sign=' in webhook_url and 'timestamp=' in webhook_url:
            # 签名验证模式
            # 从 URL 中提取 timestamp 和 sign
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(webhook_url)
            params = parse_qs(parsed.query)
            
            timestamp = params.get('timestamp', [''])[0]
            sign = params.get('sign', [''])[0]
            
            # 构建基础 URL（不含参数）
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # 构建带签名的请求
            data = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "🔥 AI 智能体 Top 10 股票热力榜"
                        },
                        "template": "red"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": message
                        }
                    ]
                }
            }
            
            # 添加签名参数到请求头
            headers = {
                'Content-Type': 'application/json',
                'X-Feishu-Timestamp': timestamp,
                'X-Feishu-Sign': sign
            }
            
            response = requests.post(base_url, json=data, headers=headers, timeout=10)
        else:
            # 无签名模式
            data = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "🔥 AI 智能体 Top 10 股票热力榜"
                        },
                        "template": "red"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": message
                        }
                    ]
                }
            }
            
            response = requests.post(webhook_url, json=data, timeout=10)
        
        response.raise_for_status()
        
        result = response.json()
        if result.get('StatusCode') == 0 or result.get('code') == 0:
            logger.info("飞书推送成功")
            return True
        else:
            logger.error(f"飞书推送失败：{result}")
            return False
            
    except Exception as e:
        logger.error(f"飞书推送异常：{type(e).__name__}: {e}")
        return False


def push_feishu_simple(message: str) -> bool:
    """
    推送到飞书（简化版 - 无签名模式）
    
    Args:
        message: Markdown 格式消息
    
    Returns:
        是否成功
    """
    if not FEISHU_WEBHOOK_URL:
        logger.warning("飞书 Webhook URL 未配置")
        return False
    
    try:
        data = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "🔥 AI 智能体 Top 10 股票热力榜"
                    },
                    "template": "red"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": message
                    }
                ]
            }
        }
        
        response = requests.post(FEISHU_WEBHOOK_URL, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('StatusCode') == 0 or result.get('code') == 0:
            logger.info("飞书推送成功")
            return True
        else:
            logger.error(f"飞书推送失败：{result}")
            return False
            
    except Exception as e:
        logger.error(f"飞书推送异常：{type(e).__name__}: {e}")
        return False


def push_feishu(message: str) -> bool:
    """
    推送到飞书机器人（支持签名验证）
    
    Args:
        message: Markdown 格式消息
    
    Returns:
        是否成功
    
    注意：
        - 如果 Webhook URL 包含 sign 和 timestamp 参数，使用签名验证
        - 如果不包含，直接推送（无签名模式）
    """
    if not FEISHU_WEBHOOK_URL:
        logger.warning("飞书 Webhook URL 未配置")
        return False
    
    try:
        # 检查 URL 是否包含签名参数
        if 'sign=' in FEISHU_WEBHOOK_URL and 'timestamp=' in FEISHU_WEBHOOK_URL:
            # 签名验证模式
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(FEISHU_WEBHOOK_URL)
            params = parse_qs(parsed.query)
            
            timestamp = params.get('timestamp', [''])[0]
            sign = params.get('sign', [''])[0]
            
            # 构建基础 URL（不含参数）
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # 构建带签名的请求
            data = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "🔥 AI 智能体 Top 10 股票热力榜"
                        },
                        "template": "red"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": message
                        }
                    ]
                }
            }
            
            # 添加签名参数到请求头
            headers = {
                'Content-Type': 'application/json',
                'X-Feishu-Timestamp': timestamp,
                'X-Feishu-Sign': sign
            }
            
            response = requests.post(base_url, json=data, headers=headers, timeout=10)
        else:
            # 无签名模式
            data = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "🔥 AI 智能体 Top 10 股票热力榜"
                        },
                        "template": "red"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": message
                        }
                    ]
                }
            }
            
            response = requests.post(FEISHU_WEBHOOK_URL, json=data, timeout=10)
        
        response.raise_for_status()
        
        result = response.json()
        if result.get('StatusCode') == 0 or result.get('code') == 0:
            logger.info("飞书推送成功")
            return True
        else:
            logger.error(f"飞书推送失败：{result}")
            return False
            
    except Exception as e:
        logger.error(f"飞书推送异常：{type(e).__name__}: {e}")
        return False
