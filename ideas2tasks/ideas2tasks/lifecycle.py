#!/usr/bin/env python3
"""
ideas2tasks lifecycle.py
每日 cron 執行：掃描 Ideas → 分類 → 彙報進度摘要

用法：
  python3 -m ideas2tasks lifecycle                    # 完整執行（預設）
  python3 -m ideas2tasks lifecycle --dry-run          # 不產生通知，只看輸出
  python3 -m ideas2tasks lifecycle --telegram        # 發送 Telegram 通知
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

from .scan import scan_ideas
from .classify import classify_idea
from .state_sync import merge_classify_with_tasks_status, sync_idea_to_task_done, scan_tasks_dir
from .config import get_tasks_dir, get_ideas_dir, get_telegram_config_path


def _load_telegram_config() -> tuple[str, str]:
    """從配置讀取 Telegram 設定。"""
    config_path = get_telegram_config_path()
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return (data.get("telegram_bot_token", ""), data.get("telegram_chat_id", ""))
        except Exception:
            pass
    return ("", "")


def send_telegram(text: str) -> bool:
    """發送 Telegram 訊息，回傳成功與否。"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        bot_token, chat_id = _load_telegram_config()
    if not bot_token or not chat_id:
        print("⚠️ 未找到 Telegram 設定（環境變數或配置檔）")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"⚠️ Telegram 發送失敗: {e}")
        return False


def archive_done_ideas(results: list, ideas_dir: Path, dry_run: bool = False) -> list[str]:
    """
    歸檔所有 task 已完成的 idea 檔到 _done/ 目錄。
    回傳：已歸檔的檔名列表。
    """
    done_dir = ideas_dir / "_done"
    done_dir.mkdir(exist_ok=True)
    archived = []

    for r in results:
        has_pending_in_idea = len(r.get("tasks", [])) > 0
        if has_pending_in_idea:
            continue

        idea_file = r.get("idea_file", "")
        if not idea_file:
            continue
        idea_path = Path(idea_file)
        if not idea_path.exists():
            continue

        dest = done_dir / idea_path.name
        if dest.exists():
            stem = idea_path.stem
            suffix = idea_path.suffix
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = done_dir / f"{stem}_{ts}{suffix}"

        if dry_run:
            print(f"  📦 [DRY RUN] 會歸檔: {idea_path.name} → _done/")
        else:
            shutil.move(str(idea_path), str(dest))
            print(f"  📦 歸檔: {idea_path.name} → _done/")

        archived.append(idea_path.name)

    return archived


PROCESSED_FILE = Path(__file__).parent.parent / "scripts" / "processed_ideas.json"


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
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_scan(ideas_dir: Path, skip_processed: bool = True) -> list:
    """執行 scan.py，回傳 ideas 清單。"""
    all_ideas = scan_ideas(str(ideas_dir))
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
    """對每個 idea 執行 classify，並合併 Tasks/ 目錄的實際狀態。"""
    results = []
    for idea in ideas:
        raw_result = classify_idea(idea)
        merged = merge_classify_with_tasks_status(raw_result)
        results.append(merged)
    return results


