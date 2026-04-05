#!/usr/bin/env python3
"""
ideas2tasks classify.py
根據 idea 內容分類、拆分 tasks、分配團隊成員。
輸出可送入 task 模板的結構化資料。
"""

import json
import re
import sys
from pathlib import Path


# ── 團隊角色定義 ──────────────────────────────────────────────
ROLE_CODER    = ["碼農 1 號", "碼農 2 號"]
ROLE_DOC      = "安安"
ROLE_REVIEWER = "樂樂"
ROLE_PLANNER  = "豪（用戶）"

# ── 關鍵字分類矩陣 ────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "skill":      ["skill", "plugin", "功能", "自動化"],
    "backup":     ["backup", "備份", "還原", "sync", "同步"],
    "security":   ["security", "安全", "防火牆", "权限", "auth"],
    "monitoring": ["monitor", "監控", "通知", "alert", "追蹤"],
    "infra":      ["deploy", "server", "vps", "docker", "config"],
    "docs":       ["doc", "howto", "readme", "文檔", "說明"],
    "dev":        ["code", "python", "script", "api", "腳本"],
    "test":       ["test", "測試", "驗證", "qa"],
}

# ── Task 類型 → 負責人映射 ────────────────────────────────────
TYPE_ASSIGNEE = {
    "skill":      [ROLE_CODER[0], ROLE_DOC],
    "backup":     [ROLE_CODER[1]],
    "security":   [ROLE_CODER[0], ROLE_REVIEWER],
    "monitoring": [ROLE_CODER[1]],
    "infra":      [ROLE_CODER[0]],
    "docs":       [ROLE_DOC],
    "dev":        [ROLE_CODER[0], ROLE_CODER[1]],
    "test":       [ROLE_REVIEWER],
}


def detect_category(text: str) -> str:
    """根據關鍵字偵測 category，回傳最可能的主類別。"""
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score:
            scores[cat] = score
    if not scores:
        return "dev"
    return max(scores, key=scores.get)


def parse_done_markers(content: str) -> tuple[list[dict], list[dict]]:
    """
    分析 idea 內容，回傳:
    - done_tasks: 已完成的 task 列表（含標題、行號）
    - pending_tasks: 待執行的 task 列表（含標題、行號、內容）
    
    規則：
    - 行首 "task.N done" / "task.N_done" → 該 task 已完成
    - 行首 "task.N" 無 done → 待執行
    - 行首無 task.N 的自由內容 → 依附到最近一個 task
    """
    lines = content.splitlines()
    done_tasks = []
    pending_tasks = []

    task_pattern = re.compile(r'^task\.(\d+)\s*(done)?[\s_]*(.*)', re.IGNORECASE)
    current_task = None
    current_body_lines = []

    for i, line in enumerate(lines):
        m = task_pattern.match(line.strip())
        if m:
            # 先把上一個 task 的內容收起來
            if current_task:
                body = "\n".join(current_body_lines).strip()
                entry = {"title": current_task["raw_title"], "body": body, "line": current_task["line"]}
                if current_task["done"]:
                    done_tasks.append(entry)
                else:
                    pending_tasks.append(entry)
            current_body_lines = []
            task_num, is_done, rest = m.group(1), m.group(2), m.group(3)
            raw_title = f"task.{task_num}" + (" done" if is_done else "")
            current_task = {
                "num": int(task_num),
                "done": bool(is_done),
                "raw_title": raw_title,
                "line": i + 1,
                "rest": rest.strip(),
            }
            if rest:
                current_body_lines.append(rest)
        elif current_task is not None:
            # 自由行內容，附加到當前 task
            stripped = line.strip()
            if stripped:
                current_body_lines.append(line)

    # 最後一個 task
    if current_task:
        body = "\n".join(current_body_lines).strip()
        entry = {"title": current_task["raw_title"], "body": body, "line": current_task["line"]}
        if current_task["done"]:
            done_tasks.append(entry)
        else:
            pending_tasks.append(entry)

    return done_tasks, pending_tasks


def build_tasks(pending: list[dict], category: str, max_tasks: int = 10) -> list[dict]:
    """將 pending task 區塊轉為標準 task 結構。"""
    # 推斷分配池
    pool = TYPE_ASSIGNEE.get(category, ROLE_CODER)
    results = []

    for idx, item in enumerate(pending[:max_tasks]):
        title = item["body"].split("\n")[0].strip()[:80] if item["body"] else item["title"]
        if not title:
            title = f"待處理任務 {item['line']}"

        # 推斷優先級
        priority = "medium"
        for kw in ["新增", "建立", "修復", "bug", "優先"]:
            if kw in title:
                priority = "high"
                break
        for kw in ["文件", "comment", "整理", "美化", "整理"]:
            if kw in title:
                priority = "low"

        assignee = pool[idx % len(pool)]
        results.append({
            "title": title,
            "description": item["body"],
            "assignee": assignee,
            "priority": priority,
            "category": category,
            "source_line": item["line"],
        })

    return results


def classify_idea(idea: dict) -> dict:
    """對單一 idea 進行完整分類分析。"""
    content = idea["content"]
    filename = idea["filename"]

    done_tasks, pending_tasks = parse_done_markers(content)
    category = detect_category(content)
    tasks = build_tasks(pending_tasks, category)

    all_assignees = [ROLE_PLANNER] + [t["assignee"] for t in tasks]
    unique_assignees = list(dict.fromkeys(all_assignees))

    return {
        "filename": filename,
        "project_name": Path(filename).stem.replace("_", "-"),
        "category": category,
        "done_count": len(done_tasks),
        "pending_count": len(pending_tasks),
        "total_actionable_tasks": len(tasks),
        "tasks": tasks,
        "assignees": unique_assignees,
        "needs_confirmation": len(tasks) > 10,
        "skipped_done": [d["title"] for d in done_tasks],
    }


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            ideas = json.load(f).get("ideas", [])
    else:
        ideas = json.load(sys.stdin).get("ideas", [])

    results = [classify_idea(idea) for idea in ideas]

    print(json.dumps({
        "total_ideas": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
