#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评分器 - 两阶段筛选逻辑（支持大模型）

阶段 1（粗排）：
- 获取概念成分股及行情数据
- 计算成交额和涨跌幅的百分位分数
- 按加权分（成交额 40% + 涨跌幅 30%）粗排
- 取前 30 只作为候选

阶段 2（精选）：
- 对候选股票获取资金流数据（带 3 次重试）
- 获取资金流失败的股票直接剔除
- 对剩余股票获取新闻数据
- 计算综合分（成交额 40% + 涨跌幅 30% + 资金流 20% + 新闻 10%）
- 新闻得分使用千问大模型分析相关性
- 返回 Top 10

权重配置（总计 100%）：
- 成交额：40%
- 涨跌幅：30%
- 资金流：20%
- 新闻：10%

注意：
- 资金流缺失的股票直接剔除，不参与排名
- 新闻缺失的股票使用大模型降级处理
- 综合分 = amount_rank*0.40 + change_pct_rank*0.30 + net_flow_rank*0.20 + news_score*0.10
"""

import logging
import time
from typing import List, Dict
import pandas as pd
from src.config import DEFAULT_CONCEPT
from src.fetcher import (
    get_candidates_stocks,
    get_single_stock_fund_flow,
    get_stock_news,
    get_trade_date
)
from src.llm_service import calculate_news_score as llm_calculate_news_score

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 权重配置
# 临时降级方案：因资金流接口不可用，暂时移除资金流权重
WEIGHT_AMOUNT = 0.40     # 成交额权重 40%
WEIGHT_CHANGE_PCT = 0.30 # 涨跌幅权重 30%
WEIGHT_NET_FLOW = 0.00   # 资金流权重 20%（临时降为 0）
WEIGHT_NEWS = 0.10       # 新闻权重 10%
# 总计：80%（临时降级）


def calculate_news_score(news_list: List[Dict]) -> float | None:
    """
    计算新闻得分（使用千问大模型）
    
    Args:
        news_list: 新闻列表，每条包含 title, link, publish_time
    
    Returns:
        新闻得分（0-1 之间）
        如果 news_list 为空，返回 None（表示该股票新闻得分缺失，不参与综合分计算）
    
    评分规则：
        - 使用千问大模型分析新闻与"AI 智能体"的相关性
        - 相关度 * 置信度 = 最终得分
        - 无新闻：返回 None，不参与综合分计算
        - 大模型不可用：0.3 基础分
    """
    # 如果新闻列表为空，返回 None
    if not news_list or len(news_list) == 0:
        logger.info("新闻列表为空，返回 None（不参与综合分计算）")
        return None
    
    # 使用大模型计算得分
    score = llm_calculate_news_score(news_list)
    
    logger.info(f"新闻得分：{score:.3f}（{len(news_list)}条新闻）")
    return score


def rank_stocks(candidates_df: pd.DataFrame, trade_date: str = None) -> pd.DataFrame:
    """
    对候选股票进行综合评分和排名（阶段 2）
    
    流程：
    1. 遍历候选股票，获取资金流数据（失败 3 次后剔除）
    2. 获取新闻数据（失败记 0 分）
    3. 计算各项百分位排名
    4. 计算综合分
    5. 按综合分降序排序
    
    Args:
        candidates_df: 候选股票 DataFrame（来自 get_candidates_stocks）
        trade_date: 交易日期（可选，默认使用最近一个交易日）
    
    Returns:
        DataFrame 包含综合排名结果，列包括：
        - stock_code: 股票代码
        - short_name: 股票名称
        - price: 最新价
        - change_pct: 涨跌幅
        - amount: 成交额
        - net_flow: 主力净流入
        - amount_rank: 成交额百分位
        - change_pct_rank: 涨跌幅百分位
        - net_flow_rank: 资金流百分位
        - news_score: 新闻得分
        - score_final: 综合分
        
        如果输入为空，返回空 DataFrame
    
    注意：
        - 资金流获取失败的股票会被剔除
        - 新闻获取失败记 0 分，但不剔除
    """
    if candidates_df is None or len(candidates_df) == 0:
        logger.warning("候选股票为空")
        return pd.DataFrame()
    
    if trade_date is None:
        trade_date = get_trade_date()
    
    logger.info(f"开始综合评分（trade_date={trade_date}），候选股票 {len(candidates_df)} 只")
    
    # 1. 逐个获取候选股票的资金流（带重试）
    # 临时降级：资金流获取失败时不剔除，标记为 0
    logger.info("阶段 2.1：获取资金流数据（逐个调用）...")
    net_flows = []
    failed_stocks = []  # 资金流获取失败的股票
    
    for idx, row in candidates_df.iterrows():
        stock_code = row['stock_code']
        
        # 获取资金流（带 1 次重试，临时降级）
        fund_data = get_single_stock_fund_flow(stock_code, retry=1)
        
        if fund_data is not None:
            # 成功，记录资金流数据
            net_flows.append(fund_data['net_flow'])
        else:
            # 失败，记录并标记为 0（临时降级方案）
            failed_stocks.append(stock_code)
            net_flows.append(0)
            logger.warning(f"股票 {stock_code} 资金流获取失败，临时降级方案：标记为 0")
        
        # 每只股票间隔 0.5 秒，降低风控概率
        if idx < len(candidates_df) - 1:
            time.sleep(0.5)
    
    logger.info(f"资金流获取完成：成功 {len(candidates_df) - len(failed_stocks)} 只，失败 {len(failed_stocks)} 只")
    
    # 转换为 DataFrame（保留所有股票）
    result_df = candidates_df.copy()
    result_df['net_flow'] = net_flows
    
    # 2. 获取新闻数据并计算新闻得分
    logger.info("阶段 2.2：获取新闻数据并计算得分...")
    news_scores = []
    missing_news_stocks = []  # 新闻缺失的股票
    
    for idx, row in result_df.iterrows():
        stock_code = row['stock_code']
        
        try:
            news_list = get_stock_news(stock_code, date=trade_date)
            news_score = calculate_news_score(news_list)
            
            # 如果新闻得分为 None，标记为缺失
            if news_score is None:
                missing_news_stocks.append(stock_code)
                logger.info(f"股票 {stock_code} 新闻得分缺失（无新闻），不参与综合分计算")
        except Exception as e:
            logger.error(f"获取新闻失败：{stock_code} - {type(e).__name__}: {e}")
            news_score = 0.0
        
        news_scores.append(news_score)
    
    result_df['news_score'] = news_scores
    
    # 3. 计算百分位排名
    logger.info("阶段 2.3：计算百分位排名...")
    
    # 成交额百分位
    result_df['amount_rank'] = result_df['amount'].rank(pct=True)
    
    # 涨跌幅百分位
    result_df['change_pct_rank'] = result_df['change_pct'].rank(pct=True)
    
    # 资金流百分位（主力净流入）
    result_df['net_flow_rank'] = result_df['net_flow'].rank(pct=True)
    
    # 4. 计算综合分
    # 新闻得分为 None 的股票，新闻权重不参与计算（相当于该股票只有前三项得分）
    def calculate_final_score(row):
        base_score = (
            row['amount_rank'] * WEIGHT_AMOUNT +
            row['change_pct_rank'] * WEIGHT_CHANGE_PCT +
            row['net_flow_rank'] * WEIGHT_NET_FLOW
        )
        
        # 如果新闻得分缺失，只计算前三项（权重 90%）
        if row['news_score'] is None:
            return base_score
        else:
            # 新闻得分存在，加上新闻权重（10%）
            return base_score + row['news_score'] * WEIGHT_NEWS
    
    result_df['score_final'] = result_df.apply(calculate_final_score, axis=1)
    
    # 5. 按综合分降序排序
    result_df = result_df.sort_values('score_final', ascending=False)
    
    logger.info(f"综合评分完成，最终排名股票数量：{len(result_df)}")
    logger.info(f"综合分范围：{result_df['score_final'].min():.4f} ~ {result_df['score_final'].max():.4f}")
    
    # 记录被剔除的股票
    if len(failed_stocks) > 0:
        logger.info(f"被剔除的股票（资金流失败）：{failed_stocks}")
    
    # 记录新闻缺失的股票
    if len(missing_news_stocks) > 0:
        logger.info(f"新闻得分缺失的股票（不参与新闻权重计算）：{missing_news_stocks}")
    
    return result_df


def get_top_stocks(concept_key: str = None, top_n: int = 10, candidate_n: int = 30) -> pd.DataFrame:
    """
    获取概念板块 Top N 股票（完整流程）
    
    流程：
    1. 获取候选股票（粗排前 candidate_n 只）
    2. 对候选股票进行综合评分
    3. 返回综合分最高的 top_n 只
    
    Args:
        concept_key: 概念标识
        top_n: 返回 Top N 只股票，默认 10
        candidate_n: 候选股票数量，默认 30
    
    Returns:
        DataFrame 包含 Top N 股票及完整数据
        
        如果获取失败或无数据，返回空 DataFrame
    """
    logger.info(f"开始获取 Top {top_n} 股票（concept={concept_key}, candidate_n={candidate_n}）")
    
    # 阶段 1：获取候选股票
    candidates_df = get_candidates_stocks(concept_key, top_n=candidate_n)
    
    if candidates_df is None or len(candidates_df) == 0:
        logger.error("获取候选股票失败")
        return pd.DataFrame()
    
    # 阶段 2：综合评分
    ranked_df = rank_stocks(candidates_df)
    
    if ranked_df is None or len(ranked_df) == 0:
        logger.error("综合评分失败")
        return pd.DataFrame()
    
    # 取 Top N
    top_stocks = ranked_df.head(top_n)
    
    logger.info(f"获取 Top {top_n} 股票完成")
    logger.info(f"Top 1: {top_stocks.iloc[0]['stock_code']} - {top_stocks.iloc[0]['short_name']} "
                f"(score={top_stocks.iloc[0]['score_final']:.4f})")
    
    return top_stocks
