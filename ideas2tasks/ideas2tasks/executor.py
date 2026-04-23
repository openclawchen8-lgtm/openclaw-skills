#!/usr/bin/env python3
"""
ideas2tasks executor.py
讀取 lifecycle_status.json → 建立 tasks → spawn agents → 彙報結果

用法：
  python3 -m ideas2tasks executor                    # 完整執行
  python3 -m ideas2tasks executor --no-spawn        # 只建立 tasks，不 spawn agents
  python3 -m ideas2tasks executor --dry-run         # 乾跑模式
  python3 -m ideas2tasks executor --sync-github     # 直接掃 T*.md 建立 GitHub Issue
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from .state_sync import (
    get_tasks_dir_status,
    read_task_status,
    write_task_status,
    should_skip_task,
)
from .config import get_tasks_dir, get_ideas_dir


# GitHub 設定（可透過環境變數覆寫）
GH_OWNER = os.environ.get("IDEAS2TASKS_GH_OWNER", "openclawchen8-lgtm")
GH_REPO = os.environ.get("IDEAS2TASKS_GH_REPO", "openclaw-tasks")
GH_PROJECT_ID = os.environ.get("IDEAS2TASKS_GH_PROJECT_ID", "PVT_kwHOD-tSg84BUX2a")
GH_PROJECT_NUMBER = int(os.environ.get("IDEAS2TASKS_GH_PROJECT_NUMBER", "1"))

# Assignee → AgentId 映射
ASSIGNEE_MAP = {
    "寶寶": "main",
    "豪": "main",
    "豪（用戶）": "main",
    "碼農1號": "agent-coder1",
    "碼農 1 號": "agent-coder1",
    "碼農2號": "agent-coder2",
    "碼農 2 號": "agent-coder2",
    "安安": "agent-ann",
    "樂樂": "agent-lele",
    "研研": "agent-researcher",
}

STATUS_FILE = Path(__file__).parent.parent / "scripts" / "lifecycle_status.json"


def load_status() -> dict:
    """讀取 lifecycle_status.json"""
    if not STATUS_FILE.exists():
        print("❌ lifecycle_status.json 不存在，請先執行 lifecycle")
        raise SystemExit(1)
    return json.loads(STATUS_FILE.read_text(encoding="utf-8"))


def get_next_task_num(project_dir: Path) -> int:
    """取得專案下一個 task 編號"""
    tasks_dir = project_dir / "tasks"
    if not tasks_dir.exists():
        return 1
    existing = list(tasks_dir.glob("T*.md"))
    nums = [int(f.stem[1:]) for f in existing if f.stem[1:].isdigit()]
    return max(nums) + 1 if nums else 1


def create_task_file(task_dir: Path, task_num: int, task: dict) -> Path:
    """建立 task 檔案"""
    task_file = task_dir / f"T{task_num:03d}.md"
    content = f"""# T{task_num:03d} - {task['title'][:50]}

## 基本資訊
- **Type**: {task.get('category', 'general')}
- **Assignee**: {task['assignee']}
- **Priority**: {task.get('priority', 'Medium')}
- **Status**: pending

## 描述
{task.get('description', task['title'])}

## 產出
- [待填寫]

---

_建立日期: {datetime.now().strftime('%Y-%m-%d')}_
"""
    task_file.write_text(content, encoding="utf-8")
    return task_file


def update_project_readme(project_dir: Path, project_name: str, tasks: list):
    """更新專案 README"""
    readme_file = project_dir / "README.md"
    tasks_status = get_tasks_dir_status(project_name)
    table_lines = ["| Task | 標題 | 負責人 | 優先級 | 狀態 |", "|------|------|--------|--------|------|"]

    for t in tasks:
        t_num = f"T{t['num']:03d}"
        status = tasks_status.get(t_num, t.get("status", "pending"))
        status_icon = "✅" if status == "done" else ("🔄" if status == "in-progress" else "⏳")
        table_lines.append(
            f"| {t_num} | {t['title'][:28]} | {t['assignee']} | {t['priority']} | {status_icon} |"
        )

    total = len(tasks)
    done = sum(1 for t in tasks if tasks_status.get(f"T{t['num']:03d}", "") == "done")

    content = f"""# {project_name} 專案

