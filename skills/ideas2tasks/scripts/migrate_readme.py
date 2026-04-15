#!/usr/bin/env python3
"""
為所有專案建立/更新 README.md，任務狀態以 T*.md 為準。
"""
import re
from pathlib import Path
from datetime import datetime

TASKS_ROOT = Path("/Users/claw/Tasks")
SKIP_DIRS = {".git", "_inbox", "_verification"}

STATUS_MAP = {
    "done": "done", "完成": "done",
    "in-progress": "in-progress", "in progress": "in-progress", "進行中": "in-progress",
    "pending": "pending", "待處理": "pending", "open": "pending",
    "skip": "skip", "skipped": "skip",
}
EMOJI_MAP = {"done": "✅", "in-progress": "🔄", "pending": "⬜", "skip": "⏭️"}

def normalize_status(raw):
    raw = raw.lower().strip()
    for key, norm in STATUS_MAP.items():
        if key in raw:
            return norm
    return "pending"

def get_emoji(s): return EMOJI_MAP.get(s, "⬜")

def parse_frontmatter(content):
    fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    status, title = "pending", None
    if fm_match:
        for line in fm_match.group(1).splitlines():
            lm = re.match(r"^\s*status\s*:\s*(.+)", line, re.I)
            if lm:
                raw = lm.group(1).strip().lower().split("#")[0].strip().replace("_", "-").replace("_", "-")
                status = normalize_status(raw)
            tm = re.match(r'^\s*title\s*:\s*(.+)', line, re.I)
            if tm:
                title = tm.group(1).strip().strip('"\'')
    if not title:
        tm = re.match(r"^#+\s*[-*]?\s*\*?T\d+[-+]?\d*\s*[\|：:]\s*(.+)", content)
        if tm:
            title = tm.group(1).strip().rstrip("|：:")
    # 2. body 內的 - **Status**: xxx（比 frontmatter 優先）
    body_status = None
    for line in content.splitlines():
        sm = re.match(r"^(-?\s*-?\s*\*+\s*[Ss]tatus\s*\*+\s*:\s*)(.+)", line.strip())
        if sm:
            raw = sm.group(2).lower().strip().split("#")[0].strip().replace("_", "-")
            if raw in ("done", "完成"): body_status = "done"
            elif raw in ("in-progress", "in progress", "in_progress"): body_status = "in-progress"
            elif raw in ("pending", "待處理", "待實作"): body_status = "pending"
            elif raw in ("skip", "skipped"): body_status = "skip"
            else: body_status = raw
    # frontmatter 無值時用 body
    if status == "pending" and body_status:
        status = body_status
    return status, title

def parse_body_status(content):
    for line in content.splitlines():
        sm = re.match(r"^(-?\s*-?\s*\*+\s*Status\s*\*+\s*:\s*)(.+)", line.strip())
        if sm:
            raw = sm.group(2).lower().strip().split("#")[0].strip().replace("_", "-")
            raw = re.sub(r"^[✅🔄❌⏳⬜🔵🟢📋➕]\s*", "", raw)
            return normalize_status(raw)
    return "pending"

def parse_task_num(name):
    m = re.match(r"^T(\d+)(-[A-Za-z0-9]+)?\.md$", name)
    if not m: return None
    # 前導零正規化：003 → 3，003-A → 3-A
    return str(int(m.group(1))) + (m.group(2) or "")

def parse_readme_task_col(task_col):
    """T001 → 1，001 → 1，T003-A → 3-A，T008-1 → 8-1"""
    m = re.match(r"^T0*(\d+)(-[A-Za-z0-9]+)?", task_col.strip(), re.I)
    if not m: return None
    return m.group(1) + (m.group(2) or "")

def get_task_meta(path):
    content = path.read_text(encoding="utf-8")
    fm_status, fm_title = parse_frontmatter(content)
    body_status = parse_body_status(content)
    status = fm_status if fm_status != "pending" else body_status
    if status == "pending" and body_status != "pending":
        status = body_status
    title = fm_title or f"任務 {path.stem}"
    num = parse_task_num(path.name)
    return {"num": num, "status": status, "title": title, "path": path}

def is_valid_task_col(col1):
    """排除中文標題、箭頭描述等非任務列"""
    col = col1.strip()
    if not col: return False
    # 包含中文（標題行、更新規範行）→ 跳過
    if re.search(r"[\u4e00-\u9fff]", col): return False
    # 包含 ` → 或 Markdown 語法 → 跳過
    if "→" in col or "`" in col: return False
    # 不是數字開頭 → 跳過
    if not re.match(r"^\d", col): return False
    return True

