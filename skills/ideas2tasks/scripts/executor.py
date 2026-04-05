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
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ===== 配置 =====
TASKS_DIR = Path("/Users/claw/Tasks")
IDEAS_DIR = Path("/Users/claw/Ideas")
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
    
    # 建立 tasks 表格
    table_lines = ["| Task | 標題 | 負責人 | 優先級 | 狀態 |", "|------|------|--------|--------|------|"]
    for t in tasks:
        status = t.get("status", "pending")
        status_icon = "✅" if status == "done" else "pending"
        table_lines.append(f"| T{t['num']:03d} | {t['title'][:30]} | {t['assignee']} | {t['priority']} | {status_icon} |")
    
    # 計算統計
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("status") == "done")
    
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
    """從 status 建立 tasks"""
    created = []
    
    for result in status.get("results", []):
        if result["pending_count"] == 0:
            continue
        
        project_name = result["project_name"]
        project_dir = TASKS_DIR / project_name
        
        if not dry_run:
            project_dir.mkdir(exist_ok=True)
            (project_dir / "tasks").mkdir(exist_ok=True)
        
        tasks_info = []
        task_num = get_next_task_num(project_dir)
        
        for task in result.get("tasks", []):
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
            
            tasks_info.append(task_info)
            created.append({
                "project": project_name,
                "task_num": task_num,
                "title": task["title"],
                "assignee": task["assignee"],
                "agent_id": ASSIGNEE_MAP.get(task["assignee"], "main"),
            })
            task_num += 1
        
        if not dry_run:
            update_project_readme(project_dir, project_name, tasks_info)
    
    return created


def build_telegram_report(created: list, spawned: list = None) -> str:
    """建立 Telegram 友善格式的報告"""
    if not created:
        return "✅ 無待處理 tasks"
    
    lines = ["✅ Tasks 已建立", ""]
    
    # 按專案分組
    by_project = {}
    for c in created:
        proj = c["project"]
        if proj not in by_project:
            by_project[proj] = []
        by_project[proj].append(c)
    
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
    args = parser.parse_args()
    
    print("🚀 executor.py 啟動")
    print(f"  讀取狀態: {STATUS_FILE}")
    
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
