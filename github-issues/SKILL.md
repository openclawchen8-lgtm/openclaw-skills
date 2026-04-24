---
name: clw-github-issues
version: 1.0.0
description: GitHub Issue 管理工具。支援 Draft Items → Issues Migration、Issue 批量建立、Board 加入/去重、Body 內容同步。觸發關鍵字：GitHub Issue、Issue Migration、Draft Item、Board 去重、gh issue。
---

# github-issues

GitHub Issue 管理標準化 skill。固化實戰最佳實踐，避免 debug 重複踩坑。

## ⚠️ 實戰學到的關鍵教訓

### 1. `gh api graphql` 的正確姿勢

❌ 錯誤：`gh api graphql --field query=@file`
→ GraphQL 被錯誤解析，回傳 `__schema` 而非 user data

❌ 錯誤：`gh api graphql --field query='{user(login:"xxx"){...}}'`
→ `shell=True` + list 參數時，query 字串被錯誤切割

✅ 正確：`gh api graphql --method POST --field 'query={...}'`
- 用 `shell=True` 執行完整 shell command string
- query 直接內嵌在 command string 中（`--field 'query={...}'`）

### 2. Issue body 換行問題

❌ 錯誤：`gh issue create --body "line1\nline2"`
→ shell 將 `\n` 當作兩個字元（backslash + n）而非換行

✅ 正確：使用 `--body-file`
```bash
echo -e "line1\nline2" > /tmp/body.txt
gh issue create --title "..." --body-file /tmp/body.txt
```
Python 寫入時直接用 `\n` 字串寫入檔案，Python 會寫入真正的換行符。

### 3. Draft Issue body 無法編輯

`updateProjectV2DraftIssueItem` mutation **不存在**於 Projects v2 API。
一旦建立 Draft Issue，body 無法透過 API 修改。

**解法**：建立時就用正確 body；或直接建立真實 Issue 而非 Draft Item。

### 4. `addProjectV2ItemById` 回傳格式

成功時回傳 `{"clientMutationId": null}`，這個 `null` 是成功訊號（不是錯誤）。
Payload 類型 `AddProjectV2ItemByIdPayload` **沒有** `projectV2Item` 欄位。

```python
d = gh_gql(mutation)
cmi = d.get("data", {}).get("addProjectV2ItemById", {}).get("clientMutationId")
# cmi is None → 成功（Python dict 中 null → None）
```

### 5. Shell subprocess 陷阱

❌ 錯誤：`subprocess.run(['gh', 'api', 'graphql', '--method', 'POST', '--field', 'query=...'], shell=True)`
→ 會把 `['gh', ...]` 第一個字元 `g` 當成命令執行

✅ 正確：使用完整 command string + `shell=True`
```python
def gh_run(cmd: str):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)
```

## 工作流程

### 流程 A：建立 Issue 並加入 Board

```
1. 讀取本地 task markdown（T*.md）
2. 解析：title, status, description, assignee
3. 對應 repo：建立 Issue
   → 用 --body-file 避免換行問題
   → body 含 GitHub URL（https://.../blob/main/.../T001.md）
4. 拿 issue node_id（gh api /repos/.../issues/{num} --jq .node_id）
5. 加進 Board（addProjectV2ItemById mutation）
6. 刪除舊 Draft Item（deleteProjectV2Item mutation）
```

### 流程 B：批量更新 Issue body

```
1. 讀取 Issue 當前 body
2. 替換 old_url → new_url（全量替換，不限次數）
3. 寫入 /tmp/body_{num}.txt
4. gh issue edit {num} --body-file /tmp/body_{num}.txt
```

### 流程 C：Board 去重

```
1. 拿 board 所有 items（GraphQL projectV2 items）
2. 比對同一 issue 是否出現多次
3. 刪除多餘的項目（deleteProjectV2Item mutation）
```

## 腳本工具

### migrate_draft_to_issue.py
完整 Migration：Draft Items → GitHub Issues → 加入 Board → 刪除舊 Items

### bulk_update_body.py
批量更新 Issue body，可指定：URL 置換、狀態同步、title 更新

### board_manage.py
Board 操作：列出 items、刪除 item、去重、查狀態

### gh_utils.py
共用工具函式：
- `gh_gql(query)` — 執行 GraphQL query
- `gh_run(cmd)` — 執行 gh CLI 命令
- `get_issue_node_id(owner, repo, num)` — 拿 issue node_id
- `read_task_md(path)` — 解析 task markdown
- `build_issue_body(title, status, file_url, extra)` — 組 issue body

## 常見錯誤對照表

| 錯誤訊息 | 原因 | 解法 |
|---------|------|------|
| `command not found: g` | shell=True + list args | 改用完整 command string |
| `RCURLY` parsing error | `--field query=@file` 不支援 GraphQL | 改 `--method POST --field 'query=...'` |
| `Field doesn't exist: updateProjectV2DraftIssueItem` | Draft Issue body 無法修改 | 直接建 Issue 不建 Draft |
| body 有 `\n` 字面量 | 用 `--body "text\ntext"` | 改用 `--body-file` |
| `clientMutationId: null` | 這是成功訊號 | 不用管，正常繼續 |

## 範本檔案

### issue_body_template.md
標準 Issue body 格式（含任務、狀態、檔案連結）

### task_md_template.md
標準 task markdown 格式（供本地維護）
