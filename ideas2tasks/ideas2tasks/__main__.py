#!/usr/bin/env python3
"""
ideas2tasks CLI 入口點

用法：
  python3 -m ideas2tasks lifecycle [--dry-run] [--telegram]
  python3 -m ideas2tasks executor [--no-spawn] [--sync-github]
  python3 -m ideas2tasks sync-status [--project xxx] [--dry-run]
  python3 -m ideas2tasks task-complete <task_file> [--status done]
  python3 -m ideas2tasks task-audit [--project xxx]
  python3 -m ideas2tasks read-status [task_file_or_project]
  python3 -m ideas2tasks --help
"""

from __future__ import annotations

import sys


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("ideas2tasks — 將 Ideas 目錄的想法轉為敏捷任務")
        print()
        print("用法：")
        print("  python3 -m ideas2tasks <command> [options]")
        print()
        print("命令：")
        print("  lifecycle          掃描 Ideas → 分類 → 彙整摘要")
        print("  executor           讀取狀態 → 建立 tasks → spawn agents")
        print("  sync               同步狀態（state_sync 模塊）")
        print("  sync-status        同步 Tasks/ ↔ Ideas/ 狀態")
        print("  task-complete      標記 task 完成（同步到 idea）")
        print("  task-audit         稽核 T*.md 與 README.md 一致性")
        print("  read-status        讀取 task 或專案狀態")
        print("  status <project>   查看專案 task 狀態")
        print()
        print("選項：")
        print("  --dry-run          預覽模式（不執行實際操作）")
        print("  --telegram         發送 Telegram 通知")
        print("  --no-spawn         只建立 tasks，不 spawn agents")
        print("  --sync-github      直接掃 T*.md 建立 GitHub Issue")
        print("  --fix-history      修復歷史不一致")
        print("  --scan-done        掃描所有 done tasks 並同步")
        print("  --help, -h         顯示此幫助")
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "lifecycle":
        from ideas2tasks.lifecycle import main as lifecycle_main
        sys.argv = ["lifecycle"] + args
        lifecycle_main()

    elif command == "executor":
        from ideas2tasks.executor import main as executor_main
        sys.argv = ["executor"] + args
        executor_main()

    elif command == "sync":
        from ideas2tasks.state_sync import sync_idea_to_task_done
        import json

        if len(args) < 1:
            print("用法: python3 -m ideas2tasks sync <project_name>")
            sys.exit(1)

        project_name = args[0]
        result = sync_idea_to_task_done(project_name)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "sync-status":
        from ideas2tasks.sync_status import main as sync_status_main
        sys.argv = ["sync-status"] + args
        sync_status_main()

    elif command == "task-complete":
        from ideas2tasks.task_completion_hook import main as task_complete_main
        sys.argv = ["task-complete"] + args
        task_complete_main()

    elif command == "task-audit":
        from ideas2tasks.task_audit import main as task_audit_main
        sys.argv = ["task-audit"] + args
        task_audit_main()

    elif command == "read-status":
        from ideas2tasks.read_task_status import main as read_status_main
        sys.argv = ["read-status"] + args
        read_status_main()

    elif command == "status":
        from ideas2tasks.state_sync import get_tasks_dir_status
        import json

        if len(args) < 1:
            print("用法: python3 -m ideas2tasks status <project_name>")
            sys.exit(1)

        project_name = args[0]
        status = get_tasks_dir_status(project_name)
        print(json.dumps(status, ensure_ascii=False, indent=2))

    else:
        print(f"❌ 未知命令: {command}")
        print("使用 --help 查看可用命令")
        sys.exit(1)


if __name__ == "__main__":
    main()