## 概述
由 ideas2tasks 自動建立的任務。

## Tasks 清單

{chr(10).join(table_lines)}

## 進度
- **完成**: {done}/{total}
- **進行中**: 0
- **待處理**: {total - done}

---

_建立日期: {datetime.now().strftime('%Y-%m-%d')}_
"""
    readme_file.write_text(content, encoding="utf-8")


def create_tasks_from_status(status: dict, dry_run: bool = False) -> list:
    """從 status 建立 tasks（已整合去重）"""
    created = []
    tasks_dir = get_tasks_dir()

    for result in status.get("results", []):
        if result.get("pending_count", 0) == 0:
            continue

        project_name = result["project_name"]
        project_dir = tasks_dir / project_name

        if not dry_run:
            project_dir.mkdir(exist_ok=True)
            (project_dir / "tasks").mkdir(exist_ok=True)

        tasks_info = []
        task_num = get_next_task_num(project_dir)
        extra_norm_set = set()

        for task in result.get("tasks", []):
            task_desc = task.get("description", task.get("body", ""))
            skip, reason = should_skip_task(task["title"], project_dir, extra_norm_set, new_desc=task_desc)
            if skip:
                print(f"  🔄 {project_name}: 跳過「{task['title'][:40]}」— {reason}")
                continue

            task_info = {
                "num": task_num,
                "title": task["title"],
                "assignee": task["assignee"],
                "priority": task.get("priority", "Medium"),
                "category": task.get("category", "general"),
                "description": task.get("description", ""),
                "status": "pending",
            }

            if not dry_run:
                create_task_file(project_dir / "tasks", task_num, task_info)
                norm = task["title"].strip()
                norm = re.sub(r'^T\d+\s*[-–—:]\s*', '', norm)
                norm = re.sub(r'\d{4}[-/]\d{2}[-/]\d{2}', '', norm)
                norm = re.sub(r'https?://\S+', '', norm)
                norm = re.sub(r'[^\w\u4e00-\u9fff]', '', norm)
                norm = re.sub(r'\s+', '', norm).lower()
                extra_norm_set.add(norm)

            tasks_info.append(task_info)
            created.append({
                "project": project_name,
                "task_num": task_num,
                "title": task["title"],
                "assignee": task["assignee"],
                "agent_id": ASSIGNEE_MAP.get(task["assignee"], "main"),
            })
            task_num += 1

        if not dry_run and tasks_info:
            update_project_readme(project_dir, project_name, tasks_info)

    return created


def build_telegram_report(created: list, spawned: list = None) -> str:
    """建立 Telegram 友善格式的報告"""
    if not created:
        return "✅ 無待處理 tasks"

    lines = ["✅ Tasks 已建立", ""]

    by_project = {}
    for c in created:
        proj = c["project"]
        by_project.setdefault(proj, []).append(c)

    for proj, tasks in by_project.items():
        lines.append(f"📁 {proj}/")
        for i, t in enumerate(tasks):
            prefix = "└─" if i == len(tasks) - 1 else "├─"
            spawn_status = "spawned" if spawned and any(s["task_num"] == t["task_num"] for s in spawned) else "pending"
            lines.append(f"  {prefix} T{t['task_num']:03d} → {t['assignee']} ({spawn_status})")
        lines.append("")

    if spawned:
        lines.append("🔄 執行中...")
    else:
        lines.append("📊 統計：建立 {} 個 tasks".format(len(created)))

    return "\n".join(lines)


# ─────────────────────────────────────────
# GitHub Issue 同步
# ─────────────────────────────────────────

def gh_run(cmd: str, timeout: int = 15) -> subprocess.CompletedProcess:
    """執行 gh CLI"""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def gh_gql(query: str) -> dict:
    """執行 GitHub GraphQL query"""
    cmd = "gh api graphql --method POST --field 'query=" + query + "'"
    r = gh_run(cmd)
    if not r.stdout.strip():
        return {}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {}


def _humanize_issue_title(raw_title: str, max_len: int = 72) -> str:
    """將原始 task 標題轉為人類可讀的 GitHub Issue 標題"""
    t = raw_title.strip()
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'^(請|幫我|請幫我|我要|需要|想要)\s*', '', t)
    if not t.strip():
        t = raw_title.strip()
    if len(t) > max_len:
        cut = max_len
        for sep in ['。', '？', '！', '；', '、', '，', '：', ' ']:
            pos = t.rfind(sep, 0, max_len)
            if pos > max_len // 2:
                cut = pos + 1
                break
        t = t[:cut].rstrip('，。、；：！？ ')
    if len(t) > max_len:
        t = t[:max_len - 1] + '…'
    return t


def sync_single_task_to_github(proj: str, tid: str, task_md_path: Path) -> dict:
    """同步單一 T*.md 到 GitHub Issue"""
    raw_body = task_md_path.read_text(encoding="utf-8")
    github_blob_url = f"https://github.com/{GH_OWNER}/{GH_REPO}/blob/main/{proj}/tasks/{tid}.md"
    full_body = raw_body.strip() + f"\n\n---\n📂 GitHub: {github_blob_url}\n"

    body_file = f"/tmp/gh_body_{os.getpid()}_{tid}.txt"
    with open(body_file, "w") as f:
        f.write(full_body)

    title_m = re.search(r"^title:\s*(.+)$", raw_body, re.MULTILINE)
    raw_title = title_m.group(1).strip() if title_m else tid
    title = f"[{proj}] {tid} — {_humanize_issue_title(raw_title)}"
    title_esc = title.replace('"', '\\"')

    cmd = f'gh issue create --repo {GH_OWNER}/{GH_REPO} --title "{title_esc}" --body-file {body_file}'
    r = gh_run(cmd)
    os.unlink(body_file)

    if r.returncode != 0:
        print(f"  ❌ {tid} 建立 Issue 失敗: {r.stderr[:80]}")
        return {"tid": tid, "issue_url": None, "added_to_board": False}

    m = re.search(r'/issues/(\d+)', r.stdout)
    issue_num = int(m.group(1)) if m else None
    issue_url = f"https://github.com/{GH_OWNER}/{GH_REPO}/issues/{issue_num}" if issue_num else None

    added_board = False
    if issue_num:
        node_cmd = f'gh api /repos/{GH_OWNER}/{GH_REPO}/issues/{issue_num} --jq .node_id'
        nr = gh_run(node_cmd)
        content_id = nr.stdout.strip().strip('"') if nr.returncode == 0 else None
        if content_id:
            gql = (f"mutation{{addProjectV2ItemById(input:{{projectId:\"{GH_PROJECT_ID}\","
                   f"contentId:\"{content_id}\"}}){{clientMutationId}}}}")
            d = gh_gql(gql)
            added_board = d.get("data", {}).get("addProjectV2ItemById", {}).get("clientMutationId") is None

    # 更新 T*.md 的 github_issue 欄位
    _update_github_issue_url(task_md_path, issue_url)

    status_emoji = "✅" if added_board else "⚠️"
    print(f"  {status_emoji} {tid} → Issue #{issue_num} | Board: {'✅' if added_board else '❌'}")
    return {"tid": tid, "issue_url": issue_url, "added_to_board": added_board}


def _update_github_issue_url(task_md_path: Path, issue_url: str):
    """更新 T*.md frontmatter 的 github_issue 欄位"""
    content = task_md_path.read_text(encoding="utf-8")
    if re.search(r"^github_issue:\s*\S+", content, re.MULTILINE):
        content = re.sub(r"^github_issue:\s*\S+", f"github_issue: {issue_url}", content, flags=re.MULTILINE)
    else:
        lines = content.splitlines()
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip() == "---":
                insert_pos = i + 1
            if re.match(r"^---", line):
                break
        new_lines = lines[:insert_pos] + [f"github_issue: {issue_url}"] + lines[insert_pos:]
        content = "\n".join(new_lines)
    task_md_path.write_text(content, encoding="utf-8")


def sync_todos_to_github(dry_run: bool = False) -> list:
    """直接掃描 Tasks/ 下所有 T*.md，缺 GitHub Issue 則建立"""
    results = []
    tasks_dir = get_tasks_dir()
    if not tasks_dir.exists():
        print("❌ Tasks 目錄不存在")
        return results

    done_dir = tasks_dir / "_done"
    t_files = []
    for proj_dir in sorted(tasks_dir.iterdir()):
        if not proj_dir.is_dir() or proj_dir == done_dir:
            continue
        tasks_sub = proj_dir / "tasks"
        if not tasks_sub.exists():
            continue
        for tf in sorted(tasks_sub.glob("T*.md")):
            t_files.append((proj_dir.name, tf))

    print(f"\n🌐 GitHub Sync 模式：掃描 {len(t_files)} 個 T*.md...")

    for proj, tf in t_files:
        tid = tf.stem
        content = tf.read_text(encoding="utf-8")

        if re.search(r"^github_issue:\s*\S+", content, re.MULTILINE):
            print(f"  ⏭️  {proj}/{tid} — 已有 Issue，跳過")
            continue

        status_m = re.search(r"^status:\s*(.+)$", content, re.MULTILINE)
        status = status_m.group(1).strip().lower() if status_m else "pending"
        if status in ("done", "skip"):
            print(f"  ⏭️  {proj}/{tid} — status={status}，不建立 Issue")
            continue

        print(f"  → {proj}/{tid} — 建立 Issue...")
        if dry_run:
            print(f"     [DRY RUN] 將建立 Issue")
            results.append({"tid": tid, "issue_url": None, "added_to_board": False})
        else:
            r = sync_single_task_to_github(proj, tid, tf)
            results.append(r)

    return results


def main():
    parser = argparse.ArgumentParser(description="ideas2tasks executor")
    parser.add_argument("--no-spawn", action="store_true", help="只建立 tasks，不 spawn agents")
    parser.add_argument("--dry-run", action="store_true", help="乾跑模式")
    parser.add_argument("--sync-github", action="store_true", help="直接掃 T*.md 建立 GitHub Issue")
    args = parser.parse_args()

    if args.sync_github:
        print("🚀 executor.py — GitHub Sync 模式（直接讀 T*.md）")
        results = sync_todos_to_github(dry_run=args.dry_run)
        ok = sum(1 for r in results if r["issue_url"])
        print(f"\n✅ 完成：{ok}/{len(results)} 個 Issue 已建立/已存在")
        return

    print("🚀 executor.py 啟動")
    print(f"  讀取狀態: {STATUS_FILE}")

    status = load_status()
    print(f"  待處理 ideas: {status.get('total_actionable', 0)}")

    created = create_tasks_from_status(status, args.dry_run)

    if args.dry_run:
        print("\n[DRY RUN] 以下 tasks 將被建立：")
        for c in created:
            print(f"  {c['project']}/T{c['task_num']:03d} → {c['assignee']}")
        return

    report = build_telegram_report(created)
    print("\n" + report)

    exec_status = {
        "timestamp": datetime.now().isoformat(),
        "created_count": len(created),
        "created": created,
    }
    exec_file = Path(__file__).parent.parent / "scripts" / "executor_status.json"
    exec_file.parent.mkdir(parents=True, exist_ok=True)
    exec_file.write_text(json.dumps(exec_status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 狀態已寫入 executor_status.json")

    if not args.no_spawn and created:
        print("\n💡 提示：使用以下指令 spawn agents：")
        for c in created:
            agent_id = c["agent_id"]
            print(f"  sessions_spawn(agentId=\"{agent_id}\", task=\"執行 {c['project']}/T{c['task_num']:03d}: {c['title'][:40]}\")")


if __name__ == "__main__":
    main()
