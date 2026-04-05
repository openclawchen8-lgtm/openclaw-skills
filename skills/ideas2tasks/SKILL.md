---
name: ideas2tasks
description: |
  將 /Users/claw/Ideas 中的臨時想法自動分類、拆解為敏捷專案任務。
  觸發條件：用戶提到「idea轉task」「ideas2tasks」「想法拆分」「專案規劃」「task管理」，
  或要求掃描 Ideas 目錄、建立專案任務、分配團隊成員。
metadata:
  emoji: "📋"
  version: "1.0.0"
---

# ideas2tasks — 想法轉敏捷任務

## 核心概念

將零散的想法（ideas）系統化轉為可執行的專案任務（tasks），搭配虛擬 Scrum 團隊成員分工執行。

## 📂 目錄結構

```
/Users/claw/Ideas/           # 臨時想法存放區
  ├── *.txt                  # 待處理的 idea 檔案
  └── _done/                 # 已處理歸檔區（自動移入）

/Users/claw/Tasks/           # 專案任務區
  └── <project-name>/
      ├── README.md          # 專案概覽、成員分工、進度
      └── tasks/
          ├── T001.md        # 個別任務檔案
          ├── T002.md
          └── ...
```

## 👥 團隊成員

| 角色 | 名稱 | OpenClaw Agent ID | Workspace |
|------|------|-------------------|-----------|
| Planner | **豪（用戶本人）** | `main` | `/Users/claw/.qclaw/workspace/` |
| Coder 1 | 碼農 1 號 | `agent-f937014d`（代可行） | `~/.qclaw/workspace-agent-f937014d/` |
| Coder 2 | 碼農 2 號 | `agent-coder2` | `~/.qclaw/workspace-coder2/` |
| DocWriter | 安安 | `agent-ann` | `~/.qclaw/workspace-ann/` |
| Reviewer | 樂樂 | `agent-lele` | `~/.qclaw/workspace-lele/` |

Spawn 方式：`sessions_spawn(agentId="agent-ann")` 等，詳見各成員的 IDENTITY.md/SOUL.md。

## 🔄 完整流程

### 步驟 1：掃描 Ideas
掃描 `/Users/claw/Ideas/*.txt`，排除 `_done/` 子目錄。
空檔案（0 bytes）跳過不處理。

### 步驟 2：分析與分類
閱讀每個 idea 檔案的內容，判斷：
- 歸屬哪個專案（新專案或已有專案）
- 涉及哪些技術領域
- 優先級（高/中/低）

### 步驟 3：拆分 Tasks
- 每個 idea 最多拆成 **10 個 tasks**
- 若超過 10 個，先說明原因和拆分方式，**等用戶確認後再拆**
- 每個 task 應具備明確的完成條件

### 步驟 4：專案命名
- 從 idea 內容提取關鍵字作為專案名稱
- **發給用戶確認後才執行**
- 命名風格：英文、簡短、見名知義（如 `gold-monitor`、`backup-system`）

### 步驟 5：建立專案結構
確認後建立目錄和檔案：
```
/Users/claw/Tasks/<project-name>/README.md
/Users/claw/Tasks/<project-name>/tasks/T001.md ~ T0xx.md
```

### 步驟 6：分配任務
根據 task 類型分配給對應成員：
- 開發/腳本 → Coder 1 或 Coder 2
- 文檔撰寫 → DocWriter
- 驗收/審核 → Reviewer
- 規劃/協調 → Planner（豪）

### 步驟 7：歸檔 Idea 檔案
將已處理的 `.txt` 移到 `/Users/claw/Ideas/_done/`：
```bash
mkdir -p /Users/claw/Ideas/_done
mv /Users/claw/Ideas/<filename>.txt /Users/claw/Ideas/_done/
```

## 📝 Task 檔案格式

每個 task md 檔案格式：

```markdown
---
id: T001
project: <project-name>
title: <任務標題>
assignee: <成員名稱>
priority: high|medium|low
status: pending|in-progress|review|done
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

## 描述
<任務詳細說明>

## 完成條件
- [ ] <具體可驗證的條件 1>
- [ ] <具體可驗證的條件 2>

## 產出
<預期產出物：腳本、文檔、配置等>

## 備註
<補充說明>
```

## 📊 專案 README 格式

```markdown
# <專案名稱>

## 概覽
<專案簡述>

## 團隊分工
| 角色 | 成員 | 負責 Tasks |
|------|------|-----------|
| Planner | 寶寶 | T001, T005 |
| Coder 1 | 碼農 1 號 | T002, T003 |
| DocWriter | 安安 | T004 |
| Reviewer | 樂樂 | 全部 |

## 進度
- 總 tasks: N
- 已完成: X
- 進行中: Y
- 待處理: Z

## Task 列表
| ID | 標題 | 負責人 | 狀態 | 優先級 |
|----|------|--------|------|--------|
| T001 | ... | ... | pending | high |
```

## ⏰ Lifecycle（每日定時）

cron 每天 **09:00 Asia/Taipei** 執行：

1. 執行 `scripts/lifecycle.py`（掃描 → 分類 → 彙整摘要）
2. 結果寫入 `scripts/lifecycle_status.json`（供 AI 讀取）
3. 有待處理 tasks → 發送摘要到 Telegram，請豪確認
4. 無新 idea → 安靜（不通知）

## ⚠️ 重要規則

1. **專案命名必須先確認** — 不可未確認就直接建立目錄
2. **Task 拆分上限 10 個** — 超過需說明原因並等確認
3. **已標記 done 的 idea task** — 檔案內含 "done" 的行視為已完成，整體仍需分析是否還有未完成項
4. **歸檔不刪除** — 移到 `_done/` 而非刪除
5. **空檔案跳過** — 0 bytes 的 .txt 不處理
