# Scrum Task Tracker Skill

Scrum 專案管理與任務追蹤標準流程。確保所有專案遵循統一的任務拆分、執行、驗證和報告規範。

## 觸發條件

當用戶提到以下關鍵詞時觸發：
- "Scrum"
- "任務追蹤"
- "task tracking"
- "專案管理"
- "拆分任務"
- "建立任務"
- "驗證任務"
- "報告"

## 核心流程

### 1. 任務拆分原則

```
收到需求 → 立即拆分所有子任務 → 建立 T001-T00N → 等待用戶確認後逐步執行
```

**拆分規則**：
- 每個任務單一職責（Single Responsibility）
- 任務粒度：4-8 小時可完成
- 明確依賴關係（T003 ← T001）
- 指派明確負責人

**任務檔案格式**：
```markdown
## TXXX - 任務名稱
- **Type**: Feature | Bugfix | Refactor | Verification
- **Assignee**: 碼農1號 | 碼農2號 | 安安 | 樂樂
- **Priority**: P0 | P1 | P2
- **Parent**: TXXX（如有）
- **Depends**: TXXX, TXXX（前置任務）
- **Description**: 
  - 具體內容...
- **Acceptance Criteria**:
  - [ ] 驗收條件1
  - [ ] 驗收條件2
- **Status**: pending | in-progress | done
- **Notes**: 
  - 備註...
```

### 2. 執行流程

**執行前**：
1. 確認依賴任務已完成
2. 檢查相關報告/文件
3. 準備執行環境

**執行中**：
1. 更新任務狀態為 `in-progress`
2. 按 Acceptance Criteria 逐一完成
3. 記錄問題與決策

**執行後**：
1. 更新任務狀態為 `done`
2. 產出執行報告到 `docs/reports/execution/`
3. 若有問題，產出 `docs/reports/incidents/`
4. 指派驗證任務給樂樂

### 3. 驗證流程

```
執行變更 → 自動產生驗證 task → 指派給樂樂 → 樂樂執行驗證 → 結果回傳 → 統一彙報
```

**驗證任務存放**：`/Users/claw/Tasks/_verification/`

**驗證報告產出**：`docs/reports/validation/`

### 4. 報告規範

所有報告統一存放於 `docs/reports/`，並同步至 GitHub：

| 報告類型 | 目錄 | 觸發時機 |
|----------|------|----------|
| 執行報告 | `execution/` | 任務完成後 |
| 驗證報告 | `validation/` | 驗證完成後 |
| 問題報告 | `incidents/` | 發現問題時 |
| 決策記錄 | `decisions/` | 重大決策時 |
| 分析報告 | `analysis/` | 架構/性能分析時 |

**報告命名**：`YYYY-MM-DD_{執行者}_{任務}.md`

### 5. 團隊角色

| 成員 | Agent ID | 職責 |
|------|----------|------|
| 寶寶 | main | Planner，統籌規劃、彙報結果 |
| 碼農1號 | agent-coder1 | Coder，後端開發 |
| 碼農2號 | agent-coder2 | Coder，ML/交易系統 |
| 安安 | agent-ann | DocWriter，前端/文檔 |
| 樂樂 | agent-lele | Reviewer，驗證/測試 |

### 6. 專案結構

```
/Users/claw/Tasks/
├── PROJECTS.md              # 專案總覽
├── _inbox/                  # 待分類任務
│   └── YYYY-MM-DD.md
├── _verification/           # 驗證任務
├── _done/                   # 已歸檔
│
└── {project-name}/
    ├── README.md            # 專案說明
    ├── tasks/
    │   ├── T001.md
    │   ├── T002.md
    │   └── ...
    └── reports/             # 專案專屬報告

/Users/claw/Projects/{project}/
├── docs/reports/            # 統一報告中心
│   ├── execution/
│   ├── validation/
│   ├── incidents/
│   ├── decisions/
│   └── analysis/
└── ...
```

### 7. Git 規範

**Commit Message 格式**：
```
{type}({scope}): {subject}

{type}: feat | fix | docs | refactor | test | chore
{scope}: backend | frontend | reports | tasks | etc.
```

**示例**：
- `feat(backend): 完成 T004-A 驗證模組`
- `docs(reports): 新增 T004 執行報告`
- `fix(frontend): 修復價格顯示錯誤`

### 8. 備註風險自動追蹤

**觸發條件**：任務標記 `status: done` 時，若備註含以下關鍵字：
- 「需處理」「待」「風險」「問題」「注意」「後續」

**處理方式**：
1. 自動建立對應子任務或技術負債卡
2. 掛在原任務下層，保留原始脈絡
3. 在日誌中記錄「備註風險已轉任務」

## 使用示例

### 建立新專案

```
用戶: "建立一個新專案叫 dashboard-tool"
AI: 建立 /Users/claw/Tasks/dashboard-tool/ 結構
    建立 README.md
    等待用戶提供需求
```

### 拆分任務

```
用戶: "dashboard-tool 需要資料視覺化功能"
AI: 拆分為 T001-T005:
    - T001: 資料獲取模組
    - T002: 圖表組件
    - T003: 儀表板頁面
    - T004: 即時更新
    - T005: 整合測試
    等待用戶確認後指派
```

### 執行任務

```
用戶: "確認執行 T001-T003"
AI: 指派 T001 給碼農1號
    指派 T002 給安安
    指派 T003 給安安
    三路並行執行
```

### 完成報告

```
AI: T001 完成
    產出 docs/reports/execution/2026-04-10_coder1_T001.md
    指派驗證任務給樂樂
    更新 PROJECTS.md
```

## 相關文件

- [專案總覽](../../../Tasks/PROJECTS.md)
- [報告中心](../../../Projects/gold-analysis/docs/reports/)
- [任務模板](../../../Tasks/TEMPLATE.md)

---
*Skill Version: 1.0.0*
*Last Updated: 2026-04-10*
