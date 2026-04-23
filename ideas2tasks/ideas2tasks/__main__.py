#!/usr/bin/env python3
"""
ideas2tasks CLI 入口點

用法：
  python3 -m ideas2tasks lifecycle [--dry-run] [--telegram]
  python3 -m ideas2tasks executor [--no-spawn] [--sync-github]
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
        print("  lifecycle       掃描 Ideas → 分類 → 彙整摘要")
        print("  executor        讀取狀態 → 建立 tasks → spawn agents")
        print("  sync <project>  同步狀態（Tasks/ ↔ Ideas/）")
        print("  status <project> 查看專案 task 狀態")
        print()
        print("選項：")
        print("  --dry-run         預覽模式（不執行實際操作）")
        print("  --telegram        發送 Telegram 通知")
        print("  --no-spawn        只建立 tasks，不 spawn agents")
        print("  --sync-github     直接掃 T*.md 建立 GitHub Issue")
        print("  --help, -h        顯示此幫助")
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "lifecycle":
        # 直接調用新模組
        from ideas2tasks.lifecycle import main as lifecycle_main
        # 替換 sys.argv 以模擬直接執行
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