def build_telegram_summary(results: list, ideas_dir: Path, sync_total: int = 0, tasks_report: list = None) -> str:
    """產生 Telegram 友善格式的摘要（簡潔版）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    tasks_report = tasks_report or []
    tasks_dir = get_tasks_dir()

    total_pending = sum(t["pending_count"] for t in tasks_report)
    total_in_progress = sum(t["in_progress_count"] for t in tasks_report)
    new_ideas = len(results)

    truly_new_actionable = 0
    truly_new_ideas = 0
    for r in results:
        pid = r["project_name"]
        if (tasks_dir / pid).exists() and not r.get("tasks"):
            continue
        if r["total_actionable_tasks"] > 0:
            truly_new_actionable += r["total_actionable_tasks"]
            truly_new_ideas += 1

    if new_ideas == 0 and total_pending == 0 and total_in_progress == 0:
        return f"📋 Ideas 掃描 — {now}\n✅ 無待處理"

    lines = [f"📋 Ideas 掃描 — {now}"]

    if truly_new_ideas > 0 and truly_new_actionable > 0:
        lines.append(f"🆕 待建立: {truly_new_actionable} tasks（{truly_new_ideas} ideas）")

    if total_pending > 0 or total_in_progress > 0:
        lines.append(f"📋 待處理: {total_pending}⬜ {total_in_progress}🔄")

    lines.append("")

    for r in results:
        pid = r["project_name"]
        actionable = r["total_actionable_tasks"]
        if actionable == 0:
            continue
        if (tasks_dir / pid).exists() and not r.get("tasks"):
            continue
        lines.append(f"🆕 {pid}/ ({actionable} tasks)")

    for t in tasks_report:
        pid = t["project_name"]
        pc = t["pending_count"]
        ic = t["in_progress_count"]
        lines.append(f"📁 {pid}/ ({pc}⬜ {ic}🔄)")
        for pt in t["pending_tasks"][:3]:
            lines.append(f"   ├─ {pt['num']}: {pt['title'][:28]}")
        for pt in t["in_progress_tasks"][:2]:
            lines.append(f"   ├─ {pt['num']}: {pt['title'][:28]} 🔄")
        shown = min(len(t["pending_tasks"]), 3) + min(len(t["in_progress_tasks"]), 2)
        remaining = (pc + ic) - shown
        if remaining > 0:
            lines.append(f"   └─ ... +{remaining} more")

    lines.append("")
    lines.append("💬 回覆「確認」執行")
    return "\n".join(lines)


def build_full_summary(results: list, ideas_dir: Path, tasks_report: list = None) -> str:
    """產生完整摘要（終端輸出用）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    tasks_report = tasks_report or []
    tasks_dir = get_tasks_dir()

    total_pending = sum(t["pending_count"] for t in tasks_report)
    total_in_progress = sum(t["in_progress_count"] for t in tasks_report)
    new_ideas = len(results)

    if new_ideas == 0 and total_pending == 0 and total_in_progress == 0:
        return f"📋 Ideas Scan Report — {now}\n Ideas 目錄：{ideas_dir}\n ✅ 無待處理"

    lines = [f"📋 Ideas Scan Report — {now}", f" Ideas 目錄：{ideas_dir}", ""]

    if new_ideas > 0:
        truly_new = []
        for r in results:
            proj_dir = tasks_dir / r["project_name"]
            if not proj_dir.exists():
                truly_new.append(r)
            else:
                if r.get("tasks"):
                    truly_new.append(r)

        new_actionable_real = sum(r["total_actionable_tasks"] for r in truly_new)
        if truly_new and new_actionable_real > 0:
            lines.append(f"🆕 新 Ideas（待建立 tasks）: {new_actionable_real} 個")
            for r in truly_new:
                pid = r["project_name"]
                actionable = r["total_actionable_tasks"]
                cat = r["category"]
                if actionable == 0:
                    continue
                lines.append(f"  📁 [{pid}] ({cat}) — {actionable} tasks 待建立")
                if r["tasks"]:
                    for t in r["tasks"][:3]:
                        lines.append(f"     • {t['title'][:60]} [{t['assignee']}] ⭐{t['priority']}")
                    if len(r["tasks"]) > 3:
                        lines.append(f"     ... 還有 {len(r['tasks']) - 3} 個 tasks")
            lines.append("")

    if total_pending > 0 or total_in_progress > 0:
        lines.append(f"📋 待處理任務（來自 Tasks/ 目錄）: {total_pending} pending | {total_in_progress} in-progress")
        for t in tasks_report:
            pid = t["project_name"]
            pc = t["pending_count"]
            ic = t["in_progress_count"]
            dc = t["done_count"]
            lines.append(f"  📁 [{pid}] ⬜{pc} 🔄{ic} ✅{dc}")
            for pt in t["pending_tasks"]:
                lines.append(f"     ⬜ {pt['num']}: {pt['title'][:60]}")
            for pt in t["in_progress_tasks"]:
                lines.append(f"     🔄 {pt['num']}: {pt['title'][:60]}")
        lines.append("")

    lines.append("請確認後執行！")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ideas2tasks 每日 lifecycle")
    parser.add_argument("--ideas-dir", default=None, help="自訂 Ideas 目錄")
    parser.add_argument("--dry-run", action="store_true", help="只輸出，不發送通知")
    parser.add_argument("--json", action="store_true", help="輸出 JSON 而非文字摘要")
    parser.add_argument("--telegram", action="store_true", help="輸出 Telegram 簡潔格式")
    parser.add_argument("--force-rescan", action="store_true", help="忽略 processed 記錄，重新掃描所有 ideas")
    args = parser.parse_args()

    ideas_dir = Path(args.ideas_dir) if args.ideas_dir else get_ideas_dir()
    tasks_dir = get_tasks_dir()

    # 1. 掃描 ideas
    skip = not args.force_rescan and not args.telegram
    ideas = run_scan(ideas_dir, skip_processed=skip)

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

    # 3.5 歸檔：全 done 的 idea → _done/
    archived = archive_done_ideas(results, ideas_dir, dry_run=args.dry_run)
    if archived and not args.telegram:
        print(f"  📦 歸檔了 {len(archived)} 個已完成的 idea")

    # 從 processed_ideas.json 移除已歸檔的條目
    if archived and not args.dry_run:
        processed = load_processed()
        for fname in archived:
            processed["processed"].pop(fname, None)
        save_processed(processed)

    # 4. 掃描 Tasks/ 目錄
    tasks_report = scan_tasks_dir()

    # 統計
    total_pending = sum(t["pending_count"] for t in tasks_report)
    total_in_progress = sum(t["in_progress_count"] for t in tasks_report)
    new_actionable = sum(r["total_actionable_tasks"] for r in results)

    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "ideas_dir": str(ideas_dir),
            "new_ideas": len(results),
            "new_actionable": new_actionable,
            "tasks_pending": total_pending,
            "tasks_in_progress": total_in_progress,
            "sync_marked": sync_total,
            "results": results,
            "tasks_report": tasks_report,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # 終端輸出
    if not args.telegram:
        summary = build_full_summary(results, ideas_dir, tasks_report)
        print(summary)
        if sync_total > 0:
            print(f"\n  🔄 已同步 {sync_total} 個 done 標記到 idea 檔")

    # JSON 寫入狀態檔
    status_file = Path(__file__).parent.parent / "scripts" / "lifecycle_status.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "ideas_dir": str(ideas_dir),
        "new_ideas": len(results),
        "new_actionable": new_actionable,
        "tasks_pending": total_pending,
        "tasks_in_progress": total_in_progress,
        "sync_marked": sync_total,
        "has_pending": total_pending > 0 or total_in_progress > 0,
        "results": results,
        "tasks_report": tasks_report,
    }, ensure_ascii=False), encoding="utf-8")

    # Telegram 格式
    if args.telegram:
        if new_actionable == 0 and total_pending == 0 and total_in_progress == 0:
            print("📋 Ideas scan 完成，無待處理 tasks")
            return
        summary = build_telegram_summary(results, ideas_dir, sync_total, tasks_report)
        if not args.dry_run:
            ok = send_telegram(summary)
            if ok:
                print(f"✅ Telegram 通知已發送")
            else:
                print(summary)
        else:
            print(summary)
        return

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
