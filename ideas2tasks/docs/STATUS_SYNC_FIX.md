# Ideas2tasks 狀態同步修復方案

## 🎯 問題分析

### 核心問題：兩套狀態系統完全不同步

**問題流程：**
```
idea 檔 (task.N / task.N done) → lifecycle.py 只看這個
         ↕ 完全不同步 ↕
Tasks/ 目錄 (T001.md Status: ...) → agent 執行完改這個
```

**結果：**
1. Agent 完成 T001 → 改 T001.md `Status: done` ✅
2. 但 idea 檔裡的 `task.1` 沒加 `done` → lifecycle 下次掃到還是 pending ❌
3. executor 再建一輪 → 重複建立 ❌

### 第二個問題：Status 格式不統一

**統計結果：**
- `Status: pending` (69 個)
- `Status: done` (20 個)
- `status: done` (3 個，小寫)
- `Status: ✅ done` (1 個)
- `Status: done ✅` (1 個)

連讀取現有狀態都會漏！

---

## 🛠️ 修復方案

### 修復 1：狀態同步器（`sync_status.py`）

**核心功能：**
- 當 Task 狀態變更為 done，自動更新對應 idea 檔的 `task.N done` 標記
- 提供手動同步工具，修復歷史不一致

**實作邏輯：**
```python
def mark_task_done_in_idea(idea_file, task_num):
    """
    在 idea 檔案中標記 task.N 為 done。
    
    匹配格式：task.1 → task.1 done
    跳過已有 done 標記的行
    """
    pattern = re.compile(rf'^(task\.{task_num})(\s+done)?[\s_]*(.*)$', re.IGNORECASE)
    # ... 替換邏輯
```

**用法：**
```bash
# 同步所有專案
python3 sync_status.py

# 預覽模式（不實際修改）
python3 sync_status.py --dry-run

# 修復歷史不一致
python3 sync_status.py --fix-history
```

---

### 修復 2：統一狀態讀取（`task_status.py`）

**核心功能：**
- 正規化讀取（忽略大小寫、emoji、空白）
- 統一寫入格式：`Status: pending` / `in-progress` / `done`

**實作邏輯：**
```python
STATUS_NORMALIZE = {
    "pending": "pending",
    "in-progress": "in-progress",
    "in_progress": "in-progress",
    "done": "done",
    "completed": "done",
    "finished": "done",
    # ...
}

def read_task_status(task_file):
    """
    從 task 檔案讀取 Status，回傳正規化後的值。
    
    處理以下格式：
    - Status: pending
    - status: done
    - **Status**: ✅ done
    - - Status: done ✅
    """
    pattern = re.compile(r'^[-*\s]*\**Status\**\s*[:：]\s*(.+)$', ...)
    # ... 正規化邏輯
```

**用法：**
```bash
# 讀取單一 task 狀態
python3 task_status.py /path/to/T001.md

# 掃描整個專案
python3 task_status.py /Users/claw/Tasks/working-issue
```

---

### 修復 3：lifecycle 增強

**核心邏輯：**
```python
def run_classify(ideas):
    """
    修2 核心邏輯：
    - 先掃描 /Users/claw/Tasks/{project}/tasks/T*.md 的 Status
    - Tasks/ 已 done 的 task → 從 pending 中移除，計入 done_count
    - 兩邊合併判斷，避免 idea 檔沒標 done 但 Tasks/ 已完成的問題
    """
    for idea in ideas:
        result = classify_idea(idea)
        
        # 掃描 Tasks/ 目錄的實際狀態
        tasks_status = scan_project_tasks(project_dir)
        done_in_tasks = len(tasks_status.get("done", []))
        
        # 如果 Tasks/ 有已完成的 task，修正 idea 檔的 done_count
        if done_in_tasks > result.get("done_count", 0):
            result["done_count"] = done_in_tasks
            result["_status_source"] = "Tasks/ (覆蓋 idea 檔)"
            # ...
```

---

### 修復 4：Task 完成掛鉤（`task_completion_hook.py`）

