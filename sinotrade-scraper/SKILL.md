---
name: sinotrade-scraper
description: "永豐投顧台股報告自動抓取系統，每日 08:30 推送新增報告至 Telegram。"
metadata:
  emoji: "📊"
  version: "1.1.0"
  last_update: "2026-04-23"
---

# sinotrade-scraper — 永豐投顧台股報告抓取

## v1.1.0 重構紀錄（2026-04-23）

**變更摘要：**
- ✅ 建立正式 Python 包結構（`sinotrade_scraper/`）
- ✅ 配置外部化（支援環境變數 + 配置檔）
- ✅ 移除硬編碼路徑
- ✅ 新增 `pyproject.toml` 專案元數據
- ✅ 向後兼容舊 cron 任務

**新結構：**
```
sinotrade-scraper/
├── pyproject.toml
├── sinotrade_scraper/       # 新包（正式 Python 模組）
│   ├── __init__.py
│   ├── __main__.py          # CLI 入口點
│   ├── config.py            # 配置管理
│   ├── scraper.py           # 核心抓取邏輯
│   └── telegram.py          # 通知模組
└── scripts/                  # 舊腳本（向後兼容）
    └── sinotrade_scraper.py
```

**配置方式（優先順序）：**
1. 環境變數：`SINOTRADE_CHROME_PATH` / `SINOTRADE_HISTORY_FILE` / `SINOTRADE_TELEGRAM_CONFIG`
2. 配置檔：`~/.qclaw/sinotrade_config.json`
3. 預設值：macOS Chrome 路徑 / `~/.qclaw/sinotrade_history.json`

---

## 核心功能

- 自動抓取永豐投顧（https://scm.sinotrade.com.tw/）台股報告
- 增量比對，僅推送新增報告
- Telegram 通知（含預覽摘要）

## 使用方式

### 新版 CLI
```bash
# 顯示幫助
python3 -m sinotrade_scraper --help

# 抓取並存檔
python3 -m sinotrade_scraper

# 抓取 + 發 Telegram 通知
python3 -m sinotrade_scraper --telegram
```

### 舊版腳本（向後兼容）
```bash
python3 /Users/claw/scripts/sinotrade_scraper.py --telegram
```

## 配置

### 環境變數
```bash
export SINOTRADE_CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
export SINOTRADE_HISTORY_FILE="~/.qclaw/sinotrade_history.json"
export SINOTRADE_TELEGRAM_CONFIG="~/.qclaw/gold_monitor_config.json"
```

### 配置文件（~/.qclaw/sinotrade_config.json）
```json
{
  "chrome_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "history_file": "~/.qclaw/sinotrade_history.json",
  "telegram_config": "~/.qclaw/gold_monitor_config.json"
}
```

## Cron Job

- **Job ID**: `bbca5563-675d-40a1-8309-09cc814c5e00`
- **排程**: 每週一～五 08:30（Asia/Taipei）
- **Payload**: `python3 -m sinotrade_scraper --telegram`

## 技術細節

- **抓取引擎**: Playwright（Python）+ 系統 Chrome
- **通知通道**: Telegram Bot API
- **關鍵技術**: 首頁 hover「研究報告」觸發 SPA dropdown

## 實測結果

- ✅ 抓取 6 篇台股個股報告（2026-04-22）
- ✅ 增量比對正常（第二次執行：0 篇新增）
- ✅ Telegram 通知發送成功

## 維護備註

- 若網站改版，需更新 `STOCK_REPORT_PATTERN` 正規表達式
- 報告 URL 格式：`/Article/Inner/{uuid}`

## 建立日期

2026-04-22
