# Ideas2tasks Scripts 目錄

## 📂 腳本清單

### 核心流程

| 腳本 | 功能 | 用法 |
|------|------|------|
| `lifecycle.py` | 掃描 Ideas → 分類 → 彙報 | `python3 lifecycle.py` |
| `executor.py` | 建立 tasks → spawn agents | `python3 executor.py` |
| `classify.py` | 分析 idea → 拆分 tasks | `python3 classify.py <ideas.json>` |
| `scan.py` | 掃描 Ideas 目錄 | `python3 scan.py` |

### 狀態同步（v2.1.0 新增）

| 腳本 | 功能 | 用法 |
|------|------|------|
| `task_status.py` | 統一 Task 狀態讀寫 | `python3 task_status.py <task_file>` |
| `sync_status.py` | 同步 Tasks ↔ Ideas 狀態 | `python3 sync_status.py --fix-history` |
| `task_completion_hook.py` | Task 完成時自動同步 | `python3 task_completion_hook.py <task_file>` |
| `read_task_status.py` | （舊版）狀態讀取 | 已整合到 `task_status.py` |

### 工具腳本

| 腳本 | 功能 |
|------|------|
| `sync_history.json` | 同步歷史記錄 |
| `lifecycle_status.json` | Lifecycle 執行狀態 |
| `executor_status.json` | Executor 執行狀態 |
| `processed_ideas.json` | 已處理 idea 記錄 |

---

## 🔄 完整工作流程

### 1. 日常執行（cron）

```bash
# 每日 09:00 執行
python3 lifecycle.py

# 若有待處理 tasks，發送通知到 Telegram
# 用戶確認後執行
python3 executor.py
```

### 2. Agent 完成任務

```bash
# Agent 完成後自動呼叫
python3 task_completion_hook.py /Users/claw/Tasks/<project>/tasks/T001.md

# 效果：
# 1. 更新 T001.md Status: done
# 2. 同步 idea 檔 task.1 → task.1 done
```

### 3. 維護與修復

```bash
# 檢查同步狀態
python3 sync_status.py --dry-run

# 修復歷史不一致
python3 sync_status.py --fix-history

# 掃描專案狀態
python3 task_status.py /Users/claw/Tasks/<project-name>
```

---

## 🎯 狀態同步系統

### 核心模組

```
task_status.py          # 統一讀寫 Task 狀態
    ↓
sync_status.py          # 同步 Tasks ↔ Ideas
    ↓
task_completion_hook.py # Agent 完成時呼叫
```

### 狀態格式標準

**接受格式：**
```markdown
Status: pending
Status: in-progress
Status: done
```

**自動正規化：**
- `status: done` → `Status: done`
- `Status: ✅ done` → `Status: done`
- `Status: done ✅` → `Status: done`

---

## 📊 技術細節

### 狀態來源優先級

1. **Tasks/ 目錄**（最終真實狀態）
2. **Ideas/ 檔案**（計畫狀態，可能過時）

### 判斷邏輯

- Tasks/ Status: done → 視為 done（覆蓋 idea 檔）
- Tasks/ Status: pending → 看 idea 檔是否有 done 標記
- 兩邊都 done → done
- 兩邊都 pending → pending

---

## 🔍 故障排除

### 問題：重複建立 tasks

**原因：** Tasks/ 已 done，但 idea 檔未同步

**解決：**
```bash
python3 sync_status.py --fix-history
```

### 問題：Status 格式不一致

**原因：** 歷史數據格式不統一

**解決：**
```bash
# 檢查所有 Status 格式
grep -r "^Status:" /Users/claw/Tasks/*/tasks/T*.md | cut -d: -f3 | sort | uniq -c

# 使用 task_status.py 統一讀取（自動正規化）
python3 task_status.py /Users/claw/Tasks/<project>
```

### 問題：找不到 idea 檔案

**原因：** 專案名稱與 idea 檔名不匹配

**解決：**
```bash
# 檢查專案名稱
ls /Users/claw/Tasks/

# 檢查 idea 檔案
ls /Users/claw/Ideas/*.txt

# 確認命名規則：
# - 專案: working-issue
# - Idea: working-issue.txt 或 working_issue.txt
```

---

## 📝 開發指南

### 新增狀態格式支援

編輯 `task_status.py`：
```python
STATUS_NORMALIZE = {
    # 新增格式
    "completed": "done",
    "finished": "done",
    # ...
}
```

### 新增同步邏輯

編輯 `sync_status.py`：
```python
def mark_task_done_in_idea(idea_file, task_num):
    # 新增匹配邏輯
    # ...
```

---

_建立日期: 2026-04-12_
_版本: v2.1.0_
