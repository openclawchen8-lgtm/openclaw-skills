#!/usr/bin/env python3
"""
task_audit.py — 任務一致性稽核工具

比對每個專案的 T*.md Status 與 README.md 中同一 task 的狀態是否一致。
T*.md 是 source of truth，README.md 是團隊可見的彙整，兩邊必須同步。

用法：
  python3 task_audit.py                        # 全域稽核
  python3 task_audit.py --project openclaw-scrum  # 指定專案稽核
  python3 task_audit.py --dry-run             # 不實際修改，只顯示結果
"""
import re
import sys
from pathlib import Path
from datetime import datetime

TASKS_DIR = Path("/Users/claw/Tasks")

# ── 本地讀取 ───────────────────────────────────────────

def read_task_meta(fp):
    """讀取 T*.md 的 Status 和標題。支援 YAML frontmatter 和 Markdown task 格式。"""
    content = fp.read_text(encoding="utf-8")

    # 1. 先檢查 YAML frontmatter（--- 之間的內容）
    fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    fm_status = None
    fm_title = None
    if fm_match:
        fm_text = fm_match.group(1)
        for line in fm_text.splitlines():
            lm = re.match(r"^\s*status\s*:\s*(.+)", line, re.I)
            if lm and fm_status is None:
                raw = lm.group(1).strip().lower()
                raw = re.sub(r"^[✅🔄❌⏳🔵🟢📋➕]\s*", "", raw)
                raw = raw.split("#")[0].strip().replace("_", "-")
                if raw in ("done", "完成", "✅"):
                    fm_status = "done"
                elif raw in ("in-progress", "in progress", "in_progress", "進行中"):
                    fm_status = "in-progress"
                elif raw in ("pending", "待處理", "待實作"):
                    fm_status = "pending"
                elif raw in ("skip", "skipped", "❌"):
                    fm_status = "skip"
                else:
                    fm_status = raw
            tm = re.match(r"^\s*title\s*:\s*(.+)", line, re.I)
            if tm and fm_title is None:
                fm_title = tm.group(1).strip().strip('"\'')
            tm2 = re.match(r"^\s*id\s*:\s*(.+)", line, re.I)
            if tm2 and fm_title is None:
                # fallback：用 id 當標題
                fm_title = tm2.group(1).strip()

    # 2. 再找 Markdown body 裡的 - **Status**: 格式
    body_status = None
    body_title = None
    body = fm_match.group(0) if fm_match else content  # 跳過 frontmatter

    in_fm = False
    for line in content.splitlines():
        if line.strip() == "---":
            in_fm = not in_fm
            continue
        if in_fm:
            continue  # 跳過 frontmatter
        sm = re.match(
            r"^(-?\s*-?\s*\*+\s*[Ss]tatus\s*\*+\s*:\s*)(.+)",
            line.strip(),
            re.I,
        )
        if sm:
            raw = sm.group(2).lower().strip().split("#")[0].strip().replace("_", "-")
            raw = re.sub(r"^[✅🔄❌⏳🔵🟢📋➕]\s*", "", raw)
            if raw in ("done", "完成"):
                body_status = "done"
            elif raw in ("in-progress", "in progress", "進行中"):
                body_status = "in-progress"
            elif raw in ("pending", "待處理", "待實作", "skip", "skipped"):
                body_status = "pending"
            else:
                body_status = raw
        if body_title is None:
            tm = re.match(r"^#+\s*[-*]?\s*\*?T\d+[-+]?\d*\s*[\|：:]\s*(.+)", line.strip())
            if tm:
                body_title = tm.group(1).strip().rstrip("|：:")

    # frontmatter 優先，body 作為 fallback
    return {
        "status": fm_status or body_status or "pending",
        "title": fm_title or body_title,
    }


