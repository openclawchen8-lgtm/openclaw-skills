#!/usr/bin/env python3
"""
ideas2tasks sync_status.py
狀態同步器：確保 Tasks/ 目錄與 Ideas/ 檔案狀態一致。

核心功能：
1. 當 Task 狀態變更為 done，自動更新對應 idea 檔的 task.N done 標記
2. 提供手動同步工具，修復歷史不一致

用法：
  python3 sync_status.py                    # 同步所有專案
  python3 sync_status.py --project working-issue  # 同步特定專案
  python3 sync_status.py --dry-run          # 預覽模式
  python3 sync_status.py --fix-history      # 修復歷史不一致
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from read_task_status import read_task_status, read_all_task_status


TASKS_DIR = Path("/Users/claw/Tasks")
IDEAS_DIR = Path("/Users/claw/Ideas")


def find_idea_file(project_name: str) -> Path | None:
    """
    根據專案名稱找到對應的 idea 檔案。
    
    Args:
        project_name: 專案名稱（如 "working-issue"）
    
    Returns:
        idea 檔案路徑，若找不到則回傳 None
    """
    # 可能的檔名格式
    candidates = [
        IDEAS_DIR / f"{project_name}.txt",
        IDEAS_DIR / f"{project_name}.md",
        IDEAS_DIR / f"{project_name.replace('-', '_')}.txt",
        IDEAS_DIR / f"{project_name.replace('-', '_')}.md",
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    return None


def mark_task_done_in_idea(idea_file: Path, task_num: int) -> bool:
    """
    在 idea 檔案中標記 task.N 為 done。
    
    Args:
        idea_file: idea 檔案路徑
        task_num: task 編號（如 1, 2, 3）
    
    Returns:
        是否成功修改
    """
    content = idea_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    modified = False
    
    # 匹配 task.N 或 task.N done
    pattern = re.compile(rf'^(task\.{task_num})(\s+done)?[\s_]*(.*)$', re.IGNORECASE)
    
    for i, line in enumerate(lines):
        match = pattern.match(line.strip())
        if match:
            # 檢查是否已標記為 done
            if match.group(2):  # 已有 done 標記
                continue
            
            # 加入 done 標記
            rest = match.group(3).strip()
            new_line = f"task.{task_num} done {rest}".strip()
            lines[i] = line.replace(match.group(0), new_line)
            modified = True
            print(f"  ✏️  {idea_file.name}: task.{task_num} → task.{task_num} done")
            break
    
    if modified:
        idea_file.write_text("\n".join(lines), encoding="utf-8")
    
    return modified


def sync_project(project_dir: Path, dry_run: bool = False) -> dict:
    """
    同步單一專案的狀態。
    
    Args:
        project_dir: 專案目錄
        dry_run: 預覽模式（不實際修改）
    
    Returns:
        {
            "project": "working-issue",
            "idea_file": "...",
            "synced": [1, 3],  # 已同步的 task 編號
            "errors": [],
        }
    """
    project_name = project_dir.name
    result = {
        "project": project_name,
        "idea_file": None,
        "synced": [],
        "errors": [],
    }
    
    # 1. 找到對應 idea 檔案
    idea_file = find_idea_file(project_name)
    if not idea_file:
        result["errors"].append(f"找不到 idea 檔案: {project_name}")
        return result
    
    result["idea_file"] = str(idea_file)
    
    # 2. 讀取 Tasks 狀態
    task_statuses = read_all_task_status(project_dir)
    
    # 3. 對每個 done 的 task，確保 idea 檔已標記
    for task_id, status in task_statuses.items():
        if status != "done":
            continue
        
        task_num = int(task_id[1:])  # T001 → 1
        
        if dry_run:
            # 預覽模式：只檢查是否需要同步
            content = idea_file.read_text(encoding="utf-8")
            pattern = re.compile(rf'^task\.{task_num}\s+done', re.IGNORECASE | re.MULTILINE)
            if not pattern.search(content):
                print(f"  🔍 {idea_file.name}: task.{task_num} 需同步 (dry-run)")
                result["synced"].append(task_num)
        else:
            # 實際同步
            if mark_task_done_in_idea(idea_file, task_num):
                result["synced"].append(task_num)
    
    return result


def sync_all_projects(dry_run: bool = False) -> list[dict]:
    """
    同步所有專案的狀態。
    
    Returns:
        各專案的同步結果列表
    """
    results = []
    
    for project_dir in TASKS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        if project_dir.name.startswith("_"):  # 跳過 _inbox, _done 等
            continue
        
        print(f"\n📁 同步專案: {project_dir.name}")
        result = sync_project(project_dir, dry_run)
        results.append(result)
    
    return results


def fix_history():
    """
    修復歷史不一致：掃描所有 Tasks/ done 的狀態，確保 Ideas/ 已標記。
    """
    print("🔧 修復歷史狀態不一致...")
    
    results = sync_all_projects(dry_run=False)
    
    total_synced = sum(len(r["synced"]) for r in results)
    total_errors = sum(len(r["errors"]) for r in results)
    
    print(f"\n✅ 修復完成")
    print(f"  同步 tasks: {total_synced}")
    print(f"  錯誤: {total_errors}")
    
    # 寫入修復記錄
    log_file = Path(__file__).parent / "sync_history.json"
    log_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_synced": total_synced,
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"  記錄已寫入: {log_file}")


def main():
    parser = argparse.ArgumentParser(description="Task 狀態同步器")
    parser.add_argument("--project", help="同步特定專案")
    parser.add_argument("--dry-run", action="store_true", help="預覽模式")
    parser.add_argument("--fix-history", action="store_true", help="修復歷史不一致")
    args = parser.parse_args()
    
    if args.fix_history:
        fix_history()
        return
    
    if args.project:
        project_dir = TASKS_DIR / args.project
        if not project_dir.exists():
            print(f"❌ 專案不存在: {args.project}")
            sys.exit(1)
        result = sync_project(project_dir, args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        results = sync_all_projects(args.dry_run)
        total_synced = sum(len(r["synced"]) for r in results)
        print(f"\n📊 統計：需同步 {total_synced} 個 tasks")


if __name__ == "__main__":
    main()
