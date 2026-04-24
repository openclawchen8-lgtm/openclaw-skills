#!/usr/bin/env python3
"""
ideas2tasks read_task_status.py
統一的 Task 狀態讀取器，處理格式不一致問題。

支援格式：
  - Status: pending
  - Status: done
  - Status: in-progress
  - status: done (小寫)
  - Status: ✅ done (帶 emoji)
  - Status: done ✅ (emoji 後置)

回傳標準化狀態：
  - "pending"
  - "in-progress"
  - "done"
"""

import re
from pathlib import Path


def normalize_status(raw_status: str) -> str:
    """
    將各種格式的狀態正規化為標準狀態。
    
    Args:
        raw_status: 原始狀態字串（可能含 emoji、大小寫不一致）
    
    Returns:
        "pending" | "in-progress" | "done"
    """
    # 轉小寫、移除 emoji、空白
    cleaned = re.sub(r'[✅❌🔄⏳📝]', '', raw_status.lower()).strip()
    
    # 標準化對照表
    status_map = {
        "pending": "pending",
        "in-progress": "in-progress",
        "in_progress": "in-progress",
        "doing": "in-progress",
        "ongoing": "in-progress",
        "done": "done",
        "completed": "done",
        "finished": "done",
    }
    
    return status_map.get(cleaned, "pending")


def read_task_status(task_file: Path) -> str:
    """
    從 task 檔案讀取狀態。
    
    Args:
        task_file: Task 檔案路徑 (T001.md)
    
    Returns:
        "pending" | "in-progress" | "done"
    """
    if not task_file.exists():
        return "pending"
    
    content = task_file.read_text(encoding="utf-8")
    
    # 匹配 Status 欄位（支援多種格式）
    # 格式 1: - **Status**: done
    # 格式 2: status: done
    # 格式 3: Status: pending
    patterns = [
        r'\*\*Status\*\*:\s*(.+)',  # Markdown 格式
        r'^status:\s*(.+)',          # YAML 格式（小寫）
        r'^Status:\s*(.+)',          # YAML 格式（大寫）
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        if match:
            raw_status = match.group(1).strip()
            return normalize_status(raw_status)
    
    return "pending"


def read_all_task_status(project_dir: Path) -> dict:
    """
    讀取專案所有 tasks 的狀態。
    
    Args:
        project_dir: 專案目錄 (如 /Users/claw/Tasks/working-issue)
    
    Returns:
        {
            "T001": "done",
            "T002": "pending",
            ...
        }
    """
    tasks_dir = project_dir / "tasks"
    if not tasks_dir.exists():
        return {}
    
    statuses = {}
    for task_file in tasks_dir.glob("T*.md"):
        task_num = task_file.stem  # T001
        statuses[task_num] = read_task_status(task_file)
    
    return statuses


def count_task_statuses(project_dir: Path) -> dict:
    """
    統計專案 task 狀態數量。
    
    Returns:
        {
            "total": 5,
            "pending": 3,
            "in-progress": 1,
            "done": 1,
        }
    """
    statuses = read_all_task_status(project_dir)
    
    return {
        "total": len(statuses),
        "pending": sum(1 for s in statuses.values() if s == "pending"),
        "in-progress": sum(1 for s in statuses.values() if s == "in-progress"),
        "done": sum(1 for s in statuses.values() if s == "done"),
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        task_file = Path(sys.argv[1])
        status = read_task_status(task_file)
        print(f"{task_file.name}: {status}")
    else:
        # 測試：讀取所有 Tasks 目錄
        tasks_root = Path("/Users/claw/Tasks")
        for project_dir in tasks_root.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith("_"):
                stats = count_task_statuses(project_dir)
                print(f"{project_dir.name}: {stats}")
