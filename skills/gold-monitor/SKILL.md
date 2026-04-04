---
name: gold-monitor
version: 1.0.0
description: 台灣銀行黃金存摺價格監控系統。支援價格變動通知、特定價格點位監控與每日收盤報告。
metadata:
  emoji: 🥇
  requires:
    bins:
      - ffmpeg
      - node
    pip:
      - playwright
      - matplotlib
  install:
    - id: brew
      kind: brew
      formula: ffmpeg
      label: "brew install ffmpeg"
    - id: pip
      kind: pip
      packages:
        - playwright
        - matplotlib
      label: "pip3 install --user playwright matplotlib"
    - id: npm
      kind: npm
      packages:
        - playwright
      label: "npm install playwright (in workspace/scripts)"
---

# Gold Monitor Skill

台灣銀行黃金存摺價格自動監控系統，支援價格變動通知、特定價格點位監控與每日收盤報告。

## 📊 功能說明

| 功能 | 說明 |
|------|------|
| 價格變動監控 | 每 10 分鐘檢查，變動超過閾值時通知 |
| 特定價格點位 | 設定買入/賣出目標價，觸達時通知 |
| 每日收盤報告 | 每日 15:30 發送收盤價 + 走勢圖 |

## 📦 環境需求

| 依賴 | 安裝方式 |
|------|----------|
| Python | 3.9+ |
| ffmpeg | `brew install ffmpeg` |
| node | 系統內建 |
| playwright | `npm install playwright` |
| matplotlib | `pip3 install --user matplotlib` |

## 🛠️ 快速開始

### 1. 配置

在 `~/.qclaw/gold_monitor_config.json` 中設定：

```json
{
  "threshold": 50,
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "price_targets": [
    {"price": 4500, "type": "buy", "label": "進場點"},
    {"price": 5000, "type": "sell", "label": "出場點"}
  ]
}
```

### 2. 指令用法

```bash
# 查看配置
python3 ~/.qclaw/workspace/scripts/gold_monitor.py --config

# 調整閾值
python3 ~/.qclaw/workspace/scripts/gold_monitor.py --set-threshold 30

# 新增價格點位
python3 ~/.qclaw/workspace/scripts/gold_monitor.py --add-target 4500:buy:進場點

# 列出價格點位
python3 ~/.qclaw/workspace/scripts/gold_monitor.py --list-targets

# 移除價格點位
python3 ~/.qclaw/workspace/scripts/gold_monitor.py --remove-target 4500

# 重置觸發狀態
python3 ~/.qclaw/workspace/scripts/gold_monitor.py --reset-targets

# 手動檢查
python3 ~/.qclaw/workspace/scripts/gold_monitor.py --check

# 手動發送日報
python3 ~/.qclaw/workspace/scripts/gold_monitor.py --daily
```

## ⏰ 定時任務

透過 OpenClaw cron 設定：

| 任務 | 時間 | 說明 |
|------|------|------|
| 價格監控 | 每 10 分鐘 (09:00-15:30) | 變動超閾值 + 點位觸發 |
| 每日報告 | 15:30 | 收盤價 + 走勢圖 |

## 📈 走勢圖基準日

| 當日 | 比較基準 |
|------|----------|
| 週一 | 上週五收盤 → 週一走勢 |
| 週二 ~ 週五 | 前一交易日收盤 → 當日走勢 |

## 📁 相關檔案

| 檔案 | 說明 |
|------|------|
| `~/.qclaw/workspace/scripts/gold_monitor.py` | 主程式 |
| `~/.qclaw/gold_monitor_config.json` | 配置檔 |
| `~/.qclaw/gold_monitor_state.json` | 狀態檔 |
| `~/.qclaw/gold_price_history.json` | 歷史記錄 |
