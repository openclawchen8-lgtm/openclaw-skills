"""
ideas2tasks — 將 Ideas 目錄的想法轉為敏捷任務

公共 API：
- scan_ideas(): 掃描 Ideas 目錄
- classify_idea(): 分類單個 idea
- lifecycle_run(): 執行完整 lifecycle 流程
- executor_run(): 執行 executor 流程

CLI 入口：
  python3 -m ideas2tasks lifecycle
  python3 -m ideas2tasks executor
  python3 -m ideas2tasks --help
"""

from ideas2tasks.config import load_config, get_tasks_dir, get_ideas_dir
from ideas2tasks.scan import scan_ideas
from ideas2tasks.classify import classify_idea
from ideas2tasks.state_sync import (
    read_task_status,
    write_task_status,
    get_tasks_dir_status,
    sync_idea_to_task_done,
)

__version__ = "2.2.0"
__all__ = [
    # Configuration
    "load_config",
    "get_tasks_dir",
    "get_ideas_dir",
    # Core functions
    "scan_ideas",
    "classify_idea",
    # State sync
    "read_task_status",
    "write_task_status",
    "get_tasks_dir_status",
    "sync_idea_to_task_done",
]
