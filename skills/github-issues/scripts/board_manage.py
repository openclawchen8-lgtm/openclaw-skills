#!/usr/bin/env python3
"""
board_manage.py — GitHub Project Board 管理工具

用法:
  # 列出 Board 所有 items
  python3 board_manage.py --owner openclawchen8-lgtm --project-id PVT_xxx --list

  # 去重（刪除同 issue 的重複項目）
  python3 board_manage.py --owner openclawchen8-lgtm --project-id PVT_xxx --dedup

  # 刪除指定 item
  python3 board_manage.py --owner openclawchen8-lgtm --project-id PVT_xxx \\
      --delete PVTI_xxx

  # 查 Issue 在 Board 中的狀態
  python3 board_manage.py --owner openclawchen8-lgtm --project-id PVT_xxx \\
      --check-issue 6
"""

import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gh_utils import gh_gql, get_board_items, delete_board_item, gh_run

# ─────────────────────────────────────────

parser = argparse.ArgumentParser(description="GitHub Project Board 管理")
parser.add_argument("--owner", required=True)
parser.add_argument("--project-id", required=True)
parser.add_argument("--project-number", type=int, default=1)
parser.add_argument("--list", action="store_true", help="列出所有 Board items")
parser.add_argument("--dedup", action="store_true", help="去重（刪除重複 items）")
parser.add_argument("--delete", metavar="ITEM_ID", help="刪除指定 item")
parser.add_argument("--check-issue", type=int, metavar="NUM",
                    help="查某個 Issue 是否在 Board 中")
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

# ─────────────────────────────────────────
# 列出所有 Board items（用 REST 拿 content 詳細資訊）
# ─────────────────────────────────────────

def list_board_items_detailed(owner: str, project_id: str) -> list[dict]:
    """用 REST API 拿 board items 的詳細資訊"""
    # 先拿 items 清單
    gql = (f"{{user(login:\"{owner}\"){{projectV2(number:{args.project_number})"
           f"{{items(first:100){{nodes{{id}}}}}}}}}}")
    d = gh_gql(gql)
    if "errors" in d:
        print(f"GraphQL error: {d['errors']}")
        return []

    items = d["data"]["user"]["projectV2"]["items"]["nodes"]
    print(f"Board items: {len(items)}")

    # 拿每個 item 的詳細資訊
    result = []
    for item in items:
        item_id = item["id"]
        # 用 gh project item-get 取詳細資訊
        r = gh_run(
            f'gh project item-get {args.project_number} --owner {owner} '
            f'--format json --id {item_id}')
        if r.returncode == 0 and r.stdout.strip():
            try:
                result.append(json.loads(r.stdout))
            except:
                result.append({"id": item_id})
        time.sleep(0.2)
        print(f"  {item_id[:20]}... → {r.stdout[:80] if r.returncode==0 else r.stderr[:40]}")

    return result

# ─────────────────────────────────────────
# 去重邏輯
# ─────────────────────────────────────────

def dedup_board(project_id: str):
    """刪除同一 issue 的重複 board entries"""
    gql = (f"{{user(login:\"{args.owner}\"){{projectV2(number:{args.project_number})"
           f"{{items(first:100){{nodes{{id content{{__typename ... on Issue{{number}}}}}}}}}}}}}")
    d = gh_gql(gql)
    if "errors" in d:
        print(f"Error: {d['errors']}"); return

    items = d["data"]["user"]["projectV2"]["items"]["nodes"]
    seen = {}  # issue_number -> first_item_id
    to_delete = []

    for item in items:
        content = item.get("content") or {}
        num = content.get("number")
        item_id = item["id"]
        if num is None:
            print(f"  ? item {item_id[:20]}...: 無 content")
            continue
        if num not in seen:
            seen[num] = item_id
            print(f"  📌 #{num}: 保留 {item_id[:20]}...")
        else:
            to_delete.append(item_id)
            print(f"  🔁 #{num}: 刪除 {item_id[:20]}... (重複)")

    if not to_delete:
        print("✅ 無重複")
        return

    print(f"\n🗑️  將刪除 {len(to_delete)} 個重複 items...")
    if args.dry_run:
        print("[dry-run] 不實際刪除")
        return

    for item_id in to_delete:
        ok = delete_board_item(project_id, item_id)
        print(f"  {'✅' if ok else '❌'} {item_id[:20]}...")
        time.sleep(0.3)

    print(f"✅ 去重完成: 刪除 {len(to_delete)} 個")

# ─────────────────────────────────────────
# 執行
# ─────────────────────────────────────────

if args.list:
    items = list_board_items_detailed(args.owner, args.project_id)

elif args.dedup:
    dedup_board(args.project_id)

elif args.delete:
    print(f"刪除 item: {args.delete}")
    if args.dry_run:
        print("[dry-run]")
    else:
        ok = delete_board_item(args.project_id, args.delete)
        print(f"{'✅ 刪除成功' if ok else '❌ 刪除失敗'}")

elif args.check_issue:
    # 查某個 Issue 是否在 Board 中
    gql = (f"{{user(login:\"{args.owner}\"){{projectV2(number:{args.project_number})"
           f"{{items(first:100){{nodes{{id content{{__typename ... on Issue{{number}}}}}}}}}}}}}")
    d = gh_gql(gql)
    items = d.get("data", {}).get("user", {}).get("projectV2", {}).get("items", {}).get("nodes", [])
    found = [it for it in items
             if it.get("content", {}).get("number") == args.check_issue]
    print(f"Issue #{args.check_issue} 在 Board 中: {len(found)} 個")
    for it in found:
        print(f"  {it['id']}")