def parse_readme_tasks(readme_path):
    tasks = {}
    if not readme_path.exists():
        return tasks
    for line in readme_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"): continue
        if "|--" in stripped or stripped.startswith("| Task"): continue
        cols = [c.strip() for c in stripped.split("|")]
        if len(cols) < 5: continue
        task_col = cols[1].strip()
        if not is_valid_task_col(task_col): continue
        num = parse_readme_task_col(task_col)
        if not num: continue
        title = cols[2].strip() if len(cols) > 2 else "未知"
        assignee = cols[3].strip() if len(cols) > 3 else "未指派"
        status_col = cols[4].strip()
        status = normalize_status(status_col)
        tasks[num] = {"num": num, "status": status, "title": title,
                      "assignee": assignee, "from_readme": True}
    return tasks

def build_readme(project_name, tasks):
    def sort_key(t):
        n = t["num"]
        m = re.match(r"(\d+)(.*)", n)
        return (int(m.group(1)) if m else 0, m.group(2) if m else "")
    sorted_tasks = sorted(tasks.values(), key=sort_key)
    rows = []
    for t in sorted_tasks:
        emoji = get_emoji(t["status"])
        status_text = f"{emoji} {t['status']}"
        assignee = t.get("assignee", "未指派")
        title = t.get("title", f"任務 {t['num']}")
        task_id = f"T{t['num']}"
        rows.append(f"| {task_id} | {title} | {assignee} | 中 | {status_text} |")
    rows_text = "\n".join(rows) if rows else "| | | | | |"
    return f"""# {project_name}

## 任務狀態

| Task | 標題 | 負責人 | 優先順序 | 狀態 |
|------|------|--------|---------|------|
{rows_text}

## 更新規範

每次狀態變更時，**同時更新** T\*.md 與本檔案：

**pending → in-progress**：T\*.md 改 `status: in-progress`，README 改 `⬜ pending` → `🔄 in-progress`

**in-progress → done**：T\*.md 改 `status: done`，README 改 `🔄 in-progress` → `✅ done`

- 更新 T\*.md 時一併更新 `updated` 欄位
- 完成後同步 GitHub Issue 狀態（`--sync-state`）
"""

def ensure_task_file(task_dir, task_info):
    num = task_info["num"]
    title = task_info["title"]
    status = task_info["status"]
    assignee = task_info.get("assignee", "未指派")
    today = datetime.now().strftime("%Y-%m-%d")
    path = task_dir / f"T{num}.md"
    content = f"""---
title: {title}
status: {status}
assignee: {assignee}
created: {today}
updated: {today}
---

# T{num} - {title}

## 目標
（描述這個任務要達成什麼）

## 驗收標準
- [ ] 標準1
- [ ] 標準2

## 備註
（風險、待處理事項注意點）
"""
    path.write_text(content, encoding="utf-8")
    return path

def main():
    results = {"created_readme": [], "updated_readme": [], "created_task": [],
               "skipped": [], "errors": []}
    for proj_dir in sorted(TASKS_ROOT.iterdir()):
        if not proj_dir.is_dir() or proj_dir.name in SKIP_DIRS:
            continue
        proj_name = proj_dir.name
        tasks_dir = proj_dir / "tasks"
        readme_path = proj_dir / "README.md"
        task_files = list(tasks_dir.glob("T*.md")) if tasks_dir.exists() else []
        tasks = {}
        for tf in task_files:
            try:
                meta = get_task_meta(tf)
                if meta["num"]:
                    tasks[meta["num"]] = meta
            except Exception as e:
                results["errors"].append(f"{proj_name}/{tf.name}: {e}")
        if readme_path.exists():
            readme_tasks = parse_readme_tasks(readme_path)
            for num, info in readme_tasks.items():
                if num not in tasks:
                    tasks[num] = info
        tasks_dir.mkdir(exist_ok=True)
        for num, info in tasks.items():
            if info.get("from_readme"):
                try:
                    ensure_task_file(tasks_dir, info)
                    results["created_task"].append(f"{proj_name}/T{num}.md")
                except Exception as e:
                    results["errors"].append(f"{proj_name}/T{num}.md: {e}")
        if not tasks:
            results["skipped"].append(f"{proj_name}（無任務）")
            continue
        new_readme = build_readme(proj_name, tasks)
        new_readme += f"\n> 自動生成於 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        if not readme_path.exists():
            readme_path.write_text(new_readme, encoding="utf-8")
            results["created_readme"].append(proj_name)
        else:
            readme_path.write_text(new_readme, encoding="utf-8")
            results["updated_readme"].append(proj_name)
    print(f"✅ 新建 README：{len(results['created_readme'])} 個")
    for p in results["created_readme"]: print(f"   - {p}")
    print(f"\n🔄 更新 README：{len(results['updated_readme'])} 個")
    for p in results["updated_readme"]: print(f"   - {p}")
    print(f"\n📄 新建 T*.md（還原）：{len(results['created_task'])} 個")
    for t in results["created_task"]: print(f"   - {t}")
    if results["errors"]:
        print(f"\n❌ 錯誤：{len(results['errors'])} 個")
        for e in results["errors"]: print(f"   - {e}")
    else:
        print(f"\n✨ 無錯誤")

if __name__ == "__main__":
    main()