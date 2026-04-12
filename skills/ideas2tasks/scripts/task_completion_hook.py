#!/usr/bin/env python3
"""
ideas2tasks task_completion_hook.py
當 Agent 完成任務時呼叫，同步更新 Tasks/ 和 Ideas/ 的狀態。

修1 核心實作：
- Agent 完成 T001 → 改 T001.md Status: done
- 同時去 idea 檔把 task.1 改成 task.1 done

用法：
  python3 task_completion_hook.py <task_file>           # 標記為 done
  python3 task_completion_hook.py <task_file> --status in-progress  # 其他狀態
  python3 task_completion_hook.py --scan-done           # 掃描所有已 done，同步到 ideas
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from task_status import read_task_status, write_task_status
from sync_status import find_idea_file, mark_task_done_in_idea


TASKS_DIR = Path("/Users/claw/Tasks")


def on_task_completed(task_file: Path, new_status: str = "done") -> dict:
    """
    Task 完成時的處理函數。
    
    步驟：
    1. 更新 task 檔案的 Status
    2. 找到對應的 idea 檔案
    3. 在 idea 檔案中標記 task.N done
    
    Args:
        task_file: Task 檔案路徑 (如 /Users/claw/Tasks/working-issue/tasks/T001.md)
        new_status: 新狀態 (pending / in-progress / done)
    
    Returns:
        {
            "task_file": "...",
            "old_status": "pending",
            "new_status": "done",
            "idea_file": "...",
            "idea_synced": True,
        }
    """
    result = {
        "task_file": str(task_file),
        "old_status": read_task_status(task_file),
        "new_status": new_status,
        "idea_file": None,
        "idea_synced": False,
    }
    
    # 1. 更新 task 檔案狀態
    if not write_task_status(task_file, new_status):
        result["error"] = "Failed to update task status"
        return result
    
    # 2. 找到對應的 idea 檔案
    # 從 task_file 路徑推導專案名稱
    # /Users/claw/Tasks/working-issue/tasks/T001.md → working-issue
    project_name = task_file.parent.parent.name
    idea_file = find_idea_file(project_name)
    
    if not idea_file:
        result["warning"] = f"No idea file found for project: {project_name}"
        return result
    
    result["idea_file"] = str(idea_file)
    
    # 3. 如果狀態是 done，同步到 idea 檔案
    if new_status == "done":
        # 從 T001 提取 task 編號
        task_num_match = re.search(r'T(\d+)', task_file.stem)
        if task_num_match:
            task_num = int(task_num_match.group(1))
            if mark_task_done_in_idea(idea_file, task_num):
                result["idea_synced"] = True
            else:
                result["warning"] = f"Task.{task_num} already marked done in idea file"
    
    return result


def scan_and_sync_done_tasks():
    """
    掃描所有 Tasks/ 目錄，找出已 done 但 idea 檔未同步的 task，進行同步。
    
    用於修復歷史數據。
    """
    print("🔍 掃描已完成的 tasks...")
    
    synced_count = 0
    projects_scanned = 0
    
    for project_dir in TASKS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        if project_dir.name.startswith("_"):
            continue
        
        projects_scanned += 1
        tasks_dir = project_dir / "tasks"
        
        if not tasks_dir.exists():
            continue
        
        # 找出所有 done 的 tasks
        for task_file in tasks_dir.glob("T*.md"):
            status = read_task_status(task_file)
            if status != "done":
                continue
            
            # 檢查 idea 檔是否已同步
            project_name = project_dir.name
            idea_file = find_idea_file(project_name)
            
            if not idea_file:
                continue
            
            # 從 T001 提取 task 編號
            task_num_match = re.search(r'T(\d+)', task_file.stem)
            if not task_num_match:
                continue
            
            task_num = int(task_num_match.group(1))
            
            # 檢查 idea 檔是否已標記
            content = idea_file.read_text(encoding="utf-8")
            pattern = re.compile(rf'^task\.{task_num}\s+done', re.IGNORECASE | re.MULTILINE)
            
            if not pattern.search(content):
                # 需要同步
                if mark_task_done_in_idea(idea_file, task_num):
                    print(f"  ✅ {project_name}/T{task_num:03d} → {idea_file.name}")
                    synced_count += 1
    
    print(f"\n📊 統計：")
    print(f"  掃描專案: {projects_scanned}")
    print(f"  同步 tasks: {synced_count}")
    
    return synced_count


def main():
    parser = argparse.ArgumentParser(description="Task 完成掛鉤")
    parser.add_argument("task_file", nargs="?", help="Task 檔案路徑")
    parser.add_argument("--status", default="done", help="新狀態 (pending/in-progress/done)")
    parser.add_argument("--scan-done", action="store_true", help="掃描所有 done tasks 並同步到 ideas")
    parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")
    args = parser.parse_args()
    
    if args.scan_done:
        synced = scan_and_sync_done_tasks()
        if args.json:
            print(json.dumps({"synced_count": synced}, ensure_ascii=False))
        return
    
    if not args.task_file:
        print("❌ 請提供 task_file 或使用 --scan-done")
        sys.exit(1)
    
    task_file = Path(args.task_file)
    if not task_file.exists():
        print(f"❌ Task 檔案不存在: {task_file}")
        sys.exit(1)
    
    result = on_task_completed(task_file, args.status)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"✅ Task 狀態已更新")
        print(f"  {task_file.name}: {result['old_status']} → {result['new_status']}")
        if result.get("idea_file"):
            if result.get("idea_synced"):
                print(f"  Idea 已同步: {Path(result['idea_file']).name}")
            elif result.get("warning"):
                print(f"  ⚠️  {result['warning']}")


if __name__ == "__main__":
    main()
