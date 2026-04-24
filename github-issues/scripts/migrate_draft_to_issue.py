#!/usr/bin/env python3
"""
migrate_draft_to_issue.py
Draft Items → GitHub Issues Migration

用法:
  python3 migrate_draft_to_issue.py --owner openclawchen8-lgtm \\
      --repo openclaw-tasks --project-id PVT_xxx --dry-run

功能:
  1. 讀取本地 task markdown
  2. 建立 GitHub Issue（含正確 body，用 --body-file 避免換行問題）
  3. 拿 issue node_id
  4. 加入 Board（addProjectV2ItemById）
  5. 刪除舊 Draft Item（deleteProjectV2Item）

⚠️  實戰關鍵：
  - 用 gh_utils.gh_run / gh_utils.gh_gql（不用 list args）
  - 用 --body-file 寫 body（不用 --body 直接傳換行）
  - addProjectV2ItemById 成功時 clientMutationId 為 None
"""

import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gh_utils import (
    gh_run, gh_gql,
    get_issue_node_id, create_issue,
    add_issue_to_board, delete_board_item,
    read_task_md, build_issue_body, build_github_url,
    get_board_items,
)

# ─────────────────────────────────────────
# 解析引數
# ─────────────────────────────────────────

parser = argparse.ArgumentParser(description="Draft Items → GitHub Issues Migration")
parser.add_argument("--owner", required=True, help="GitHub owner (org or user)")
parser.add_argument("--repo", required=True, help="GitHub repo name")
parser.add_argument("--project-id", required=True, help="Board Project ID (PVT_xxx)")
parser.add_argument("--tasks-root", required=True,
                    help="本地 Tasks 根目錄（如 /Users/claw/Tasks）")
parser.add_argument("--dry-run", action="store_true", help="不實際執行，顯示將執行的命令")
parser.add_argument("--skip-delete", action="store_true",
                    help="跳過刪除舊 Draft Items")
parser.add_argument("--batch-size", type=int, default=10, help="每批處理的 task 數")
args = parser.parse_args()

# ─────────────────────────────────────────
# Step 1: 收集所有本地 task markdown
# ─────────────────────────────────────────

print(f"📂 掃描: {args.tasks_root}")
task_map = {}  # (proj, tid) -> issue_num (if already created)

for proj in os.listdir(args.tasks_root):
    tasks_dir = os.path.join(args.tasks_root, proj, "tasks")
    if not os.path.isdir(tasks_dir):
        continue
    for fname in os.listdir(tasks_dir):
        if not fname.endswith(".md") or fname.startswith("_"):
            continue
        tid = fname[:-3]  # 去掉 .md
        md_path = os.path.join(tasks_dir, fname)
        info = read_task_md(md_path)
        info["proj"] = proj
        info["tid"] = tid
        info["md_path"] = md_path
        info["github_url"] = build_github_url(
            args.owner, args.repo, proj, tid)
        task_map[(proj, tid)] = info

print(f"✅ 找到 {len(task_map)} 個 task 檔案")

# ─────────────────────────────────────────
# Step 2: 建立 GitHub Issues
# ─────────────────────────────────────────

print("\n📝 建立 GitHub Issues...")
ok_create = 0
issue_numbers = {}  # (proj, tid) -> issue_number

for (proj, tid), info in sorted(task_map.items()):
    title = f"[{proj}] {tid} {info['title']}"
    body = build_issue_body(
        title=info["title"],
        status=info["status"],
        github_url=info["github_url"],
        extra=f"*Board Migration {time.strftime('%Y-%m-%d')}*"
    )

    num = create_issue(
        args.owner, args.repo,
        title=title,
        body=body,
        dry_run=args.dry_run,
    )
    if num:
        issue_numbers[(proj, tid)] = num
        ok_create += 1
        print(f"  ✅ #{num} {proj}::{tid}")
    else:
        print(f"  ❌ {proj}::{tid}")

    if ok_create % args.batch_size == 0:
        time.sleep(1)

print(f"\n✅ 建立完成: {ok_create}/{len(task_map)}")

# ─────────────────────────────────────────
# Step 3: 加入 Board
# ─────────────────────────────────────────

print("\n📌 加入 Board...")
ok_add = 0
for (proj, tid), num in sorted(issue_numbers.items()):
    content_id = get_issue_node_id(args.owner, args.repo, num)
    if not content_id:
        print(f"  ⚠️  #{num}: 無法取得 node_id"); continue

    ok = add_issue_to_board(args.project_id, content_id)
    if ok:
        ok_add += 1
        print(f"  ✅ #{num} {proj}::{tid}")
    else:
        print(f"  ❌ #{num}: 加入 Board 失敗")
    time.sleep(0.3)

print(f"\n✅ Board 加入完成: {ok_add}/{len(issue_numbers)}")

# ─────────────────────────────────────────
# Step 4: 刪除舊 Draft Items
# ─────────────────────────────────────────

if args.skip_delete:
    print("\n⏭️  跳過刪除舊 Draft Items（--skip-delete）")
else:
    print("\n🗑️  刪除舊 Draft Items...")
    board_items = get_board_items(
        args.owner.replace("-", " ").split()[0],  # user login
        1,  # project number
        fields="id content{__typename ... on DraftIssue{id}}"
    )

    deleted = 0
    for item in board_items:
        content = item.get("content")
        if content and content.get("__typename") == "DraftIssue":
            item_id = item["id"]
            ok = delete_board_item(args.project_id, item_id)
            if ok:
                deleted += 1
                print(f"  ✅ 刪除 Draft: {item_id[:20]}...")
            else:
                print(f"  ❌ 刪除失敗: {item_id[:20]}...")
            time.sleep(0.3)

    print(f"\n✅ 刪除完成: {deleted} 個 Draft Items")

print("\n🎉 Migration 完成！")
