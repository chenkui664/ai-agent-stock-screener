#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据获取层

数据源方案（本地环境）：
- 成分股 + 行情：adata（已验证稳定）- 469 只成分股
- 交易日历：adata（已验证稳定）
- 新闻：akshare（已验证稳定）
- 资金流：akshare.stock_fund_flow_individual（已验证稳定）- 5214 只股票

真实接口返回字段：
- 成分股：['stock_code', 'short_name']
- 实时行情：['stock_code', 'short_name', 'price', 'change', 'change_pct', 'volume', 'amount']
- 资金流：['序号', '股票代码', '股票简称', '最新价', '涨跌幅', '换手率', '流入资金', '流出资金', '净额', '成交额']
- 新闻：['关键词', '新闻标题', '新闻内容', '发布时间', '文章来源', '新闻链接']
- 交易日历：['trade_date', 'trade_status', 'day_week']

注意：
- 成分股接口偶尔不稳定（返回空 DataFrame），重试即可
- 资金流接口耗时约 10-15 秒（获取全市场 5000+ 股票）
"""

import logging
from datetime import datetime, timedelta
import time
import pandas as pd

import adata
import akshare as ak
from src.config import TARGET_CONCEPTS, DEFAULT_CONCEPT

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_single_stock_fund_flow(stock_code: str, retry: int = 2) -> dict | None:
    """
    获取单只股票的资金流数据（逐个调用，避免风控）
    
    Args:
        stock_code: 股票代码，如 "300857"
        retry: 重试次数，默认 2 次（失败重试 1 次）
    
    Returns:
        dict 包含资金流数据：
        - stock_code: 股票代码
        - fund_inflow: 主力流入资金
        - fund_outflow: 主力流出资金
        - net_flow: 主力净流入
        
        如果获取失败，返回 None
    
    注意：
        - 使用 ak.stock_individual_fund_flow() 逐个调用
        - 每次调用间隔 0.5 秒（由调用者控制）
        - 失败重试 1 次，仍失败则剔除
    """
    delays = [0.5, 1]  # 重试间隔（秒）
    
    for attempt in range(retry):
        try:
            logger.info(f"获取资金流：{stock_code} (尝试 {attempt + 1}/{retry})")
            
            # 获取单只股票资金流
            fund_flow_df = ak.stock_individual_fund_flow(stock=stock_code)
            
            if fund_flow_df is None or len(fund_flow_df) == 0:
                logger.warning(f"资金流数据为空：{stock_code} (尝试 {attempt + 1}/{retry})")
                if attempt < retry - 1:
                    time.sleep(delays[attempt])
                continue
            
            # 取最新一行数据
            row = fund_flow_df.iloc[0]
            result = {
                'stock_code': stock_code,
                'fund_inflow': row['流入资金'],
                'fund_outflow': row['流出资金'],
                'net_flow': row['净额']
            }
            logger.info(f"资金流获取成功：{stock_code}, net_flow={row['净额']}")
            return result
                
        except Exception as e:
            logger.error(f"获取资金流失败：{stock_code} (尝试 {attempt + 1}/{retry}) - {type(e).__name__}: {e}")
            if attempt < retry - 1:
                logger.info(f"等待 {delays[attempt]} 秒后重试...")
                time.sleep(delays[attempt])
            else:
                logger.error(f"放弃获取 {stock_code} 资金流，已重试 {retry} 次")
                return None
    
    return None


def get_candidates_stocks(concept_key: str = None, top_n: int = 30) -> pd.DataFrame:
    """
    获取候选股票列表（两阶段筛选的第一阶段）
    
    流程：
    1. 获取概念成分股及行情数据
    2. 计算成交额和涨跌幅的百分位分数
    3. 按加权分（成交额 40% + 涨跌幅 30%）粗排
    4. 返回前 top_n 只作为候选
    
    Args:
        concept_key: 概念标识
        top_n: 返回候选股票数量，默认 30
    
    Returns:
        DataFrame 包含候选股票及基础数据，列包括：
        - stock_code: 股票代码
        - short_name: 股票名称
        - price: 最新价
        - change: 涨跌额
        - change_pct: 涨跌幅
        - volume: 成交量
        - amount: 成交额
        - amount_rank: 成交额百分位排名（0-1）
        - change_pct_rank: 涨跌幅百分位排名（0-1）
        - score_pre: 粗排分数（amount_rank*0.4 + change_pct_rank*0.7）
        
        如果获取失败，返回 None
    """
    # 1. 获取成分股及行情数据
    logger.info(f"获取成分股及行情数据（{concept_key}）...")
    stocks_df = get_concept_stocks(concept_key)
    
    if stocks_df is None or len(stocks_df) == 0:
        logger.error("获取成分股失败")
        return None
    
    # 2. 检查必要字段
    required_cols = ['stock_code', 'short_name', 'amount', 'change_pct']
    missing_cols = [col for col in required_cols if col not in stocks_df.columns]
    
    if missing_cols:
        logger.error(f"缺少必要字段：{missing_cols}")
        return None
    
    # 3. 计算百分位排名
    logger.info(f"计算成交额和涨跌幅百分位排名...")
    
    # 成交额百分位（成交额越大，排名越高）
    stocks_df['amount_rank'] = stocks_df['amount'].rank(pct=True)
    
    # 涨跌幅百分位（涨幅越大，排名越高）
    stocks_df['change_pct_rank'] = stocks_df['change_pct'].rank(pct=True)
    
    # 4. 计算粗排分数（成交额 40% + 涨跌幅 30%）
    # 注意：与最终综合分保持一致的权重
    stocks_df['score_pre'] = stocks_df['amount_rank'] * 0.40 + stocks_df['change_pct_rank'] * 0.30
    
    # 5. 按粗排分数降序排序，取前 top_n 只
    stocks_df = stocks_df.sort_values('score_pre', ascending=False).head(top_n)
    
    logger.info(f"获取到 {len(stocks_df)} 只候选股票（粗排前 {top_n}）")
    logger.info(f"候选股票分数范围：{stocks_df['score_pre'].min():.4f} ~ {stocks_df['score_pre'].max():.4f}")
    
    return stocks_df


def get_concept_stocks(concept_key: str = None) -> pd.DataFrame:
    """
    获取指定概念板块的成分股、实时行情及资金流数据
    
    Args:
        concept_key: 概念标识，使用 src.config.TARGET_CONCEPTS 中的 key
                    如果为 None，使用 DEFAULT_CONCEPT
    
    Returns:
        DataFrame 包含成分股、行情及资金流数据，列包括：
        - stock_code: 股票代码
        - short_name: 股票名称
        - price: 最新价
        - change: 涨跌额
        - change_pct: 涨跌幅
        - volume: 成交量
        - amount: 成交额（元）
        - fund_inflow: 主力流入资金（元）
        - fund_outflow: 主力流出资金（元）
        - net_flow: 主力净流入（元）
        
        如果找不到对应概念或获取失败，返回 None
    
    注意：
        - 资金流数据来自 akshare.stock_fund_flow_individual(symbol='即时')
        - 该接口返回全市场 5000+ 只股票的即时资金流，按净额排序
        - 云环境测试稳定，约 10-15 秒完成
    """
    if concept_key is None:
        concept_key = DEFAULT_CONCEPT
    
    if concept_key not in TARGET_CONCEPTS:
        logger.error(f"未知的概念标识：{concept_key}，可用的有：{list(TARGET_CONCEPTS.keys())}")
        return None
    
    config = TARGET_CONCEPTS[concept_key]
    source = config['source']
    code = config['code']
    
    try:
        # 1. 根据数据源获取成分股
        if source == 'ths':
            # 同花顺：使用指数代码（已验证稳定）
            logger.info(f"使用同花顺指数代码：{code}")
            constituent_df = adata.stock.info.concept_constituent_ths(index_code=code)
            
            # 如果返回空，尝试用 concept_code
            if constituent_df is None or len(constituent_df) == 0:
                concept_code = config.get('concept_code')
                if concept_code:
                    logger.info(f"指数代码返回空，尝试概念代码：{concept_code}")
                    constituent_df = adata.stock.info.concept_constituent_ths(concept_code=concept_code)
            
        elif source == 'eastmoney':
            # 东方财富：使用 concept_code 参数（BK 开头）
            logger.info(f"使用东方财富板块代码：{code}")
            constituent_df = adata.stock.info.concept_constituent_east(concept_code=code)
            
        else:
            logger.error(f"不支持的数据源：{source}")
            return None
        
        if constituent_df is None or len(constituent_df) == 0:
            logger.error(f"获取成分股失败：{concept_key} ({code})")
            return None
        
        logger.info(f"获取到 {len(constituent_df)} 只成分股（{concept_key}）")
        
        # 2. 获取成分股的实时行情数据
        stock_codes = constituent_df['stock_code'].tolist()
        
        # 使用 list_market_current 批量获取实时行情
        market_df = adata.stock.market.list_market_current(stock_codes)
        
        if market_df is None or len(market_df) == 0:
            logger.warning("获取实时行情失败，返回基础成分股数据")
            return constituent_df
        
        # 3. 合并成分股信息和行情数据
        result_df = pd.merge(constituent_df, market_df, on=['stock_code', 'short_name'], how='left')
        
        # 4. 获取全市场资金流数据（约 10-15 秒）
        logger.info("获取全市场资金流数据...")
        try:
            fund_flow_df = ak.stock_fund_flow_individual(symbol='即时')
            
            if fund_flow_df is not None and len(fund_flow_df) > 0:
                logger.info(f"获取到 {len(fund_flow_df)} 只股票的资金流数据")
                
                # 重命名资金流字段，避免冲突
                fund_flow_df = fund_flow_df.rename(columns={
                    '流入资金': 'fund_inflow',
                    '流出资金': 'fund_outflow',
                    '净额': 'net_flow'
                })
                
                # 转换股票代码为字符串（确保类型一致）
                fund_flow_df['股票代码'] = fund_flow_df['股票代码'].astype(str).str.zfill(6)
                
                # 合并资金流数据
                result_df = pd.merge(
                    result_df,
                    fund_flow_df[['股票代码', 'fund_inflow', 'fund_outflow', 'net_flow']],
                    left_on='stock_code',
                    right_on='股票代码',
                    how='left'
                )
                
                # 删除重复的股票代码列
                if '股票代码' in result_df.columns and 'stock_code' in result_df.columns:
                    result_df = result_df.drop(columns=['股票代码'])
                
                logger.info(f"合并资金流后数据形状：{result_df.shape}，字段：{result_df.columns.tolist()}")
            else:
                logger.warning("获取资金流数据失败，返回不含资金流的数据")
                
        except Exception as e:
            logger.error(f"获取资金流异常：{type(e).__name__}: {e}", exc_info=True)
            # 不返回 None，继续返回不含资金流的数据
        
        logger.info(f"最终数据形状：{result_df.shape}，字段：{result_df.columns.tolist()}")
        
        return result_df
        
    except Exception as e:
        logger.error(f"获取概念成分股异常：{type(e).__name__}: {e}", exc_info=True)
        return None


def get_stock_news(stock_code: str, date: str = None) -> list[dict]:
    """
    获取指定股票当日新闻（使用 akshare）
    
    Args:
        stock_code: 股票代码，如 "300857"
        date: 日期，格式 YYYY-MM-DD（可选，akshare 返回最新 N 条，不严格按日期过滤）
    
    Returns:
        list[dict] 每条新闻包含：
        - title: 新闻标题
        - link: 新闻链接
        - publish_time: 发布时间
        
        如果获取失败，返回空列表 []
        如果无可靠新闻，返回 []
    
    注意：
        - akshare 返回的是最新 N 条新闻，不严格按 date 过滤
        - 云环境测试稳定，本地环境更可靠
        - 数据来源：东方财富网
    """
    if date is None:
        # 默认使用最近一个交易日
        date = get_trade_date()
    
    try:
        logger.info(f"获取股票新闻：stock_code={stock_code}, date={date}")
        
        # 调用 akshare 新闻接口
        news_df = ak.stock_news_em(symbol=stock_code)
        
        if news_df is None or len(news_df) == 0:
            logger.warning(f"无新闻数据：{stock_code}")
            return []
        
        logger.info(f"获取到 {len(news_df)} 条新闻（{stock_code}）")
        
        # 检查必要字段
        required_cols = ['新闻标题', '新闻链接', '发布时间']
        if not all(col in news_df.columns for col in required_cols):
            logger.error(f"新闻字段不完整，期望包含 {required_cols}，实际有 {news_df.columns.tolist()}")
            return []
        
        # 转换为 list[dict] 格式
        news_list = []
        for _, row in news_df.iterrows():
            news_item = {
                'title': str(row['新闻标题']),
                'link': str(row['新闻链接']),
                'publish_time': str(row['发布时间'])
            }
            news_list.append(news_item)
        
        # 返回最新的一条作为"当日关键新闻"（可选）
        # 如果需要严格按 date 过滤，可以在这里添加过滤逻辑
        
        return news_list
        
    except Exception as e:
        logger.error(f"获取股票新闻异常：{type(e).__name__}: {e}", exc_info=True)
        return []


def get_trade_date() -> str:
    """
    返回最近一个交易日（北京时间）
    
    Returns:
        str: 最近一个交易日，格式 YYYY-MM-DD
        
    非交易日会正确回溯到上一个交易日
    
    注意：
        - 使用 adata 的交易日历接口
        - 正确识别周末和法定节假日
    """
    try:
        # 使用 adata 的交易日历接口
        calendar_df = adata.stock.info.trade_calendar()
        
        if calendar_df is None or len(calendar_df) == 0:
            logger.error("获取交易日历失败")
            return None
        
        # 获取今天日期（北京时间）
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 筛选今天及之前的交易日
        # calendar_df 包含 trade_date (str), trade_status (0/1), day_week
        # trade_status=1 表示交易日
        if 'trade_date' in calendar_df.columns and 'trade_status' in calendar_df.columns:
            # 筛选已过去的交易日且是交易日的日期
            past_dates = calendar_df[
                (calendar_df['trade_date'] <= today) & 
                (calendar_df['trade_status'] == 1)
            ]
            
            if len(past_dates) > 0:
                # 按日期降序排序，取第一个（最近的交易日）
                past_dates = past_dates.sort_values('trade_date', ascending=False)
                last_trade_date = past_dates.iloc[0]['trade_date']
                logger.info(f"最近一个交易日：{last_trade_date}")
                return last_trade_date
        
        # 如果没有找到明确的交易日标记，尝试获取当前日期并回溯
        # 简单策略：如果是周末，回溯到周五
        today_dt = datetime.now()
        weekday = today_dt.weekday()
        
        if weekday >= 5:  # 周六或周日
            days_back = weekday - 4  # 回溯到周五
            trade_date = (today_dt - timedelta(days=days_back)).strftime('%Y-%m-%d')
        else:
            trade_date = today_dt.strftime('%Y-%m-%d')
        
        logger.info(f"最近一个交易日（推算）：{trade_date}")
        return trade_date
        
    except Exception as e:
        logger.error(f"获取交易日异常：{type(e).__name__}: {e}", exc_info=True)
        raise
