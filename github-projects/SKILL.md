---
name: clw-github-projects
version: 1.0.0
description: GitHub Projects (Board) 原生 GraphQL API 管理工具。紀錄 Draft Item Migration 失敗經驗與已知問題。⚠️ 此 skill 為「問題快照」，建議搭配 github-issues 使用。
---

# github-projects

GitHub Projects v2（Board）原生 GraphQL API 管理工具。

> ⚠️ **重要說明**：這個 skill 記錄了 Draft Item → Real Issue Migration 的**完整失敗過程**。已知多個 GraphQL API 限制導致無法達成目標，詳見「已知問題」章節。此 skill 保留作為日後修復或社群參考的起點。

## 為什麼建立這個 skill

這次 Migration 最終**繞道成功**（放棄原生 Board API，改用 `gh issue create` + `gh project item-add`），但過程中對 GitHub Projects v2 GraphQL API 有了完整的第一手認識。把這些知識記錄下來，讓：
1. **自己日後**想重啟時有起點
2. **其他人**想改版或提 PR 有依据

---

## 核心 API 結構

### Projects v2 GraphQL Endpoint

```
POST https://api.github.com/graphql
Authorization: Bearer <token>
```

### 常用 Query / Mutation

```graphql
# 查 Board 所有 Items
query {
  user(login: "<owner>") {
    projectV2(number: <N>) {
      items(first: 100) {
        nodes {
          id
          type
          content {
            __typename
            ... on Issue { number title }
            ... on DraftIssue { id title }
            ... on PullRequest { number title }
          }
          fieldValues(first: 10) {
            nodes { ... }
          }
        }
      }
    }
  }
}

# 加 Issue 到 Board
mutation {
  addProjectV2ItemById(input: {
    projectId: "<projectId>"
    contentId: "<issueNodeId>"
  }) {
    clientMutationId  # ← 成功時回傳 null（None），不是 projectV2Item
    projectV2Item { id }
  }
}

# 刪除 Board Item
mutation {
  deleteProjectV2Item(input: {
    projectId: "<projectId>"
    itemId: "<itemId>"
  }) {
    clientMutationId
  }
}
```

---

## 已知問題（Blocked Issues）

### ❌ Issue #1：Draft Issue body 無法透過 API 修改

**GraphQL Mutation 不存在**

測試過的 mutations（全部失敗）：

| Mutation | 結果 |
|----------|------|
| `updateProjectV2DraftIssueItem` | ❌ Field doesn't exist |
| `updateProjectV2Item` | ❌ Field doesn't exist |
| `updateProjectV2ItemContent` | ❌ Field doesn't exist |

**現階段解法**：放棄修改 Draft Item，直接建立新的真實 Issue。

```python
# 繞道：直接建立 Issue，不用 Draft Item
gh issue create --title "..." --body "..."
```

---

### ❌ Issue #2：`content{...}` 在複雜 query 中 RCURLY error

**症狀**

```bash
gh api graphql --field query=@file query.graphql
# 或
gh api graphql --method POST -f query='{user(login:"xxx"){...content{__typename}...}}'
```

兩種寫法都失敗：

1. `--field query=@file`：GraphQL 被錯誤解析，回傳 `__schema` 而非 user data
2. `-f query='...content{...}'`：RCURLY parsing error（`}` 被錯誤解析）

**懷疑原因**

`gh api graphql` 內部對 `--field` / `-f` 的處理與標準 `gh api --graphql` 不同。GraphQL query 中的 `{` / `}` 在 shell 轉義後可能被干擾。

**Workaround**：分開查，先拿 items ID 清單，再各自查 content

```python
# 分兩步：先拿 ID
gql = "{user(login:\"...\"){projectV2(number:N){items(first:100){nodes{id}}}}}"
items = gh_gql(gql)["data"]["user"]["projectV2"]["items"]["nodes"]

# 再各自用 gh project item-get 拿 content（REST fallback）
for item in items:
    r = gh_run(f'gh project item-get {N} --owner {owner} --format json --id {item["id"]}')
    # r.stdout 是 JSON，包含 content 詳細資訊
```