def read_readme_tasks(readme_path):
    """解析 README.md，回傳 {task_id: {"status": ..., "line": ...}}。
    表格格式：| T001 | 標題 | 負責人 | Status |
    用 pipe 數量定位欄位，不靠 regex 猜測。"""
    tasks = {}
    if not readme_path.exists():
        return tasks

    for line in readme_path.read_text(encoding="utf-8").splitlines():
        # 跳过表头和分隔行
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|--") or "---" in stripped:
            continue
        if "T001" in stripped and "標題" in stripped:
            continue  # 表头行

        cols = [c.strip() for c in stripped.split("|")]
        cols = [c for c in cols if c]  # 移除空字串

        if len(cols) < 2:
            continue

        # 第一欄是 task id，格式：T001 / T001-1 等
        tid_match = re.match(r"^T(\d+)(-[A-Za-z0-9]+)?\s*", cols[0], re.I)
        if not tid_match:
            continue
        # 跳過假的 task ID（更新規範表格行，如 T`in-progress`）
        if "→" in cols[0] or "`" in cols[0]:
            continue
        tid_num = tid_match.group(1)
        tid_suffix = tid_match.group(2) or ""
        # 前導零正規化 + 子任務後綴
        tid = str(int(tid_num)) + tid_suffix

        # 最後一欄是 Status（通用規則）
        last_col = cols[-1].lower().strip()
        last_col = re.sub(r"[\U0001F300-\U0001F9FF\u200d✅🔄❌⏳⬜⏭️]+\s*", "", last_col)
        last_col = re.sub(r"[\U0001F300-\U0001F9FF\u200d✅🔄❌⏳⬜⏭️]+$", "", last_col).strip()

        if last_col in ("done", "完成", "closed", "✅"):
            status = "done"
        elif last_col in ("in-progress", "in progress", "進行中", "in review", "review", "🔄"):
            status = "in-progress"
        elif last_col in ("pending", "待處理", "待實作", "todo", "open", "⬜", "🔵"):
            status = "pending"
        elif last_col in ("skip", "skipped"):
            status = "skip"
        else:
            status = last_col  # 未知狀態保留原文

        tasks[tid] = {"status": status, "line": stripped[:100]}

    return tasks


# ── 比對邏輯 ───────────────────────────────────────────

def audit_project(project_dir):
    """稽核單一專案，回傳 (consistent, inconsistent, warnings)。"""
    consistent = []
    inconsistent = []
    warnings = []

    tasks_dir = project_dir / "tasks"
    readme_path = project_dir / "README.md"

    if not tasks_dir.exists():
        return [], [], [f"  tasks/ 目錄不存在"]

    readme_tasks = read_readme_tasks(readme_path) if readme_path.exists() else {}

    # 掃描所有 T*.md
    for tf in sorted(tasks_dir.glob("T*.md")):
        # 統一正規化：T001.md → "1"，T008-1.md → "8-1"
        raw_tid = tf.stem  # "T001"
        m = re.match(r"^T0*(\d+)(-[A-Za-z0-9]+)?$", raw_tid, re.I)
        tid = m.group(1) if m else raw_tid
        if m and m.group(2):
            tid += m.group(2)  # "3-A"（子任務後綴）
        md_meta = read_task_meta(tf)
        md_status = md_meta["status"]
        md_title = md_meta["title"]
        readme_meta = readme_tasks.get(tid)
        if readme_meta is None:
            # README 裡沒有這條任務
            warnings.append(
                f"  [{tid}] T*.md 有，但 README.md 無  |  md={md_status}"
                + (f" 「{md_title}」" if md_title else "")
            )
            continue

        readme_status = readme_meta["status"]

        if md_status == readme_status:
            consistent.append(f"  ✅ [{tid}] {md_status}")
        else:
            inconsistent.append(
                f"  ❌ [{tid}] 不一致  |  T*.md={md_status}  README={readme_status}"
                + (f"  「{md_title}」" if md_title else "")
            )
            inconsistent.append(f"       README: {readme_meta['line']}")

    return consistent, inconsistent, warnings


# ── 主程式 ─────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="任務一致性稽核")
    parser.add_argument("--project", help="只稽核指定專案")
    parser.add_argument("--dry-run", action="store_true", help="只顯示，不寫入")
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"📋 Task Audit Report — {now}"]

    # 找出要稽核的專案
    if args.project:
        project_dirs = [TASKS_DIR / args.project]
        if not project_dirs[0].exists():
            print(f"❌ 專案不存在: {project_dirs[0]}")
            sys.exit(1)
    else:
        project_dirs = sorted(
            d for d in TASKS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )

    total_consistent = 0
    total_inconsistent = 0
    total_warnings = 0

    for project_dir in project_dirs:
        project_name = project_dir.name
        consistent, inconsistent, warnings = audit_project(project_dir)

        if not consistent and not inconsistent and not warnings:
            continue  # 跳過空專案

        lines.append(f"\n{'='*50}")
        lines.append(f"📁 {project_name}")

        for w in warnings:
            lines.append(w)
            total_warnings += 1

        for c in consistent:
            lines.append(c)
            total_consistent += 1

        for i in inconsistent:
            lines.append(i)
            total_inconsistent += 1

        if not inconsistent:
            lines.append(f"  ✅ 全部一致 ({len(consistent)} 項)")
        else:
            lines.append(f"  ❌ {len(inconsistent)//2} 項不一致，請確認")

    # 摘要
    lines.append(f"\n{'='*50}")
    lines.append(
        f"📊 總計  ✅ 一致: {total_consistent}  |  "
        f"❌ 不一致: {total_inconsistent}  |  ⚠️ 警告: {total_warnings}"
    )

    report = "\n".join(lines)
    print(report)

    if total_inconsistent > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()