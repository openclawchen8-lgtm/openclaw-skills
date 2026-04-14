#!/usr/bin/env python3
from __future__ import annotations
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
import sys
from datetime import datetime
from pathlib import Path

# 從相對位置 import 同目錄的 scan / classify / state_sync 模組
sys.path.insert(0, str(Path(__file__).parent))
from scan import scan_ideas
from classify import classify_idea
from state_sync import merge_classify_with_tasks_status, TASKS_DIR, sync_idea_to_task_done


PROCESSED_FILE = Path(__file__).parent / "processed_ideas.json"


def load_processed() -> dict:
    """讀取已處理 idea 記錄"""
    if PROCESSED_FILE.exists():
        try:
            return json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"processed": {}}
    return {"processed": {}}


def save_processed(data: dict):
    """儲存已處理 idea 記錄"""
    PROCESSED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_scan(ideas_dir: str, skip_processed: bool = True) -> list:
    """執行 scan.py，回傳 ideas 清單。若 skip_processed=True，跳過已處理過的 idea。"""
    all_ideas = scan_ideas(ideas_dir)
    if not skip_processed:
        return all_ideas

    processed = load_processed()
    processed_filenames = set(processed.get("processed", {}).keys())

    new_ideas = [idea for idea in all_ideas if idea["filename"] not in processed_filenames]
    skipped = len(all_ideas) - len(new_ideas)
    if skipped > 0:
        print(f"  🔄 跳過 {skipped} 個已處理 ideas")

    return new_ideas


def run_classify(ideas: list) -> list:
    """
    對每個 idea 執行 classify，並合併 Tasks/ 目錄的實際狀態。
    重要：Tasks/ 目錄是 ground truth。已 done 的 task 不會再被建一次。
    """
    results = []
    for idea in ideas:
        raw_result = classify_idea(idea)
        merged = merge_classify_with_tasks_status(raw_result)
        results.append(merged)
    return results


def build_telegram_summary(results: list, ideas_dir: str, sync_total: int = 0) -> str:
    """產生 Telegram 友善格式的摘要（簡潔版）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)

    if total == 0:
        return f"📋 Ideas 掃描 — {now}\n✅ 無待處理 idea"

    total_actionable = sum(r["total_actionable_tasks"] for r in results)
    total_done = sum(r.get("done_in_tasks", r["done_count"]) for r in results)

    lines = [
        f"📋 Ideas 掃描 — {now}",
        f"📊 待處理: {total_actionable} | Tasks/ 已完成: {total_done} (含 merge 前次 {sync_total} 個)",
        "",
    ]
    if sync_total > 0:
        lines.append(f"🔄 已同步 {sync_total} 個 done 標記到 idea 檔")
        lines.append("")

    for r in results:
        pid = r["project_name"]
        actionable = r["total_actionable_tasks"]
        done_tasks = r.get("done_in_tasks", 0)
        pending_tasks = r.get("pending_in_tasks", 0)

        if actionable == 0:
            continue  # 跳過無待處理 tasks 的專案

        by_assignee = {}
        for t in r["tasks"]:
            a = t["assignee"]
            by_assignee.setdefault(a, []).append(t)

        lines.append(f"📁 {pid}/")
        if done_tasks or pending_tasks:
            lines.append(f"   ✅ {done_tasks} done | 📋 {pending_tasks} in Tasks/")
        for assignee, tasks in by_assignee.items():
            for i, t in enumerate(tasks):
                prefix = "└─" if i == len(tasks) - 1 else "├─"
                lines.append(f"   {prefix} {t['title'][:28]} → {assignee}")
        lines.append("")

    lines.append("💬 回覆「確認」執行")
    return "\n".join(lines)


def build_full_summary(results: list, ideas_dir: str) -> str:
    """產生完整摘要（終端輸出用）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)

    if total == 0:
        return f"📋 Ideas Scan Report — {now}\n Ideas 目錄：{ideas_dir}\n 發現 0 個待處理 idea ✅\n 暫無新任務。"

    lines = [f"📋 Ideas Scan Report — {now}", f" Ideas 目錄：{ideas_dir}", ""]
    total_actionable = sum(r["total_actionable_tasks"] for r in results)
    total_done = sum(r.get("done_in_tasks", r["done_count"]) for r in results)
    lines.append(f"發現 {total} 個 idea 檔案，")
    lines.append(f"  待處理 tasks（合併後）：{total_actionable} 個")
    lines.append(f"  Tasks/ 目錄已完成：{total_done} 個")
    lines.append("")

    for r in results:
        pid = r["project_name"]
        actionable = r["total_actionable_tasks"]
        done_in_tasks = r.get("done_in_tasks", 0)
        assignees = ", ".join(r["assignees"])
        cat = r["category"]

        lines.append(f"  📁 [{pid}] ({cat})")
        lines.append(f"     待處理: {actionable} | Tasks/ done: {done_in_tasks} | 負責人: {assignees}")

        if r["tasks"]:
            for t in r["tasks"][:3]:
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
    parser.add_argument("--force-rescan", action="store_true", help="忽略 processed 記錄，重新掃描所有 ideas")
    args = parser.parse_args()

    # 1. 掃描 ideas
    ideas = run_scan(args.ideas_dir, skip_processed=not args.force_rescan)

    # 2. 分類（合併 Tasks/ 實際狀態）
    results = run_classify(ideas)

    # 3. 同步：Tasks/ done → idea 檔 done 標記
    sync_total = 0
    for r in results:
        project_name = r.get("project_name", "")
        tasks_status = r.get("_tasks_status", {})
        if tasks_status:
            sync = sync_idea_to_task_done(project_name)
            if sync.get("done", 0) > 0:
                sync_total += sync["done"]

    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "ideas_dir": args.ideas_dir,
            "total_ideas": len(results),
            "total_actionable": sum(r["total_actionable_tasks"] for r in results),
            "total_done": sum(r.get("done_in_tasks", r["done_count"]) for r in results),
            "sync_marked": sync_total,
            "results": results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # 終端輸出
    if not args.telegram:
        summary = build_full_summary(results, args.ideas_dir)
        print(summary)
        if sync_total > 0:
            print(f"\n  🔄 已同步 {sync_total} 個 done 標記到 idea 檔")

    # JSON 寫入狀態檔（供 executor.py 使用）
    status_file = Path(__file__).parent / "lifecycle_status.json"
    status_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "ideas_dir": args.ideas_dir,
        "total_ideas": len(results),
        "total_actionable": sum(r["total_actionable_tasks"] for r in results),
        "total_done": sum(r.get("done_in_tasks", r["done_count"]) for r in results),
        "sync_marked": sync_total,
        "has_pending": any(r["pending_count"] > 0 for r in results),
        "results": results,
    }, ensure_ascii=False), encoding="utf-8")

    # Telegram 格式
    if args.telegram:
        print(build_telegram_summary(results, args.ideas_dir, sync_total))

    # 標記本次處理的 ideas 為已處理
    processed = load_processed()
    for r in results:
        idea_file = r.get("idea_file", "") or ""
        if idea_file:
            fname = Path(idea_file).name
            processed["processed"][fname] = {
                "timestamp": datetime.now().isoformat(),
                "project": r.get("project_name", ""),
                "task_count": r.get("pending_count", 0),
            }
    save_processed(processed)

    if args.dry_run:
        print("\n[DRY RUN] 未發送通知")
    else:
        print("\n✅ Lifecycle 完成，狀態已寫入 lifecycle_status.json")


if __name__ == "__main__":
    main()
