#!/usr/bin/env python3
"""
ideas2tasks executor.py
讀取 lifecycle_status.json → 建立 tasks → spawn agents → 彙報結果

用法：
  python3 executor.py                    # 完整執行
  python3 executor.py --no-spawn         # 只建立 tasks，不 spawn agents
  python3 executor.py --dry-run          # 乾跑模式（不實際建立）
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 共用狀態同步模組
sys.path.insert(0, str(Path(__file__).parent))
from state_sync import (
    TASKS_DIR, IDEAS_DIR,
    get_tasks_dir_status, read_task_status, write_task_status,
    should_skip_task,
)

# ===== 配置 =====
STATUS_FILE = Path(__file__).parent / "lifecycle_status.json"

# Assignee → AgentId 映射
ASSIGNEE_MAP = {
    "寶寶": "main",
    "豪": "main",
    "豪（用戶）": "main",
    "碼農1號": "agent-f937014d",
    "碼農 1 號": "agent-f937014d",
    "碼農2號": "agent-coder2",
    "碼農 2 號": "agent-coder2",
    "安安": "agent-ann",
    "樂樂": "agent-lele",
    "研研": "agent-researcher",
}

# ===== 函數 =====

def load_status() -> dict:
    """讀取 lifecycle_status.json"""
    if not STATUS_FILE.exists():
        print("❌ lifecycle_status.json 不存在，請先執行 lifecycle.py")
        sys.exit(1)
    return json.loads(STATUS_FILE.read_text(encoding="utf-8"))


def get_next_task_num(project_dir: Path) -> int:
    """取得專案下一個 task 編號"""
    tasks_dir = project_dir / "tasks"
    if not tasks_dir.exists():
        return 1
    existing = list(tasks_dir.glob("T*.md"))
    nums = [int(f.stem[1:]) for f in existing if f.stem[1:].isdigit()]
    return max(nums) + 1 if nums else 1


def create_task_file(task_dir: Path, task_num: int, task: dict) -> Path:
    """建立 task 檔案"""
    task_file = task_dir / f"T{task_num:03d}.md"
    content = f"""# T{task_num:03d} - {task['title'][:50]}

## 基本資訊
- **Type**: {task.get('category', 'general')}
- **Assignee**: {task['assignee']}
- **Priority**: {task.get('priority', 'Medium')}
- **Status**: pending

## 描述
{task.get('description', task['title'])}

## 產出
- [待填寫]

---

_建立日期: {datetime.now().strftime('%Y-%m-%d')}_
"""
    task_file.write_text(content, encoding="utf-8")
    return task_file


def update_project_readme(project_dir: Path, project_name: str, tasks: list):
    """更新專案 README"""
    readme_file = project_dir / "README.md"

    # 建立 tasks 表格（讀取實際狀態）
    tasks_status = get_tasks_dir_status(project_name)
    table_lines = ["| Task | 標題 | 負責人 | 優先級 | 狀態 |", "|------|------|--------|--------|------|"]

    for t in tasks:
        t_num = f"T{t['num']:03d}"
        status = tasks_status.get(t_num, t.get("status", "pending"))
        status_icon = "✅" if status == "done" else ("🔄" if status == "in-progress" else "⏳")
        table_lines.append(
            f"| {t_num} | {t['title'][:28]} | {t['assignee']} | {t['priority']} | {status_icon} |"
        )

    total = len(tasks)
    done = sum(1 for t in tasks if tasks_status.get(f"T{t['num']:03d}", "") == "done")

    content = f"""# {project_name} 專案

## 概述
由 ideas2tasks 自動建立的任務。

## Tasks 清單

{chr(10).join(table_lines)}

## 進度
- **完成**: {done}/{total}
- **進行中**: 0
- **待處理**: {total - done}

---

