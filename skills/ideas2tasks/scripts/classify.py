#!/usr/bin/env python3
"""
ideas2tasks classify.py
根據 idea 內容分類、拆分 tasks、分配團隊成員。
輸出可送入 task 模板的結構化資料。

支援格式：
  1. task.N / task.N done 格式（原有）
  2. 任務 X.X：格式（專案計畫書常見）
  3. Task X.X: 格式（英文計畫書）
  4. - [ ] 待辦清單格式
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
ROLE_RESEARCH = "研研"

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
    "analysis":   ["分析", "決策", "agent", "投資", "策略"],
    "research":   ["研究", "調研", "評估", "比較", "review", "recommend"],
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
    "analysis":   [ROLE_CODER[0], ROLE_DOC, ROLE_RESEARCH],
    "research":   [ROLE_RESEARCH],
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


def parse_task_dot_n_format(content: str) -> tuple[list[dict], list[dict]]:
    """
    解析 task.N 格式。

    規則：
    - 行首 "task.N done" / "task.N_done" → 該 task 已完成
    - 行首 "task.N" 無 done → 待執行
    - task.N 後的內容只取到下一個 task.N、連續空行（≥2）或段落分隔符（---）為止
    - 段落分隔符出現後，該 task 立即 flush；分隔符後所有內容全部忽略
      （包含對話歷史，直到下一個 task.N 出現）

    修正紀錄（2026-04-15）：
    1. 段落分隔符（---）出現時立即 flush task，並忽略之後所有內容直到下一個 task.N
    2. 只 1 行空白不足以作為邊界；≥2 行空白才關閉 body 收集
       （task.2 後只有 1 行空白，對話被誤吃）
    3. 當前無 task 時，段落分隔符應忽略
    """
    lines = content.splitlines()
    done_tasks = []
    pending_tasks = []

    task_pattern = re.compile(r'^task\.(\d+)\s*(done)?[\s_]*(.*)', re.IGNORECASE)
    # 偵測段落分隔符（----, ===, *** 等）
    separator_pattern = re.compile(r'^[-=_*]{3,}\s*$')
    current_task = None
    current_body_lines = []
    consecutive_blank = 0   # 連續空行計數
    body_closed = False      # 該 task 的 body 是否已關閉
    past_separator = False   # 是否已越過段落分隔符（之後全部忽略）

    def flush_task():
        nonlocal current_task, current_body_lines, body_closed, consecutive_blank
        if current_task:
            body = "\n".join(current_body_lines).strip()
        # 組 title（只取 task.N 部分，去掉重複前綴）
            raw = current_task["raw_title"]
            title = re.sub(r'^task\.', '', raw)
            entry = {"title": f"task.{title}", "body": body, "line": current_task["line"]}
            if current_task["done"]:
                done_tasks.append(entry)
            else:
                pending_tasks.append(entry)
        current_task = None
        current_body_lines = []
        body_closed = False
        consecutive_blank = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = task_pattern.match(stripped)

        if m:
            # 遇到新的 task.N → 先 flush 舊的，並重置忽略狀態
            flush_task()
            past_separator = False
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
            continue

        # 越過段落分隔符後，所有內容全部忽略
        if past_separator:
            continue

        if current_task is not None and not body_closed:
            # 偵測段落分隔符 → 立即 flush task + 忽略後續內容
            if separator_pattern.match(stripped):
                flush_task()
                past_separator = True
                continue

            if stripped == "":
                consecutive_blank += 1
                if consecutive_blank >= 2:
                    # 連續 2 行空白 → 關閉 body 收集
                    body_closed = True
                continue
            else:
                consecutive_blank = 0
                current_body_lines.append(stripped)
        elif current_task is None:
            # 無 current_task 時，段落分隔符也設為忽略（避免干擾）
            if separator_pattern.match(stripped):
                past_separator = True
        # else: 有 task 但 body 已關閉，忽略

    # flush 最後一個 task
    flush_task()

    return done_tasks, pending_tasks


def parse_chinese_task_format(content: str) -> tuple[list[dict], list[dict]]:
    """
    解析「任務 X.X：」格式（中文專案計畫書常見）。

    支援格式：
    - 任務 1.1：搭建開發環境
    - 任務1.1: 搭建開發環境
    - 任务 1.1：搭建开发环境（简体）
    """
    done_tasks = []
    pending_tasks = []

    # 匹配「任務 X.X：」或「任務 X.X:」格式
    task_pattern = re.compile(
        r'^任\s*[务務]\s*(\d+(?:\.\d+)?)\s*[：:]\s*(.+)$',
        re.IGNORECASE
    )

    lines = content.splitlines()
    current_task = None
    current_body_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = task_pattern.match(stripped)

        if m:
            # 先保存上一個 task
            if current_task:
                body = "\n".join(current_body_lines).strip()
                entry = {
                    "title": current_task["title"],
                    "body": body,
                    "line": current_task["line"],
                    "num": current_task["num"],
                }
                if current_task["done"]:
                    done_tasks.append(entry)
                else:
                    pending_tasks.append(entry)

            # 開始新 task
            task_num = m.group(1)
            task_title = m.group(2).strip()

            # 檢查是否標記為 done
            is_done = bool(re.search(r'\bdone\b|\b完成\b|\b已完成\b', task_title, re.IGNORECASE))

            current_task = {
                "num": task_num,
                "title": f"任務 {task_num}：{task_title}",
                "line": i + 1,
                "done": is_done,
            }
            current_body_lines = []
        elif current_task is not None:
            # 收集 task 的描述內容（直到下一個 task 或空行區隔）
            if stripped and not stripped.startswith('任'):
                # 只收集有意義的內容，跳過過長的描述
                if len(current_body_lines) < 3:  # 限制每個 task 的描述行數
                    current_body_lines.append(stripped)

    # 最後一個 task
    if current_task:
        body = "\n".join(current_body_lines).strip()
        entry = {
            "title": current_task["title"],
            "body": body,
            "line": current_task["line"],
            "num": current_task["num"],
        }
        if current_task["done"]:
            done_tasks.append(entry)
        else:
            pending_tasks.append(entry)

    return done_tasks, pending_tasks


def parse_english_task_format(content: str) -> tuple[list[dict], list[dict]]:
    """
    解析「Task X.X:」格式（英文專案計畫書）。

    支援格式：
    - Task 1.1: Setup development environment
    - Task 1.1：Setup development environment
    """
    done_tasks = []
    pending_tasks = []

    task_pattern = re.compile(
        r'^Task\s*(\d+(?:\.\d+)?)\s*[：:]\s*(.+)$',
        re.IGNORECASE
    )

    lines = content.splitlines()
    current_task = None
    current_body_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = task_pattern.match(stripped)

        if m:
            if current_task:
                body = "\n".join(current_body_lines).strip()
                entry = {
                    "title": current_task["title"],
                    "body": body,
                    "line": current_task["line"],
                    "num": current_task["num"],
                }
                if current_task["done"]:
                    done_tasks.append(entry)
                else:
                    pending_tasks.append(entry)

            task_num = m.group(1)
            task_title = m.group(2).strip()
            is_done = bool(re.search(r'\bdone\b|\bcompleted?\b', task_title, re.IGNORECASE))

            current_task = {
                "num": task_num,
                "title": f"Task {task_num}: {task_title}",
                "line": i + 1,
                "done": is_done,
            }
            current_body_lines = []
        elif current_task is not None:
            if stripped and not re.match(r'^Task\s*\d', stripped, re.IGNORECASE):
                if len(current_body_lines) < 3:
                    current_body_lines.append(stripped)

    if current_task:
        body = "\n".join(current_body_lines).strip()
        entry = {
            "title": current_task["title"],
            "body": body,
            "line": current_task["line"],
            "num": current_task["num"],
        }
        if current_task["done"]:
            done_tasks.append(entry)
        else:
            pending_tasks.append(entry)

    return done_tasks, pending_tasks


def parse_checkbox_format(content: str) -> tuple[list[dict], list[dict]]:
    """
    解析 Markdown 待辦清單格式。

    支援格式：
    - [ ] 待辦事項
    - [x] 已完成事項
    """
    done_tasks = []
    pending_tasks = []

    lines = content.splitlines()
    task_counter = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 匹配 [x] 已完成
        m_done = re.match(r'^-\s*\[[xX]\]\s*(.+)$', stripped)
        if m_done:
            task_counter += 1
            done_tasks.append({
                "title": m_done.group(1).strip(),
                "body": "",
                "line": i + 1,
                "num": str(task_counter),
            })
            continue

        # 匹配 [ ] 待辦
        m_pending = re.match(r'^-\s*\[\s*\]\s*(.+)$', stripped)
        if m_pending:
            task_counter += 1
            pending_tasks.append({
                "title": m_pending.group(1).strip(),
                "body": "",
                "line": i + 1,
                "num": str(task_counter),
            })

    return done_tasks, pending_tasks


def parse_all_formats(content: str) -> tuple[list[dict], list[dict]]:
    """
    嘗試所有格式解析器，返回結果最多的一個。
    返回：(all_tasks, done_tasks) — pending 任務在前，已完成在後。
    
    各格式解析器內部變量命名已統一：
      done_tasks = 已完成（task.N done 標記）
      pending_tasks = 待執行
    因此各格式返回 (pending_tasks, done_tasks)。
    """
    results = [
        ("task.N", parse_task_dot_n_format(content)),
        ("任務 X.X", parse_chinese_task_format(content)),
        ("Task X.X", parse_english_task_format(content)),
        ("checkbox", parse_checkbox_format(content)),
    ]

    best_format = None
    best_count = 0
    best_pending = []
    best_done = []

    for fmt, result in results:
        # 每個 parser 返回 (done_tasks, pending_tasks)
        done, pending = result
        total = len(done) + len(pending)
        if total > best_count:
            best_count = total
            best_pending = pending
            best_done = done
            best_format = fmt

    if best_count == 0:
        return [], []

    # 返回 (pending_tasks, done_tasks) 與內部變量一致
    return best_pending, best_done


def parse_done_markers(content: str) -> tuple[list[dict], list[dict]]:
    """
    分析 idea 內容，回傳:
    - done_tasks: 已完成的 task 列表（含標題、行號）
    - pending_tasks: 待執行的 task 列表（含標題、行號、內容）

    自動偵測並使用最佳格式解析器。
    """
    return parse_all_formats(content)


def build_tasks(pending: list[dict], category: str, max_tasks: int = 10) -> list[dict]:
    """將 pending task 區塊轉為標準 task 結構。"""
    pool = TYPE_ASSIGNEE.get(category, ROLE_CODER)
    results = []

    for idx, item in enumerate(pending[:max_tasks]):
        title = item["body"].split("\n")[0].strip()[:80] if item["body"] else item["title"]
        if not title:
            title = f"待處理任務 {item['line']}"

        # 推斷優先級
        priority = "medium"
        for kw in ["新增", "建立", "修復", "bug", "優先", "urgent", "critical"]:
            if kw in title:
                priority = "high"
                break
        for kw in ["文件", "comment", "整理", "美化", "文檔", "docs"]:
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
