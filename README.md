# openclaw-skills

> 🍼 豪的 OpenClaw Skills 備份倉庫備份倉庫 | Backup Repository

[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skills-blue)](https://github.com/openclaw)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

<!-- TOC -->
- [關於 | About](#關於--about)
- [目錄結構 | Directory Structure](#目錄結構--directory-structure)
- [Skills 列表 | Skills List](#skills-列表--skills-list)
  - [原創技能 | Original Skills](#原創技能--original-skills)
  - [工具技能 | Utility Skills](#工具技能--utility-skills)
  - [第三方技能 | Third-Party Skills](#第三方技能--third-party-skills)
- [安裝方式 | Installation](#安裝方式--installation)
- [許可證 | License](#許可證--license)

---

## 關於 | About

本倉庫用於備份所有安裝在 OpenClaw 中的 Skills，包含原創技能與第三方技能。
備份時保留完整目錄結構，方便日後還原或 Fork。

This repository backs up all Skills installed in OpenClaw, including original and third-party skills.
Full directory structure is preserved for restore or Fork purposes.

---

## 目錄結構 | Directory Structure

```
openclaw-skills/
├── README.md              ← 你在這裡
└── skills/
    ├── gold-monitor/          # 🥇 原創：黃金價格監控
    ├── voice-reply/           # 🎙️ 原創：語音雙模回覆
    ├── prompt-injection-filter/  # 🛡️ 原創：Prompt 注入過濾器
    ├── self-improving/        # 🧠 自我提升代理（主版）
    ├── self-improving-agent/  # 🧠 自我提升代理（Alt版）
    ├── summarize/             # 🧾 URL / 檔案摘要工具
    ├── openai-whisper/        # 🎙️ Whisper 語音轉文字
    ├── agent-browser-clawdbot/ # 🌐 無頭瀏覽器自動化
    ├── openclaw-backup/       # 🔒 OpenClaw 備份與還原
    └── github/                # 🐙 GitHub CLI 工具
```

---

## Skills 列表 | Skills List

### 原創技能 | Original Skills

| Skill | 名稱 | 說明 |
|-------|------|------|
| 🥇 `gold-monitor` | Gold Price Monitor | 台灣銀行黃金存摺價格監控系統。追蹤報價、價格變動通知、特定價位提醒、每日收盤報告含走勢圖。 |
| 🎙️ `voice-reply` | Voice Reply | 語音雙模技能：Whisper 語音轉文字 + Edge TTS 文字轉語音，無需 API Key，完全免費。 |
| 🛡️ `prompt-injection-filter` | Prompt Injection Filter | 純 Python 正則 Prompt 注入過濾器，檢測 ignore previous、role play、jailbreak 等攻擊模式。 |

### 工具技能 | Utility Skills

| Skill | 名稱 | 說明 |
|-------|------|------|
| 🔒 `openclaw-backup` | OpenClaw Backup | OpenClaw 配置、憑證、workspace 的完整備份與還原工具，支援 Cron 自動排程。 |
| 🐙 `github` | GitHub CLI | 透過 gh CLI 管理 Issues、PRs、Workflow Runs 及 API 查詢。 |

### 第三方技能 | Third-Party Skills

| Skill | 名稱 | 說明 |
|-------|------|------|
| 🧠 `self-improving` | Self-Improving Agent | 自我反思 + 自我學習。將修正、錯誤、模式寫入分層記憶（HOT/WARM/COLD），AI 持續自我優化。 |
| 🧠 `self-improving-agent` | Self-Improvement Agent | 將學習、錯誤寫入 .learnings/ Markdown 檔案，支援鉤子整合與跨 agent 推廣。 |
| 🧾 `summarize` | URL & File Summarizer | 摘要任意 URL、本地檔案（PDF/圖片/音頻）或 YouTube 影片，支援 Gemini/GPT/Claude 模型。 |
| 🎙️ `openai-whisper` | Whisper STT | 本地語音轉文字，離線運行，多種模型大小可選，無需 API Key。 |
| 🌐 `agent-browser-clawdbot` | Headless Browser Automation | AI 優化的無頭瀏覽器自動化，透過無障礙樹快照與 ref 定址元素，支援多 session 隔離。 |

---

## 安裝方式 | Installation

每個 Skill 都有獨立的 `SKILL.md` 說明文件，請參考各目錄中的說明。

Each skill has its own `SKILL.md` documentation. Refer to the file inside each directory.

**通用安裝方式（以 ClawHub 為例）：**

```bash
# 安裝單一 Skill
skillhub install <skill-name>

# 或透過 OpenClaw CLI
openclaw skills install <skill-name>
```

**手動安裝：**

```bash
# 將感興趣的 skill 目錄複製到 OpenClaw skills 目錄
cp -r skills/<skill-name> ~/.qclaw/workspace/skills/
```

---

## 許可證 | License

本倉庫中原創技能（`gold-monitor`、`voice-reply`、`prompt-injection-filter`）採用 MIT License。

Third-party skills retain their original licenses as specified in their respective directories.

---

*本倉庫的最後更新時間：2026-04-04*
