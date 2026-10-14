#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
推送模块 - 支持多个 IM 平台

支持的平台：
1. 企业微信机器人
2. 飞书机器人
3. 钉钉机器人
4. Telegram Bot
5. 邮件推送

使用方式：
- 通过环境变量配置 Webhook URL
- 调用 push_to_platform() 推送
- 或调用 push_to_all_platforms() 推送到所有配置的平台

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
import smtplib
import hashlib
import hmac
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 从环境变量读取 Webhook URL
WEBHOOKS = {
    'wechat': os.getenv('WECHAT_WEBHOOK_URL'),      # 企业微信
    'feishu': os.getenv('FEISHU_WEBHOOK_URL'),      # 飞书
    'dingtalk': os.getenv('DINGTALK_WEBHOOK_URL'),  # 钉钉
    'telegram': os.getenv('TELEGRAM_BOT_TOKEN'),    # Telegram
    'email': os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',  # 邮件
}

EMAIL_CONFIG = {
    'smtp_server': os.getenv('EMAIL_SMTP_SERVER'),
    'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', '587')),
    'username': os.getenv('EMAIL_USERNAME'),
    'password': os.getenv('EMAIL_PASSWORD'),
    'from_addr': os.getenv('EMAIL_FROM'),
    'to_addrs': os.getenv('EMAIL_TO', '').split(','),
}


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


def push_wechat(message: str) -> bool:
    """
    推送到企业微信机器人
    
    Args:
        message: Markdown 格式消息
    
    Returns:
        是否成功
    """
    webhook_url = WEBHOOKS.get('wechat')
    
    if not webhook_url:
        logger.warning("企业微信 Webhook URL 未配置")
        return False
    
    try:
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": message
            }
        }
        
        response = requests.post(webhook_url, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('errcode') == 0:
            logger.info("企业微信推送成功")
            return True
        else:
            logger.error(f"企业微信推送失败：{result}")
            return False
            
    except Exception as e:
        logger.error(f"企业微信推送异常：{type(e).__name__}: {e}")
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


def push_dingtalk(message: str) -> bool:
    """
    推送到钉钉机器人
    
    Args:
        message: Markdown 格式消息
    
    Returns:
        是否成功
    """
    webhook_url = WEBHOOKS.get('dingtalk')
    
    if not webhook_url:
        logger.warning("钉钉 Webhook URL 未配置")
        return False
    
    try:
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": "AI 智能体 Top 10 股票热力榜",
                "text": message
            }
        }
        
        response = requests.post(webhook_url, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('errcode') == 0:
            logger.info("钉钉推送成功")
            return True
        else:
            logger.error(f"钉钉推送失败：{result}")
            return False
            
    except Exception as e:
        logger.error(f"钉钉推送异常：{type(e).__name__}: {e}")
        return False


def push_telegram(message: str) -> bool:
    """
    推送到 Telegram
    
    Args:
        message: Markdown 格式消息
    
    Returns:
        是否成功
    """
    bot_token = WEBHOOKS.get('telegram')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.warning("Telegram Bot Token 或 Chat ID 未配置")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            logger.info("Telegram 推送成功")
            return True
        else:
            logger.error(f"Telegram 推送失败：{result}")
            return False
            
    except Exception as e:
        logger.error(f"Telegram 推送异常：{type(e).__name__}: {e}")
        return False


def push_email(message: str, trade_date: str) -> bool:
    """
    推送到邮件
    
    Args:
        message: 消息内容
        trade_date: 交易日期
    
    Returns:
        是否成功
    """
    if not WEBHOOKS.get('email'):
        logger.info("邮件推送未启用")
        return False
    
    config = EMAIL_CONFIG
    if not all([config['smtp_server'], config['username'], config['password'], config['from_addr']]):
        logger.warning("邮件配置不完整")
        return False
    
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = config['from_addr']
        msg['To'] = ', '.join(config['to_addrs'])
        msg['Subject'] = f"AI 智能体 Top 10 股票热力榜 ({trade_date})"
        
        # 添加正文
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        # 发送
        server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        server.starttls()
        server.login(config['username'], config['password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"邮件推送成功，收件人：{config['to_addrs']}")
        return True
        
    except Exception as e:
        logger.error(f"邮件推送异常：{type(e).__name__}: {e}")
        return False


def push_to_platform(platform: str, message: str) -> bool:
    """
    推送到指定平台
    
    Args:
        platform: 平台名称 (wechat/feishu/dingtalk/telegram/email)
        message: 消息内容
    
    Returns:
        是否成功
    """
    pushers = {
        'wechat': push_wechat,
        'feishu': push_feishu,
        'dingtalk': push_dingtalk,
        'telegram': push_telegram,
        'email': push_email
    }
    
    if platform not in pushers:
        logger.error(f"不支持的平台：{platform}")
        return False
    
    return pushers[platform](message)


def push_to_all_platforms(message: str, trade_date: str) -> Dict[str, bool]:
    """
    推送到所有已配置的平台
    
    Args:
        message: 消息内容
        trade_date: 交易日期
    
    Returns:
        dict 各平台的推送结果 {platform: success}
    """
    results = {}
    
    # 尝试推送到每个平台
    for platform in ['wechat', 'feishu', 'dingtalk', 'telegram', 'email']:
        # 检查是否配置
        if platform == 'email':
            enabled = WEBHOOKS.get('email', False)
        else:
            enabled = WEBHOOKS.get(platform) is not None
        
        if enabled:
            logger.info(f"推送到 {platform}...")
            success = push_to_platform(platform, message)
            results[platform] = success
        else:
            logger.info(f"跳过 {platform}（未配置）")
            results[platform] = False
    
    return results
