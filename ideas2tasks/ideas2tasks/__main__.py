#!/usr/bin/env python3
"""
ideas2tasks CLI 入口點

用法：
  python3 -m ideas2tasks lifecycle [--dry-run]
  python3 -m ideas2tasks executor [--no-spawn]
  python3 -m ideas2tasks --help
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("ideas2tasks — 將 Ideas 目錄的想法轉為敏捷任務")
        print()
        print("用法：")
        print("  python3 -m ideas2tasks <command> [options]")
        print()
        print("命令：")
        print("  lifecycle   掃描 Ideas → 分類 → 彙整摘要")
        print("  executor    讀取狀態 → 建立 tasks → spawn agents")
        print("  sync        同步狀態（Tasks/ ↔ Ideas/）")
        print()
        print("選項：")
        print("  --dry-run    預覽模式（不執行實際操作）")
        print("  --no-spawn   只建立 tasks，不 spawn agents")
        print("  --help, -h   顯示此幫助")
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    # 找到 scripts 目錄（舊版，向後兼容）
    # 新版會直接 import 模組
    this_dir = Path(__file__).parent

    if command == "lifecycle":
        # 向後兼容：調用舊版 lifecycle.py
        legacy_script = this_dir.parent / "scripts" / "lifecycle.py"
        if legacy_script.exists():
            subprocess.run([sys.executable, str(legacy_script)] + args)
        else:
            print("❌ lifecycle.py 不存在")
            sys.exit(1)

    elif command == "executor":
        legacy_script = this_dir.parent / "scripts" / "executor.py"
        if legacy_script.exists():
            subprocess.run([sys.executable, str(legacy_script)] + args)
        else:
            print("❌ executor.py 不存在")
            sys.exit(1)

    elif command == "sync":
        from ideas2tasks.state_sync import sync_idea_to_task_done, get_tasks_dir_status
        import json

        if len(args) < 1:
            print("用法: python3 -m ideas2tasks sync <project_name>")
            sys.exit(1)

        project_name = args[0]
        result = sync_idea_to_task_done(project_name)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"❌ 未知命令: {command}")
        print("使用 --help 查看可用命令")
        sys.exit(1)


if __name__ == "__main__":
    main()
