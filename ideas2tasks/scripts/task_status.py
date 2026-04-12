#!/usr/bin/env python3
"""
ideas2tasks task_status.py
統一 Task Status 讀寫工具。

修3 核心實作：
- 正規化讀取（忽略大小寫、emoji、空白）
- 統一寫入格式：Status: pending / in-progress / done
"""

import re
from pathlib import Path


# 正規化映射表：各種變體 → 標準值
STATUS_NORMALIZE = {
    "pending": "pending",
    "in-progress": "in-progress",
    "in_progress": "in-progress",
    "in progress": "in-progress",
    "doing": "in-progress",
    "active": "in-progress",
    "done": "done",
    "completed": "done",
    "complete": "done",
    "finished": "done",
    "closed": "done",
    "skip": "done",
    "skipped": "done",
}

# 用於從 task 檔案中提取 Status 行的正則
STATUS_PATTERN = re.compile(
    r'^[-*\s]*\**Status\**\s*[:：]\s*(.+)$',
    re.MULTILINE | re.IGNORECASE
)


def read_task_status(task_file: Path) -> str:
    """
    從 task 檔案讀取 Status，回傳正規化後的值。
    
    處理以下格式：
    - Status: pending
    - status: done
    - **Status**: ✅ done
    - - Status: done ✅
    - Status：in-progress
    
    回傳：pending / in-progress / done（標準三值之一）
    """
    if not task_file.exists():
        return "pending"
    
    try:
        content = task_file.read_text(encoding="utf-8")
    except Exception:
        return "pending"
    
    m = STATUS_PATTERN.search(content)
    if not m:
        return "pending"
    
    raw = m.group(1).strip()
    
    # 移除 emoji 和多餘符號
    cleaned = re.sub(r'[✅❌⏳🔄🚧✔️✓√]', '', raw).strip()
    # 移除前後的 ** 或其他 markdown 符號
    cleaned = re.sub(r'^[*_`]+|[*_`]+$', '', cleaned).strip()
    
    # 正規化
    normalized = STATUS_NORMALIZE.get(cleaned.lower(), "pending")
    return normalized


def write_task_status(task_file: Path, status: str) -> bool:
    """
    將 task 檔案的 Status 更新為標準格式。
    
    只接受三個值：pending / in-progress / done
    回傳 True 表示成功更新。
    """
    if status not in ("pending", "in-progress", "done"):
        return False
    
    if not task_file.exists():
        return False
    
    try:
        content = task_file.read_text(encoding="utf-8")
    except Exception:
        return False
    
    # 替換現有的 Status 行
    new_content, count = STATUS_PATTERN.subn(
        f'Status: {status}',
        content
    )
    
    if count > 0:
        task_file.write_text(new_content, encoding="utf-8")
        return True
    
    return False


def scan_project_tasks(project_dir: Path) -> dict:
    """
    掃描專案目錄下所有 T*.md，回傳各狀態的 task 清單。
    
    回傳格式：
    {
        "pending": [T001, T003, ...],
        "in-progress": [T002],
        "done": [T004, T005],
    }
    """
    tasks_dir = project_dir / "tasks"
    result = {"pending": [], "in-progress": [], "done": []}
    
    if not tasks_dir.exists():
        return result
    
    for task_file in sorted(tasks_dir.glob("T*.md")):
        status = read_task_status(task_file)
        task_num = task_file.stem  # e.g. "T001"
        result[status].append(task_num)
    
    return result


def get_project_done_count(project_dir: Path) -> int:
    """快速取得專案已完成的 task 數量。"""
    return len(scan_project_tasks(project_dir).get("done", []))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: task_status.py <task_file_or_project_dir>")
        sys.exit(1)
    
    target = Path(sys.argv[1])
    
    if target.is_dir():
        # 掃描整個專案
        tasks = scan_project_tasks(target)
        print(f"Pending:     {len(tasks['pending'])}  {tasks['pending']}")
        print(f"In-progress: {len(tasks['in-progress'])}  {tasks['in-progress']}")
        print(f"Done:        {len(tasks['done'])}  {tasks['done']}")
    else:
        # 讀取單一 task
        status = read_task_status(target)
        print(f"Status: {status}")
