#!/usr/bin/env python3
"""
ideas2tasks lifecycle.py
每日 cron 執行：掃描 Ideas → 分類 → 彙報進度摘要

用法：
  python3 lifecycle.py                    # 完整執行（預設）
  python3 lifecycle.py --dry-run         # 不產生通知，只看輸出
  python3 lifecycle.py --ideas-dir /path  # 自訂 Ideas 目錄
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 從相對位置 import 同目錄的 scan / classify 模組
sys.path.insert(0, str(Path(__file__).parent))
from scan import scan_ideas
from classify import classify_idea


def run_scan(ideas_dir: str) -> list:
    """執行 scan.py，回傳 ideas 清單。"""
    return scan_ideas(ideas_dir)


def run_classify(ideas: list) -> list:
    """對每個 idea 執行 classify，回傳分類結果。"""
    return [classify_idea(idea) for idea in ideas]


def build_telegram_summary(results: list, ideas_dir: str) -> str:
    """產生 Telegram 友善格式的摘要（簡潔版）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)

    if total == 0:
        lines = [
            f"📋 Ideas 掃描 — {now}",
            "✅ 無待處理 idea",
        ]
    else:
        total_actionable = sum(r["total_actionable_tasks"] for r in results)
        total_done = sum(r["done_count"] for r in results)
        
        lines = [
            f"📋 Ideas 掃描 — {now}",
            f"📊 待處理: {total_actionable} | 已完成: {total_done}",
            "",
        ]

        for r in results:
            pid = r["project_name"]
            pending = r["pending_count"]
            actionable = r["total_actionable_tasks"]
            
            if actionable == 0:
                continue  # 跳過無待處理的專案
            
            # 按負責人分組
            by_assignee = {}
            for t in r["tasks"]:
                a = t["assignee"]
                if a not in by_assignee:
                    by_assignee[a] = []
                by_assignee[a].append(t)
            
            lines.append(f"📁 {pid}/")
            for assignee, tasks in by_assignee.items():
                for i, t in enumerate(tasks):
                    prefix = "└─" if i == len(tasks) - 1 else "├─"
                    lines.append(f"  {prefix} {t['title'][:30]} → {assignee}")
            lines.append("")
        
        lines.append("💬 回覆「確認」執行")

    return "\n".join(lines)


def build_full_summary(results: list, ideas_dir: str) -> str:
    """產生完整摘要（終端輸出用）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)

    if total == 0:
        lines = [
            f"📋 Ideas Scan Report — {now}",
            f" Ideas 目錄：{ideas_dir}",
            f" 發現 0 個待處理 idea ✅",
            f" 暫無新任務。",
        ]
    else:
        lines = [f"📋 Ideas Scan Report — {now}", f" Ideas 目錄：{ideas_dir}", ""]
        total_actionable = sum(r["total_actionable_tasks"] for r in results)
        total_done = sum(r["done_count"] for r in results)
        lines.append(f"發現 {total} 個 idea 檔案，")
        lines.append(f"  待處理 tasks：{total_actionable} 個")
        lines.append(f"  已完成 tasks：{total_done} 個")
        lines.append("")

        for r in results:
            pid = r["project_name"]
            pending = r["pending_count"]
            done = r["done_count"]
            actionable = r["total_actionable_tasks"]
            assignees = ", ".join(r["assignees"])
            cat = r["category"]
            lines.append(f"  📁 [{pid}] ({cat})")
            lines.append(f"     待處理: {pending} | 已完成: {done} | 可執行: {actionable}")
            lines.append(f"     負責人: {assignees}")

            # 列出 pending tasks 摘要
            if r["tasks"]:
                for t in r["tasks"][:3]:  # 最多顯示前 3 個
                    lines.append(f"     • {t['title'][:60]} [{t['assignee']}] ⭐{t['priority']}")
                if len(r["tasks"]) > 3:
                    lines.append(f"     ... 還有 {len(r['tasks']) - 3} 個 tasks")
            lines.append("")

        lines.append("請確認後執行！")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ideas2tasks 每日 lifecycle")
    parser.add_argument("--ideas-dir", default="/Users/claw/Ideas")
    parser.add_argument("--dry-run", action="store_true", help="只輸出，不發送通知")
    parser.add_argument("--json", action="store_true", help="輸出 JSON 而非文字摘要")
    parser.add_argument("--telegram", action="store_true", help="輸出 Telegram 簡潔格式")
    args = parser.parse_args()

    ideas = run_scan(args.ideas_dir)
    results = run_classify(ideas)

    if args.json:
        print(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "ideas_dir": args.ideas_dir,
            "results": results,
        }, ensure_ascii=False, indent=2))
        return

    # 終端輸出用完整格式
    if not args.telegram:
        summary = build_full_summary(results, args.ideas_dir)
        print(summary)

    # JSON 結構一併寫入狀態檔，供 executor.py 使用
    status_file = Path(__file__).parent / "lifecycle_status.json"
    status_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "ideas_dir": args.ideas_dir,
        "total_ideas": len(results),
        "total_actionable": sum(r["total_actionable_tasks"] for r in results),
        "total_done": sum(r["done_count"] for r in results),
        "has_pending": any(r["pending_count"] > 0 for r in results),
        "results": results,
    }, ensure_ascii=False), encoding="utf-8")

    # Telegram 格式輸出（供 cron 通知用）
    if args.telegram:
        telegram_summary = build_telegram_summary(results, args.ideas_dir)
        print(telegram_summary)

    if args.dry_run:
        print("\n[DRY RUN] 未發送通知")
    else:
        print("\n✅ Lifecycle 完成，狀態已寫入 lifecycle_status.json")


if __name__ == "__main__":
    main()
