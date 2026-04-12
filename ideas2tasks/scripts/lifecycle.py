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

# 從相對位置 import 同目錄的 scan / classify / task_status 模組
sys.path.insert(0, str(Path(__file__).parent))
from scan import scan_ideas
from classify import classify_idea
from task_status import scan_project_tasks, get_project_done_count


PROCESSED_FILE = Path(__file__).parent / "processed_ideas.json"
TASKS_DIR = Path("/Users/claw/Tasks")


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
    
    修2 核心邏輯：
    - 先掃描 /Users/claw/Tasks/{project}/tasks/T*.md 的 Status
    - Tasks/ 已 done 的 task → 從 pending 中移除，計入 done_count
    - 兩邊合併判斷，避免 idea 檔沒標 done 但 Tasks/ 已完成的問題
    """
    results = []
    for idea in ideas:
        result = classify_idea(idea)
        project_name = result.get("project_name", "")
        project_dir = TASKS_DIR / project_name
        
        if project_dir.exists():
            # 掃描 Tasks/ 目錄的實際狀態
            tasks_status = scan_project_tasks(project_dir)
            done_in_tasks = len(tasks_status.get("done", []))
            
            # 如果 Tasks/ 有已完成的 task，修正 idea 檔的 done_count
            if done_in_tasks > 0:
                old_done = result.get("done_count", 0)
                if done_in_tasks > old_done:
                    result["done_count"] = done_in_tasks
                    result["_status_source"] = "Tasks/ (覆蓋 idea 檔)"
                    
                    # 從 pending tasks 中移除已在 Tasks/ 標 done 的
                    # （比對標題去重太脆弱，用 task 數量差異修正）
                    extra_done = done_in_tasks - old_done
                    if extra_done > 0 and result.get("pending_count", 0) > 0:
                        # 保留 pending 但調整計數
                        adjusted_pending = max(0, result["pending_count"] - extra_done)
                        result["pending_count"] = adjusted_pending
                        result["total_actionable_tasks"] = min(
                            result.get("total_actionable_tasks", 0),
                            adjusted_pending
                        )
                        # 只保留還在 pending 的 tasks
                        if extra_done <= len(result.get("tasks", [])):
                            result["tasks"] = result["tasks"][extra_done:]
                else:
                    result["_status_source"] = "idea 檔 (與 Tasks/ 一致)"
            else:
                result["_status_source"] = "idea 檔 (Tasks/ 無 done)"
        else:
            result["_status_source"] = "idea 檔 (專案目錄不存在)"
        
        results.append(result)
    
    return results


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

    # 標記本次處理的 ideas 為已處理
    processed = load_processed()
    for r in results:
        idea_file = r.get("idea_file", "")
        if idea_file:
            processed["processed"][idea_file] = {
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
