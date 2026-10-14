# 🚀 快速部署指南 - 5 分钟完成

## 前置条件

- ✅ GitHub 账号
- ✅ 飞书/企业微信/钉钉账号（用于接收推送）
- ✅ 千问 API Key（可选，用于大模型摘要）

---

## 步骤 1：Fork 仓库（1 分钟）

1. 打开 GitHub 仓库
2. 点击右上角 **Fork** 按钮
3. 等待 Fork 完成

---

## 步骤 2：获取机器人 Webhook URL（2 分钟）

### 飞书（推荐）

1. 打开飞书群聊
2. 点击右上角 **···** → **群机器人**
3. 点击 **添加机器人** → **自定义机器人**
4. 设置名称（如：股票推送助手）
5. 复制 **Webhook URL**

示例：
```
https://open.feishu.cn/open-apis/bot/v2/hook/2c9667c7-5058-4127-b5b0-ca5dee8a7abd
```

### 企业微信

1. 打开企业微信群聊
2. 点击右上角 **···** → **添加群机器人**
3. 设置名称，点击 **添加**
4. 复制 **Webhook URL**

### 钉钉

1. 打开钉钉群聊
2. 点击右上角 **···** → **群设置** → **智能群助手**
3. 点击 **添加机器人** → **自定义**
4. 复制 **Webhook URL**

---

## 步骤 3：配置 GitHub Secrets（1 分钟）

1. 进入你的 Fork 仓库
2. 点击 **Settings** 标签
3. 左侧菜单选择 **Secrets and variables** → **Actions**
4. 点击 **New repository secret**

添加以下 Secrets：

| Name | Value | 必需 |
|------|-------|------|
| `FEISHU_WEBHOOK_URL` | 步骤 2 获取的 Webhook URL | ✅ |
| `DASHSCOPE_API_KEY` | `sk-0674fb7732444b62919651ca08a86095` | 可选 |

点击 **Add secret** 保存。

---

## 步骤 4：配置 Variables（30 秒）

在同一页面：

1. 点击 **Variables** 标签
2. 点击 **New repository variable**

添加以下 Variables：

| Name | Value | 说明 |
|------|-------|------|
| `CONCEPT_KEY` | `AI 智能体_同花顺` | 概念板块 |
| `TOP_N` | `10` | 返回 Top 10 |
| `CANDIDATE_N` | `15` | 候选池大小 |

点击 **Add variable** 保存。

---

## 步骤 5：手动测试（30 秒）

1. 点击 **Actions** 标签
2. 选择 **AI 智能体 Top 10 股票热力榜** 工作流
3. 点击 **Run workflow** 按钮
4. 选择分支（main），点击 **Run workflow**

等待 1-2 分钟，查看运行状态。

---

## 步骤 6：验证结果

### 方式 1：查看 GitHub Actions 日志

1. 点击刚运行的工作流记录
2. 查看日志输出
3. 确认显示：`feishu: ✓ 成功`

### 方式 2：查看飞书群聊

打开飞书群，应该收到消息：

```
📈 AI 智能体 Top 10 股票热力榜

🏆 第 1 名：芒果超媒 (300413)
摘要：芒果超媒 +6.83% 成交额 37.83 亿 主力净流入 3.24 亿
关键新闻：[新闻标题](链接)

...

📊 数据来源：同花顺/东方财富
⏰ 更新时间：2026-10-14
⚠️ 风险提示：以上内容仅供参考，不构成投资建议
```

---

## ✅ 完成！

现在系统已经配置完成，每天上午 11:00（北京时间）自动运行。

---

## 🔧 后续配置

### 添加更多推送平台

在 **Secrets** 中添加：

| Name | Value |
|------|-------|
| `WECHAT_WEBHOOK_URL` | 企业微信 Webhook |
| `DINGTALK_WEBHOOK_URL` | 钉钉 Webhook |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |

### 修改推送时间

编辑 `.github/workflows/stock_screener.yml`：

```yaml
on:
  schedule:
    - cron: '0 3 * * *'  # 改为其他时间
```

Cron 表达式参考：
- `0 3 * * *` = 每天 11:00（北京时间）
- `0 7 * * *` = 每天 15:00（北京时间）
- `0 1 * * 1` = 每周一 9:00（北京时间）

### 修改概念板块

在 **Variables** 中修改：

| Name | Value |
|------|-------|
| `CONCEPT_KEY` | `AI 智能体_东财` |

可用概念：
- `AI 智能体_同花顺`（886099）
- `AI 智能体_东财`（BK0809）

---

## ⚠️ 故障排查

### 问题 1：推送失败

**检查 Webhook URL 是否正确：**

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"test"}}' \
  "YOUR_FEISHU_WEBHOOK_URL"
```

如果返回 `success: ok`，说明 Webhook 正常。

### 问题 2：GitHub Actions 不运行

**检查是否启用了 Actions：**

1. Settings → Actions → General
2. 确保 **Allow all actions and reusable workflows** 已选中

### 问题 3：资金流数据获取失败（已知问题）

**当前状态**：同花顺资金流接口在部分网络环境下不可用

**错误信息**：
```
ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**原因**：同花顺对 IP 的连接级风控（非你个人问题）

**解决方案**：

#### 方案 A：等待网络恢复（推荐）
- 同花顺的风控通常是临时性的
- 等待 10-30 分钟后重试
- GitHub Actions 会自动重试

#### 方案 B：临时降级运行
系统会自动降级为**三因子评分**：
- ✅ 成交额（40%）
- ✅ 涨跌幅（30%）
- ✅ 新闻（10%）
- ❌ 资金流（20%，暂时缺失）

**影响**：
- 系统仍可正常运行
- 飞书推送正常
- 只是缺少资金流维度

#### 方案 C：切换数据源
在 `config.py` 中切换到东财源：
```python
DEFAULT_CONCEPT = "AI 智能体_东财"
```

---

### 问题 4：大模型摘要未启用

**检查是否配置了 API Key：**

1. Settings → Secrets and variables → Actions
2. 确认 `DASHSCOPE_API_KEY` 已配置

**如果未配置**：
- 系统会自动降级到基础摘要模式
- 仍能生成摘要，但不够智能
- 不影响其他功能

---

## 📊 当前系统状态（2026-10-14）

| 组件 | 状态 | 说明 |
|------|------|------|
| ✅ 成分股获取 | 正常 | 同花顺 469 只成分股 |
| ✅ 行情数据 | 正常 | 成交额、涨跌幅 |
| ✅ 新闻获取 | 正常 | akshare 稳定 |
| ✅ 大模型摘要 | 正常 | 千问 API（需配置 Key） |
| ✅ 飞书推送 | 正常 | 已测试成功 |
| ⚠️ 资金流数据 | **临时不可用** | 同花顺接口风控 |

**重要说明**：
- 资金流接口不可用是**临时网络问题**
- 其他所有功能（成分股、行情、新闻、推送、大模型）**全部正常**
- 系统会自动降级运行，不影响基本功能
- 等网络恢复后，资金流数据会自动恢复

---

## 📞 获取帮助

- 查看 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解完整架构
- 查看 [README.md](./README.md) 了解详细说明
- 查看 GitHub Issues 提交问题

---

**最后更新**：2026-10-14  
**部署时间**：约 5 分钟
