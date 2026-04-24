# {project_name}

## 任務狀態

| Task | 標題 | 負責人 | 優先順序 | 狀態 |
|------|------|--------|---------|------|
| {rows}

## 更新規範

每次狀態變更時，**同時更新** T\*.md 與本檔案：

| 變更時機 | T\*.md 更新 | README 更新 |
|---------|------------|------------|
| `pending` → `in-progress` | `status: pending` → `status: in-progress` | `⬜ pending` → `🔄 in-progress` |
| `in-progress` → `done` | `status: in-progress` → `status: done` | `🔄 in-progress` → `✅ done` |

- 更新 T\*.md 時一併更新 `updated` 欄位
- 完成後同步 GitHub Issue 狀態（`--sync-state`）