---

### ❌ Issue #3：`addProjectV2ItemById` 回傳無 `projectV2Item` 欄位

**症狀**

```python
d = gh_gql(mutation)
item = d["data"]["addProjectV2ItemById"]["projectV2Item"]  # KeyError!
```

**根因**：GitHub API 的 `AddProjectV2ItemByIdPayload` 類型中，`projectV2Item` 欄位在某些條件下不存在。成功時只回傳 `clientMutationId: null`。

```json
{
  "data": {
    "addProjectV2ItemById": {
      "clientMutationId": null  // ← 這就是成功訊號
    }
  }
}
```

**解法**：不要取 `projectV2Item`，直接以 `clientMutationId is None` 判斷成功

```python
ok = d["data"]["addProjectV2ItemById"].get("clientMutationId") is None
```

---

### ❌ Issue #4：`gh api graphql --field query=@file` 拿到 `__schema`

**症狀**

```bash
gh api graphql --field query=@file query.graphql
```

Output 是：
```json
{"data":{"__schema": {...}}}
```

而非預期的 user data。

**懷疑原因**：`--field` flag 在 `gh api graphql` 模式下被 gh 內部攔截處理，而非當作 GraphQL query 傳遞。

**解法**：直接用 `-f query='{...}'` 配合 `--method POST`

```python
def gh_gql(query: str) -> dict:
    cmd = "gh api graphql --method POST --field 'query=" + query + "'"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return json.loads(r.stdout)
```

---

## 嘗試過但未驗證的想法

### 嘗試 A：REST API 直接改 Draft Issue body

```
PATCH /repos/{owner}/{repo}/projects/columns/cards/{card_id}
```

→ 只能改 card 位置，無法改 body

### 嘗試 B：`gh project item-edit` 改 Board item 欄位

```bash
gh project item-edit <item-id> --field "Status" --value "Done"
```

→ `item-edit` 只能改 Project 本身屬性，**不是 item 的內容**

### 嘗試 C：建立 Issue 時直接加入 Board

```bash
gh issue create --project <project-number> --title "..."
```

→ 可行！但仍無法先建立 Draft Issue 再升級

### 嘗試 D：GraphQL schema introspection

```
POST /graphql
{"query": "{ __type(name: \"AddProjectV2ItemByIdPayload\") { fields { name } } }"}
```

→ 可拿到 schema，但最終仍確認 `projectV2Item` 欄位不存在

---

## 實驗腳本

| 腳本 | 狀態 | 說明 |
|------|------|------|
| `test_project_api.py` | 🔬 實驗中 | 測試各 GraphQL mutation 可用性 |
| `test_content_query.py` | 🔬 實驗中 | 測試 `content{...}` query 的正確姿勢 |
| `test_rest_fallback.py` | 🔬 實驗中 | REST API 作為 GraphQL 的 fallback |

---

## 修復路線圖（待驗證）

### Plan A（推薦）：Python GitHub API Library

```python
from github import Github
g = Github(token)
repo = g.get_repo("owner/repo")
issue = repo.get_issue(N)
# 然後用 PyGithub 拿 node_id，再 call GraphQL
```

PyGithub 封裝了 REST + GraphQL，減少 raw API 的坑。

### Plan B：GitHub CLI Extensions

[gh-projects](https://github.com/github/projects-beta-cli) 是 GitHub 官方出的 CLI extension，可能對 board 管理有更完整的支援。需另外安裝：

```bash
gh extension install github/projects-beta-cli
```

### Plan C：等待 GitHub API 更新

`updateProjectV2DraftIssueItem` mutation 可能在未來版本出現，可追蹤 [GitHub API Changelog](https://docs.github.com/en/rest/changelog)。

---

## 觸發關鍵字

GitHub Project Board、GraphQL API、projects v2、Draft Issue、Migration（失敗經驗）
