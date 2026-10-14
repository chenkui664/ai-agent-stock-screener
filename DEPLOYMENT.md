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

### 问题 3：资金流数据获取失败

查看日志中的错误信息：
- 如果显示 `Connection refused`，是同花顺风控，稍后重试即可
- 系统会自动重试 1 次，仍失败则标记为 0

---

## 📞 获取帮助

- 查看 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解完整架构
- 查看 [README.md](./README.md) 了解详细说明
- 查看 GitHub Issues 提交问题

---

**最后更新**：2026-10-14  
**部署时间**：约 5 分钟
