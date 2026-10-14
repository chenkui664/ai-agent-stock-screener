#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
目标板块配置表

这些板块代码是可验证的：
- 同花顺指数代码 886099 在 https://q.10jqka.com.cn/886099 可见
- 东方财富板块代码 BK0809 在 https://quote.eastmoney.com/bk0809.html 可见
"""

# 目标板块映射表
# key: 板块标识（用于日志和配置），value: 数据源和代码
TARGET_CONCEPTS = {
    "AI 智能体_同花顺": {
        "source": "ths",
        "code": "886099",  # 同花顺指数代码
        "concept_code": "309183",  # 同花顺概念代码（备选）
        "priority": 1  # 优先级，数字越小优先级越高
    },
    "AI 应用_同花顺": {
        "source": "ths",
        "code": "886108",
        "concept_code": "309264",
        "priority": 2
    },
    "AI 智能体_东财": {
        "source": "eastmoney",
        "code": "BK0809",  # 东方财富板块代码
        "priority": 3
    },
}

# 默认使用的板块标识
DEFAULT_CONCEPT = "AI 智能体_同花顺"
