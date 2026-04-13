# github-projects — 實驗性 / 已知問題快照

> ⚠️ 此 skill 為「過程記錄」，包含失敗經驗與已知問題，非 production-ready。

---

## 🎯 目標

透過 GitHub Projects v2 GraphQL API 管理 Draft Items：
- 修改 Draft Issue body
- 將 Draft Item 升級為真實 Issue
- 批量操作 Board items

**現實**：目標**未完全達成**，以下記錄原因。

---

## ❌ 失敗摘要

| 目標 | 結果 | 原因 |
|------|------|------|
| 修改 Draft Issue body | ❌ 不可能 | GraphQL API 中沒有對應 mutation |
| 將 Draft Item 升級為 Issue | ❌ 不可能 | API 不支援直接轉換 |
| `gh api graphql --field query=@file` 正常運作 | ❌ 失效 | 拿到的資料是 `__schema` 而非 user data |
| `content{...}` 複雜 query | ❌ RCURLY error | `}` 在 shell/gh 解析時被錯誤處理 |
| `addProjectV2ItemById` 回傳 `projectV2Item` | ❌ 欄位不存在 | 只回 `clientMutationId: null`（成功訊號） |

---

## ✅ 實際成功的解法（已遷移到 github-issues skill）

```
放棄：試圖修改 Draft Item
    ↓
改用：建立真實 Issue（gh issue create）
    ↓
加入：Board（addProjectV2ItemById）
    ↓
刪除：舊 Draft Items（deleteProjectV2Item）
```

詳見 `github-issues` skill 的 `migrate_draft_to_issue.py`。

---

## 🔧 想繼續研究？

### 方向 1：官方 CLI Extension
```bash
gh extension install github/projects-beta-cli
gh projects view
```
可能對 board 管理有更完整的支援（未測試）。

### 方向 2：PyGithub Library
```python
from github import Github
```
封裝了 REST + GraphQL，減少 raw API 的坑。

### 方向 3：等待 API 更新
追蹤 [GitHub API Changelog](https://docs.github.com/en/rest/changelog)，
`updateProjectV2DraftIssueItem` 可能未來出現。

---

## 📁 目錄結構

```
github-projects/
├── SKILL.md              ← 完整問題記錄 + GraphQL API 結構
├── README.md             ← 本檔，總覽 + 修復方向
└── scripts/
    └── test_project_api.py  ← 實驗腳本，測試各 API 極限
```

---

## 歡迎 Fork / PR

如果你找到方法解決任何一個「❌」問題，歡迎分享！
