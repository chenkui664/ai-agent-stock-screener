#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
千问大模型调用服务

提供以下功能：
1. 新闻提及识别：判断新闻是否与"AI 智能体"概念相关
2. 智能摘要生成：为股票生成<50 字的精炼摘要
"""

import logging
import os
from typing import Optional, Dict, Any

try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    dashscope = None

logger = logging.getLogger(__name__)

# 模型配置
DEFAULT_MODEL = "qwen-plus"  # 千问 3.5 Plus


def get_api_key() -> Optional[str]:
    """从环境变量获取 API Key"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        logger.warning("未配置 DASHSCOPE_API_KEY，大模型功能将不可用")
        return None
    return api_key


def init_client():
    """初始化千问客户端"""
    if not DASHSCOPE_AVAILABLE:
        logger.error("未安装 dashscope 库，请运行：pip install dashscope")
        return None
    
    api_key = get_api_key()
    if not api_key:
        return None
    
    dashscope.api_key = api_key
    logger.info(f"千问客户端初始化成功（模型：{DEFAULT_MODEL}）")
    return dashscope


def analyze_news_relevance(news_title: str, news_content: str = "") -> Dict[str, Any]:
    """
    分析新闻是否与"AI 智能体"概念相关
    
    Args:
        news_title: 新闻标题
        news_content: 新闻内容（可选）
    
    Returns:
        {
            "is_relevant": bool,  # 是否相关
            "confidence": float,  # 置信度 0-1
            "keywords": list,  # 提取的关键词
            "reason": str  # 判断理由
        }
    """
    client = init_client()
    if not client:
        # 返回默认值（假设相关）
        return {
            "is_relevant": True,
            "confidence": 0.5,
            "keywords": [],
            "reason": "大模型未配置"
        }
    
    prompt = f"""请判断以下新闻是否与"AI 智能体"概念相关：

新闻标题：{news_title}
{f'新闻内容：{news_content}' if news_content else ''}

请从以下维度分析：
1. 是否明确提及"AI 智能体"、"智能体"、"Agent"、"自主智能体"等关键词
2. 是否涉及 AI 智能体的技术研发、产品发布、应用落地、产业生态
3. 是否只是泛泛提及 AI，没有特指智能体

请返回 JSON 格式：
{{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "keywords": ["关键词 1", "关键词 2"],
    "reason": "简要说明判断理由"
}}
"""
    
    try:
        response = Generation.call(
            model=DEFAULT_MODEL,
            prompt=prompt,
            result_format='message'
        )
        
        if response.status_code == 200:
            import json
            result_text = response.output.choices[0].message.content
            result = json.loads(result_text)
            logger.info(f"新闻分析完成：相关={result.get('is_relevant')}")
            return result
        else:
            logger.error(f"千问调用失败：{response.code} - {response.message}")
            return {
                "is_relevant": True,
                "confidence": 0.5,
                "keywords": [],
                "reason": f"API 调用失败：{response.message}"
            }
    
    except Exception as e:
        logger.error(f"新闻分析异常：{type(e).__name__}: {e}")
        return {
            "is_relevant": True,
            "confidence": 0.5,
            "keywords": [],
            "reason": f"异常：{str(e)}"
        }


def generate_stock_summary(
    stock_name: str,
    change_pct: float,
    amount: float,
    net_flow: str,
    news_list: list
) -> str:
    """
    为股票生成智能摘要（<50 字）
    
    Args:
        stock_name: 股票名称
        change_pct: 涨跌幅
        amount: 成交额（元）
        net_flow: 主力净流入（字符串，如"4.12 亿"）
        news_list: 新闻列表 [{"title": "...", "url": "..."}]
    
    Returns:
        <50 字的摘要字符串
    """
    client = init_client()
    if not client:
        # 返回基础摘要（无大模型）
        change_str = f"+{change_pct:.2f}%" if change_pct >= 0 else f"{change_pct:.2f}%"
        amount_str = f"{amount / 1e8:.2f}亿" if amount >= 1e8 else f"{amount / 1e4:.0f}万"
        base = f"{stock_name} {change_str} 成交额{amount_str} 主力净流入{net_flow}"
        if news_list:
            base += f" {news_list[0]['title'][:20]}"
        return base[:50]
    
    # 构建新闻上下文
    news_context = ""
    if news_list:
        for i, news in enumerate(news_list[:3], 1):
            news_context += f"{i}. {news['title']}\n"
    
    prompt = f"""请为以下股票生成精炼摘要（<50 字）：

股票名称：{stock_name}
涨跌幅：{change_pct:.2f}%
成交额：{amount / 1e8:.2f}
主力净流入：{net_flow}

相关新闻：
{news_context if news_context else '无新闻'}

要求：
1. 必须包含：涨跌幅、成交额、资金流方向
2. 如果有新闻，提炼最核心的信息
3. 严格控制在 50 字以内
4. 语言简洁有力，突出亮点

示例格式：
"{stock_name} 大涨 X% 成交 XX 亿 主力大幅净流入 AI 智能体产品发布"
"""
    
    try:
        response = Generation.call(
            model=DEFAULT_MODEL,
            prompt=prompt,
            result_format='message'
        )
        
        if response.status_code == 200:
            summary = response.output.choices[0].message.content.strip()
            # 确保不超过 50 字
            if len(summary) > 50:
                summary = summary[:47] + "..."
            logger.info(f"生成摘要：{summary}")
            return summary
        else:
            logger.error(f"摘要生成失败：{response.code} - {response.message}")
            # 降级到基础摘要
            return f"{stock_name} {change_pct:+.2f}% 成交额{amount/1e8:.2f}亿"
    
    except Exception as e:
        logger.error(f"摘要生成异常：{type(e).__name__}: {e}")
        return f"{stock_name} {change_pct:+.2f}% 成交额{amount/1e8:.2f}亿"


def calculate_news_score(news_list: list) -> float:
    """
    使用大模型计算新闻得分（0-1 分）
    
    Args:
        news_list: 新闻列表 [{"title": "...", "url": "..."}]
    
    Returns:
        新闻得分 0.0-1.0
    """
    if not news_list:
        return 0.0
    
    client = init_client()
    if not client:
        # 降级到简单计分
        return min(len(news_list) * 0.1, 1.0)
    
    # 批量分析新闻
    relevant_count = 0
    total_confidence = 0.0
    
    for news in news_list[:5]:  # 最多分析 5 条
        result = analyze_news_relevance(news.get('title', ''))
        if result.get('is_relevant'):
            relevant_count += 1
            total_confidence += result.get('confidence', 0.5)
    
    if relevant_count == 0:
        return 0.3  # 基础分
    
    # 得分 = 相关度 * 平均置信度
    avg_confidence = total_confidence / relevant_count
    score = (relevant_count / 5) * avg_confidence
    return min(score, 1.0)
