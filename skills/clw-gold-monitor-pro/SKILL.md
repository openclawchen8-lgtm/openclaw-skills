---
name: clw-gold-monitor-pro
version: 2.0.0
description: Gold Monitor Pro - 多金屬價格監控系統。支持黃金、白銀、鉑金，台銀價格 + 國際現貨價對比，多通道告警。SQLite 收盤記錄為唯一比較基準。
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
      - playwright
    npm:
      - playwright
  install:
    - id: pip
      kind: pip
      packages:
        - fastapi
        - uvicorn
        - pydantic
        - playwright
      label: "pip3 install fastapi uvicorn pydantic playwright"
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
| 雙數據源 | 台銀價格 + Yahoo Finance 國際現貨價 |
| 歷史數據 | SQLite 存儲，支持 1 年數據 |
| 買/賣雙價 | 台銀賣出與買進價格同時顯示 |
| REST API | FastAPI 提供歷史數據查詢 |
| 多通道告警 | Telegram、Email、Webhook |
| 價格點位 | 設定買入/賣出目標價 |

## 📦 環境需求

| 依賴 | 安裝方式 |
|------|----------|
| Python | 3.9+ |
| Node.js | 系統內建 |
| playwright | `pip3 install playwright` |
| fastapi | `pip3 install fastapi uvicorn pydantic` |

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

## ⏰ 定時任務（OpenClaw Cron）

| 任務 | 時間 | 說明 |
|------|------|------|
| 價格監控 | 每 10 分鐘 (09:00-21:00) | 即時價 vs 昨天收盤，超閾值通知 |
| 每日報告 | 22:00 | 真正收盤後寫入 SQLite，發送報告 |

> **為什麼是 22:00？** 台銀網站晚上持續更新最終掛牌價，22:00 執行能抓到真正的收盤價。`--check` 只讀取不寫 DB，`--daily` 才寫入收盤記錄作為明日基準。

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

## 📁 相關檔案

| 檔案 | 說明 |
|------|------|
| `~/.qclaw/workspace/scripts/gold_monitor_pro.py` | 主程式 |
| `~/.qclaw/workspace/scripts/api_server.py` | FastAPI 服務 |
| `~/.qclaw/gold_monitor_pro_config.json` | 配置文件 |
| `~/.qclaw/gold_monitor_pro.db` | SQLite 數據庫 |
| `~/.qclaw/workspace/scripts/data_adapters/` | 數據適配器目錄 |

## 📊 比較基準邏輯

`--check` 的比較基準固定為 SQLite 中 `is_daily_close=1` 的最近一筆記錄（昨天 22:00 的收盤價）。

`--daily`（22:00）執行後，會寫入新的收盤記錄，作為明日 `--check` 的比較基準。

## 🔑 API Key 獲取

### Yahoo Finance（免費，無需 Key）

預設啟用，無需任何配置。

### Telegram Bot

1. 在 Telegram 中搜索 @BotFather
2. 發送 `/newbot` 創建新 Bot
3. 獲取 Bot Token
4. 發送 `/start` 給你的 Bot
5. 訪問 `https://api.telegram.org/bot<TOKEN>/getUpdates` 獲取 Chat ID

## 🔄 v1 → v2 升級重點

- ✅ SQLite 新增 `is_daily_close` 欄位（自動 migration）
- ✅ `--check` 只讀取不寫 DB，基準固定為昨日收盤記錄
- ✅ `--daily`（22:00）才寫入收盤記錄
- ✅ 買/賣雙價格同時顯示
- ✅ 比較基準時間固定顯示（昨天收盤時間）

## 📊 數據對比說明

| 數據源 | 黃金 | 白銀 | 鉑金 | 單位 |
|--------|------|------|------|------|
| 台灣銀行 | ✅ | 部分 | 部分 | TWD/gram |
| Yahoo Finance | ✅ | ✅ | ✅ | USD/oz |

注意：國際現貨價格單位為美元/盎司，與台銀的台幣/公克不同。
