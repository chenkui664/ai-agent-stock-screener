# 千问大模型集成说明

## 📋 功能概述

系统已集成阿里云千问大模型（Qwen 3.5 Plus），用于增强新闻处理和摘要生成能力。

## 🔧 配置步骤

### 1. 获取 API Key

1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
2. 注册/登录阿里云账号
3. 创建 API Key
4. 复制 API Key

### 2. 配置环境变量

编辑 `.env` 文件，填入 API Key：

```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. 安装依赖

```bash
conda activate py312_env
pip install dashscope
```

## 🚀 大模型功能

### 功能 1：新闻相关性分析

**用途**：判断新闻是否与"AI 智能体"概念相关

**调用方式**：
```python
from src.llm_service import analyze_news_relevance

result = analyze_news_relevance(
    news_title="某某公司发布 AI 智能体新产品",
    news_content="详细内容..."  # 可选
)

# 返回结果
{
    "is_relevant": True,      # 是否相关
    "confidence": 0.95,       # 置信度 0-1
    "keywords": ["AI 智能体", "产品发布"],
    "reason": "新闻明确提及 AI 智能体产品发布"
}
```

**应用场景**：
- 计算新闻得分时，只统计与"AI 智能体"相关的新闻
- 避免将泛 AI 新闻误判为智能体新闻

### 功能 2：智能摘要生成

**用途**：为 Top 10 股票生成<50 字的精炼摘要

**调用方式**：
```python
from src.llm_service import generate_stock_summary

summary = generate_stock_summary(
    stock_name="协创数据",
    change_pct=5.23,
    amount=1250000000,  # 12.5 亿
    net_flow="3200 万",
    news_list=[
        {"title": "业绩增长超预期", "url": "http://..."},
        {"title": "新产品发布", "url": "http://..."}
    ]
)

# 输出示例
"协创数据 +5.23% 成交额 12.5 亿 主力净流入 3200 万 业绩超预期"
```

**优势**：
- 比简单拼接更自然流畅
- 能提炼新闻核心信息
- 严格控制字数在 50 字以内

### 功能 3：新闻得分计算

**用途**：使用大模型分析新闻质量，给出 0-1 分评分

**调用方式**：
```python
from src.llm_service import calculate_news_score

score = calculate_news_score(news_list)
# score: 0.0-1.0
```

**评分维度**：
- 新闻与"AI 智能体"的相关性
- 新闻的情感倾向（利好/利空）
- 新闻的重要性

## 📊 降级策略

当大模型不可用时（未配置 API Key 或网络异常），系统自动降级到基础实现：

| 功能 | 大模型模式 | 降级模式 |
|------|-----------|---------|
| 新闻分析 | 语义理解相关性 | 关键词匹配 |
| 摘要生成 | 智能提炼<50 字 | 简单拼接 |
| 新闻得分 | 相关性*置信度 | 基础分 0.5 |

**降级触发条件**：
- 未配置 `DASHSCOPE_API_KEY`
- dashscope 库未安装
- API 调用失败

## 💰 成本估算

千问 Plus 模型价格：约 ¥0.008/千 tokens

**单次运行成本**：
- 新闻分析：30 条 × 200 tokens = 6000 tokens ≈ ¥0.048
- 摘要生成：10 条 × 100 tokens = 1000 tokens ≈ ¥0.008
- **总计**：≈ ¥0.06/天 ≈ ¥1.8/月

## 🔍 调试技巧

### 查看大模型调用日志

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python main.py
```

### 测试大模型连接

```python
from src.llm_service import init_client

client = init_client()
if client:
    print("✅ 大模型连接成功")
else:
    print("❌ 大模型不可用")
```

## 📝 注意事项

1. **API Key 安全**：不要将 `.env` 文件提交到 Git
2. **网络要求**：需要能访问阿里云 API
3. **速率限制**：千问默认 QPS 限制，如有需要可申请提升
4. **模型选择**：默认使用 `qwen-plus`，可在 `llm_service.py` 中修改

## 🎯 后续优化方向

1. **批量处理**：将 30 条新闻批量发送给大模型，减少调用次数
2. **缓存机制**：相同新闻不重复分析
3. **提示词优化**：根据实际效果调整 prompt
4. **多模型支持**：支持切换其他大模型（如文心、通义）