**核心功能：**
- Agent 完成任務時呼叫，同步更新 Tasks/ 和 Ideas/ 的狀態
- 支援掃描所有已 done 的 tasks，批量同步到 ideas

**實作邏輯：**
```python
def on_task_completed(task_file, new_status="done"):
    """
    步驟：
    1. 更新 task 檔案的 Status
    2. 找到對應的 idea 檔案
    3. 在 idea 檔案中標記 task.N done
    """
    # 1. 更新 task 狀態
    write_task_status(task_file, new_status)
    
    # 2. 找到 idea 檔案
    idea_file = find_idea_file(project_name)
    
    # 3. 同步到 idea 檔案
    if new_status == "done":
        mark_task_done_in_idea(idea_file, task_num)
```

**用法：**
```bash
# 標記 task 為 done（同時同步 idea 檔）
python3 task_completion_hook.py /Users/claw/Tasks/working-issue/tasks/T001.md

# 掃描所有已 done 的 tasks，同步到 ideas
python3 task_completion_hook.py --scan-done
```

---

## 📊 執行結果

### 歷史同步結果（2026-04-12）

```
🔍 掃描已完成的 tasks...
📊 統計：
  掃描專案: 28
  同步 tasks: 9

✅ 成功同步：
  - openclaw.txt: task.1, task.2, task.3, task.4, task.5
  - claw-sessions-issue.txt: task.1
  - github-data-review.txt: task.1, task.2
  - gold-monitor-issue.txt: task.1
```

---

## 🔄 完整工作流程

### 正常流程（修復後）

```
1. lifecycle.py 掃描 Ideas/
   ├─ 讀取 idea 檔的 task.N done 標記
   ├─ 同時掃描 Tasks/ 目錄的實際狀態
   └─ 合併判斷：兩邊取 done 狀態

2. executor.py 建立 tasks
   ├─ 建立 T001.md（Status: pending）
   └─ （暫不回寫 idea 檔，因為 task 還沒完成）

3. Agent 執行任務
   ├─ 完成後呼叫 task_completion_hook.py
   ├─ 更新 T001.md（Status: done）
   └─ 同步 idea 檔（task.1 → task.1 done）

4. 下次 lifecycle.py 掃描
   ├─ idea 檔已有 task.1 done ✅
   ├─ Tasks/ 目錄 T001.md Status: done ✅
   └─ 不會重複建立 ✅
```

---

## 📝 維護指南

### 日常維護

1. **定期檢查同步狀態**
   ```bash
   python3 sync_status.py --dry-run
   ```

2. **修復不一致**
   ```bash
   python3 sync_status.py --fix-history
   ```

3. **驗證狀態格式**
   ```bash
   # 統計各種 Status 格式
   grep -r "^Status:" /Users/claw/Tasks/*/tasks/T*.md | cut -d: -f3 | sort | uniq -c
   ```

### 新增功能建議

- [ ] 在 executor.py 建立任務後，也回寫 idea 檔的 task 編號（雙向同步）
- [ ] 建立 Web UI 查看同步狀態
- [ ] 支援手動標記 done（從 idea 檔反向同步到 Tasks/）

---

## 🎓 技術細節

### 狀態來源優先級

1. **Tasks/ 目錄**：最終真實狀態（Agent 實際執行的結果）
2. **Ideas/ 檔案**：計畫狀態（可能過時）

**判斷邏輯：**
- Tasks/ Status: done → 視為 done（覆蓋 idea 檔狀態）
- Tasks/ Status: pending → 看 idea 檔是否有 done 標記
- 兩邊都 done → done
- 兩邊都 pending → pending

### 狀態格式標準

**統一格式：**
```markdown
- **Status**: pending
- **Status**: in-progress
- **Status**: done
```

**不接受：**
- `status: done`（小寫）
- `Status: ✅ done`（帶 emoji）
- `Status: done ✅`（emoji 後置）

---

_建立日期: 2026-04-12_
_修復版本: v2.1.0_
