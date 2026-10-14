# AI 智能体 Top 10 股票热力榜

自动筛选 A 股"AI 智能体/Agent"概念板块 Top 10 股票，推送到 IM 平台。

## 📊 流程图

```
每天 11:00 (北京时间)
    ↓
获取 AI 智能体概念成分股（adata）
    ↓
阶段 1 粗排：成交额 40% + 涨跌幅 30% → 前 30 只候选
    ↓
阶段 2 精选：
  - 获取资金流（失败 3 次后剔除）
  - 获取新闻（失败记 0 分）
  - 综合分 = 成交额 40% + 涨跌幅 30% + 资金流 20% + 新闻 10%
    ↓
生成 Top 10 报告（<50 字摘要 + 新闻链接）
    ↓
推送到 IM 平台（企业微信/飞书/钉钉/Telegram/邮件）
```

## 🚀 快速部署

### 方式 1：GitHub Actions（推荐）

#### 1. Fork 本仓库

点击仓库页面的 **Fork** 按钮。

#### 2. 配置 Secrets（Webhook URL）

进入仓库 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 说明 | 示例 |
|-----------|------|------|
| `WECHAT_WEBHOOK_URL` | 企业微信机器人 Webhook | `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx` |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook | `https://open.feishu.cn/open-apis/bot/v2/hook/xxx` |
| `DINGTALK_WEBHOOK_URL` | 钉钉机器人 Webhook | `https://oapi.dingtalk.com/robot/send?access_token=xxx` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | `-1234567890` |
| `EMAIL_SMTP_SERVER` | 邮件 SMTP 服务器 | `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | SMTP 端口 | `587` |
| `EMAIL_USERNAME` | 邮箱账号 | `your@gmail.com` |
| `EMAIL_PASSWORD` | 邮箱密码/授权码 | `xxx` |
| `EMAIL_FROM` | 发件人邮箱 | `your@gmail.com` |
| `EMAIL_TO` | 收件人邮箱（逗号分隔） | `a@example.com,b@example.com` |

#### 3. 配置 Variables（可选参数）

进入 **Settings → Secrets and variables → Actions → Variables**，添加：

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `CONCEPT_KEY` | 概念标识 | `AI 智能体_同花顺` |
| `TOP_N` | 返回 Top N 只 | `10` |
| `CANDIDATE_N` | 候选股票数量 | `30` |
| `EMAIL_ENABLED` | 是否启用邮件推送 | `false` |

#### 4. 手动测试

进入仓库 **Actions** 标签，选择 **"AI 智能体 Top 10 股票热力榜"** 工作流，点击 **Run workflow** 进行测试。

#### 5. 查看运行日志

工作流运行完成后，点击运行记录查看日志，确认推送结果。

---

### 方式 2：本地运行

#### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/ai-agent-stock-screener.git
cd ai-agent-stock-screener
```

#### 2. 创建虚拟环境

```bash
conda create -n stock python=3.12
conda activate stock
```

#### 3. 安装依赖

```bash
pip install adata akshare pandas requests
```

#### 4. 配置环境变量

**Windows (PowerShell):**

```powershell
$env:WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/..."
$env:FEISHU_WEBHOOK_URL="https://open.feishu.cn/..."
$env:CONCEPT_KEY="AI 智能体_同花顺"
python main.py
```

**Linux/macOS:**

```bash
export WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/..."
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/..."
export CONCEPT_KEY="AI 智能体_同花顺"
python main.py
```

#### 5. 设置定时任务（可选）

**Linux (cron):**

```bash
crontab -e
# 添加：每天 11:00 运行
0 11 * * * cd /path/to/ai-agent-stock-screener && /path/to/conda/envs/stock/bin/python main.py
```

**Windows (Task Scheduler):**

使用"任务计划程序"创建每天 11:00 运行的任务。

---

## 📋 获取机器人 Webhook URL

### 企业微信

1. 在企业微信群中，点击右上角 **···**
2. 选择 **添加群机器人**
3. 设置机器人名称，点击 **添加**
4. 复制 Webhook URL

### 飞书

1. 在飞书群中，点击右上角 **···**
2. 选择 **群机器人**
3. 点击 **添加机器人**
4. 选择 **自定义机器人**
5. 复制 Webhook URL

### 钉钉

1. 在钉钉群中，点击右上角 **···**
2. 选择 **群设置 → 智能群助手**
3. 点击 **添加机器人**
4. 选择 **自定义（通过 Webhook 接入）**
5. 复制 Webhook URL

### Telegram

1. 联系 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建 Bot
3. 获取 Bot Token
4. 将 Bot 添加到群组
5. 获取 Chat ID（联系 [@userinfobot](https://t.me/userinfobot)）

---

## 📊 权重配置

综合分计算公式：

```
综合分 = 成交额百分位 × 40% + 涨跌幅百分位 × 30% + 资金流百分位 × 20% + 新闻得分 × 10%
```

修改权重：编辑 `src/scorer.py` 中的 `WEIGHT_*` 常量。

---

## ⚠️ 注意事项

1. **资金流接口**：云环境（GitHub Actions）偶尔会被东财风控，已实现 3 次重试机制
2. **新闻接口**：云环境稳定，本地环境更可靠
3. **成分股接口**：同花顺源偶尔不稳定，会自动重试
4. **推送失败**：检查 Webhook URL 是否有效，机器人是否被移除

---

## 📝 示例输出

```
🔥 AI 智能体 Top 10 股票热力榜
日期：2026-10-14

#1 协创数据 (300857)
协创数据 +5.23% 成交额 12.50 亿 主力净流入 3200 万 业绩增长超预期
🔗 http://example.com/news/300857

#2 金山办公 (688111)
金山办公 +3.15% 成交额 8.50 亿 主力净流入 1500 万

#3 同花顺 (300033)
同花顺 +2.87% 成交额 6.50 亿 主力净流入 -500 万 发布新产品
🔗 http://example.com/news/300033

---
数据源：同花顺/东方财富/AKShare
⚠️ 投资有风险，入市需谨慎
```

---

## 🛠️ 故障排查

### 问题 1：推送失败

**检查 Webhook URL 是否有效：**

```bash
curl -X POST -H "Content-Type: application/json" -d '{"msgtype":"text","text":{"content":"test"}}' "YOUR_WEBHOOK_URL"
```

### 问题 2：资金流获取失败

查看日志中的重试记录，如果 3 次都失败，该股票会被剔除。

### 问题 3：成分股为空

可能是同花顺接口暂时不稳定，稍后重试即可。

---

## 📄 许可证

MIT License