_建立日期: {datetime.now().strftime('%Y-%m-%d')}_
"""
    readme_file.write_text(content, encoding="utf-8")


def create_tasks_from_status(status: dict, dry_run: bool = False) -> list:
    """從 status 建立 tasks（已整合去重）"""
    created = []

    for result in status.get("results", []):
        # 跳過：無待處理 tasks（已由 merge 處理過）
        if result.get("pending_count", 0) == 0:
            continue

        project_name = result["project_name"]
        project_dir = TASKS_DIR / project_name

        if not dry_run:
            project_dir.mkdir(exist_ok=True)
            (project_dir / "tasks").mkdir(exist_ok=True)

        tasks_info = []
        task_num = get_next_task_num(project_dir)
        extra_norm_set = set()  # 同一批次的正規化標題，防止同 run 內重複

        for task in result.get("tasks", []):
            # Dedup: 用 should_skip_task 檢查（精確+正規化+相似度三重比對）
            skip, reason = should_skip_task(task["title"], project_dir, extra_norm_set)
            if skip:
                print(f"  🔄 {project_name}: 跳過「{task['title'][:40]}」— {reason}")
                continue

            task_info = {
                "num": task_num,
                "title": task["title"],
                "assignee": task["assignee"],
                "priority": task.get("priority", "Medium"),
                "category": task.get("category", "general"),
                "description": task.get("description", ""),
                "status": "pending",
            }

            if not dry_run:
                create_task_file(project_dir / "tasks", task_num, task_info)
                # 把這次建的標題正規化後加入 extra_norm_set（防止同批次重複）
                norm = task["title"].strip()
                norm = re.sub(r'^T\d+\s*[-–—:]\s*', '', norm)
                norm = re.sub(r'\d{4}[-/]\d{2}[-/]\d{2}', '', norm)
                norm = re.sub(r'https?://\S+', '', norm)
                norm = re.sub(r'[^\w\u4e00-\u9fff]', '', norm)
                norm = re.sub(r'\s+', '', norm).lower()
                extra_norm_set.add(norm)

            tasks_info.append(task_info)
            created.append({
                "project": project_name,
                "task_num": task_num,
                "title": task["title"],
                "assignee": task["assignee"],
                "agent_id": ASSIGNEE_MAP.get(task["assignee"], "main"),
            })
            task_num += 1

        if not dry_run and tasks_info:
            update_project_readme(project_dir, project_name, tasks_info)

    return created


def build_telegram_report(created: list, spawned: list = None) -> str:
    """建立 Telegram 友善格式的報告"""
    if not created:
        return "✅ 無待處理 tasks"

    lines = ["✅ Tasks 已建立", ""]

    by_project = {}
    for c in created:
        proj = c["project"]
        by_project.setdefault(proj, []).append(c)

    for proj, tasks in by_project.items():
        lines.append(f"📁 {proj}/")
        for i, t in enumerate(tasks):
            prefix = "└─" if i == len(tasks) - 1 else "├─"
            spawn_status = "spawned" if spawned and any(s["task_num"] == t["task_num"] for s in spawned) else "pending"
            lines.append(f"  {prefix} T{t['task_num']:03d} → {t['assignee']} ({spawn_status})")
        lines.append("")

    if spawned:
        lines.append("🔄 執行中...")
    else:
        lines.append("📊 統計：建立 {} 個 tasks".format(len(created)))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ideas2tasks executor")
    parser.add_argument("--no-spawn", action="store_true", help="只建立 tasks，不 spawn agents")
    parser.add_argument("--dry-run", action="store_true", help="乾跑模式")
    parser.add_argument("--normalize", action="store_true", help="執行前先統一所有 Tasks/ 的 Status 格式")
    args = parser.parse_args()

    print("🚀 executor.py 啟動")
    print(f"  讀取狀態: {STATUS_FILE}")

    # 0. 統一歷史 Status 格式（可選）
    if args.normalize:
        from state_sync import normalize_all_task_statuses
        fixed = normalize_all_task_statuses()
        print(f"  🔧 修復 {fixed} 個 Status 格式")

    # 1. 讀取狀態
    status = load_status()
    print(f"  待處理 ideas: {status.get('total_actionable', 0)}")

    # 2. 建立 tasks
    created = create_tasks_from_status(status, args.dry_run)

    if args.dry_run:
        print("\n[DRY RUN] 以下 tasks 將被建立：")
        for c in created:
            print(f"  {c['project']}/T{c['task_num']:03d} → {c['assignee']}")
        return

    # 3. 彙報結果
    report = build_telegram_report(created)
    print("\n" + report)

    # 4. 寫入執行狀態
    exec_status = {
        "timestamp": datetime.now().isoformat(),
        "created_count": len(created),
        "created": created,
    }
    exec_file = Path(__file__).parent / "executor_status.json"
    exec_file.write_text(json.dumps(exec_status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 狀態已寫入 executor_status.json")

    # 5. 提示 spawn（實際 spawn 由 OpenClaw session 處理）
    if not args.no_spawn and created:
        print("\n💡 提示：使用以下指令 spawn agents：")
        for c in created:
            agent_id = c["agent_id"]
            print(f"  sessions_spawn(agentId=\"{agent_id}\", task=\"執行 {c['project']}/T{c['task_num']:03d}: {c['title'][:40]}\")")


if __name__ == "__main__":
    main()
