---
name: free-gold-monitor-pro
version: 2.0.0
description: Gold Monitor Pro - 多金屬價格監控系統。支持黃金、白銀、鉑金，台銀價格 + 國際現貨價對比，多通道告警。
metadata:
  emoji: 🥇
  requires:
    bins:
      - python3
      - node
    pip:
      - fastapi
      - uvicorn
      - pydantic
    npm:
      - playwright
  install:
    - id: pip
      kind: pip
      packages:
        - fastapi
        - uvicorn
        - pydantic
      label: "pip3 install fastapi uvicorn pydantic"
    - id: npm
      kind: npm
      packages:
        - playwright
      label: "npm install playwright"
---

# Gold Monitor Pro

多金屬價格監控系統，支持黃金、白銀、鉑金，同時監控台灣銀行價格與國際現貨價格。

## 📊 功能特性

| 功能 | 說明 |
|------|------|
| 多金屬支持 | 黃金、白銀、鉑金 |
| 雙數據源 | 台銀價格 + Alpha Vantage 國際現貨價 |
| 歷史數據 | SQLite 存儲，支持 1 年數據 |
| REST API | FastAPI 提供歷史數據查詢 |
| 多通道告警 | Telegram、Email、Webhook |
| 價格點位 | 設定買入/賣出目標價 |

## 📦 環境需求

| 依賴 | 安裝方式 |
|------|----------|
| Python | 3.9+ |
| Node.js | 系統內建 |
| playwright | `npm install playwright` |
| fastapi | `pip3 install fastapi uvicorn` |

## 🛠️ 快速開始

### 1. 初始化配置

```bash
python3 ~/.qclaw/workspace/scripts/gold_monitor_pro.py --init
```

編輯配置文件 `~/.qclaw/gold_monitor_pro_config.json`：

```json
{
  "metals": ["gold", "silver", "platinum"],
  "thresholds": {
    "gold": 50,
    "silver": 5,
    "platinum": 100
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "YOUR_BOT_TOKEN",
      "chat_id": "YOUR_CHAT_ID"
    },
    "email": {
      "enabled": false,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "your@email.com",
      "smtp_pass": "your_password",
      "to_email": "your@email.com"
    },
    "webhook": {
      "enabled": false,
      "url": "https://your-webhook-url.com/alert",
      "headers": {}
    }
  },
  "yahoo_finance": {
    "enabled": true
  },
  "alpha_vantage": {
    "api_key": "YOUR_API_KEY",
    "enabled": false
  }
}
```

### 2. 測試告警通道

```bash
python3 ~/.qclaw/workspace/scripts/gold_monitor_pro.py --test-alert
```

### 3. 手動執行價格檢查

```bash
python3 ~/.qclaw/workspace/scripts/gold_monitor_pro.py --check
```

### 4. 發送每日報告

```bash
python3 ~/.qclaw/workspace/scripts/gold_monitor_pro.py --daily
```

## 🌐 REST API

啟動 API 服務器：

```bash
cd ~/.qclaw/workspace/scripts
python3 api_server.py
```

API 端點：

| 端點 | 說明 |
|------|------|
| `GET /` | API 信息 |
| `GET /health` | 健康檢查 |
| `GET /prices` | 所有價格記錄 |
| `GET /prices/{metal}` | 指定金屬最新價格 |
| `GET /prices/{metal}/history?days=30` | 歷史價格 |
| `GET /summary` | 價格摘要統計 |
| `GET /alerts` | 告警記錄 |
| `GET /config` | 系統配置 |

## ⏰ 定時任務

### OpenClaw Cron 配置

```bash
# 價格監控（每 10 分鐘，交易日 09:00-15:30）
openclaw cron create \
  --name "gold-monitor-check" \
  --schedule "*/10 9-15 * * 1-5" \
  --command "python3 ~/.qclaw/workspace/scripts/gold_monitor_pro.py --check"

# 每日報告（15:30）
openclaw cron create \
  --name "gold-monitor-daily" \
  --schedule "30 15 * * 1-5" \
  --command "python3 ~/.qclaw/workspace/scripts/gold_monitor_pro.py --daily"
```

## 📁 檔案結構

```
~/.qclaw/workspace/scripts/
├── gold_monitor_pro.py           # 主程式
├── api_server.py                 # FastAPI 服務
├── config.schema.json            # 配置規範
└── data_adapters/
    ├── __init__.py
    ├── bot_adapter.py            # 台銀數據適配器
    └── alpha_vantage_adapter.py  # Alpha Vantage 適配器

~/.qclaw/
├── gold_monitor_pro_config.json  # 配置文件
├── gold_monitor_pro.db           # SQLite 數據庫
└── gold_monitor_pro_state.json   # 狀態文件
```

## 🔑 API Key 獲取

### Alpha Vantage

1. 訪問 https://www.alphavantage.co/support/#api-key
2. 填寫表單獲取免費 API Key
3. 免費版限制：5 次 API 請求/分鐘，500 次/天

### Telegram Bot

1. 在 Telegram 中搜索 @BotFather
2. 發送 `/newbot` 創建新 Bot
3. 獲取 Bot Token
4. 發送 `/start` 給你的 Bot
5. 訪問 `https://api.telegram.org/bot<TOKEN>/getUpdates` 獲取 Chat ID

## 📊 數據對比說明

| 數據源 | 黃金 | 白銀 | 鉑金 | 單位 |
|--------|------|------|------|------|
| 台灣銀行 | ✅ | ✅ | ✅ | TWD/gram |
| Yahoo Finance | ✅ | ✅ | ✅ | USD/oz |

注意：國際現貨價格單位為美元/盎司，與台銀的台幣/公克不同。

## 🔄 從 Gold Monitor 升級

1. 備份原有配置：
   ```bash
   cp ~/.qclaw/gold_monitor_config.json ~/.qclaw/gold_monitor_config.json.bak
   ```

2. 初始化新配置：
   ```bash
   python3 ~/.qclaw/workspace/scripts/gold_monitor_pro.py --init
   ```

3. 遷移 Telegram 配置到新配置文件

4. 測試新系統：
   ```bash
   python3 ~/.qclaw/workspace/scripts/gold_monitor_pro.py --test-alert
   ```

5. 更新定時任務指向新腳本

## 🐛 故障排除

### 無法獲取台銀價格

- 確認網絡連接正常
- 檢查台銀網站是否維護
- 查看 `node_modules` 是否存在

### Alpha Vantage API 限制

- 免費版每分鐘最多 5 次請求
- 超過限制會返回信息提示
- 建議啟用緩存或降低請求頻率

### Email 發送失敗

- Gmail 需要使用 App Password
- 163 郵箱需要使用授權碼
- 檢查 SMTP 端口和 SSL/TLS 設置
��
