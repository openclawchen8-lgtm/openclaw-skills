#!/usr/bin/env python3
"""
bulk_update_body.py — 批量更新 Issue body 內容

用法:
  # URL 置換（file:// → GitHub URL）
  python3 bulk_update_body.py --owner openclawchen8-lgtm --repo openclaw-tasks \
      --replace-urls

  # 指定 Issue 範圍
  python3 bulk_update_body.py --owner ... --repo ... --from 6 --to 46

  # dry-run（只顯示不執行）
  python3 bulk_update_body.py --owner ... --repo ... --dry-run
"""

import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gh_utils import gh_run, get_issue_node_id, replace_urls_in_body, update_issue_body

# ─────────────────────────────────────────

parser = argparse.ArgumentParser(description="批量更新 GitHub Issue body")
parser.add_argument("--owner", required=True)
parser.add_argument("--repo", required=True)
parser.add_argument("--from-num", type=int, default=1, help="起始 Issue 編號")
parser.add_argument("--to-num", type=int, default=999, help="結束 Issue 編號")
parser.add_argument("--replace-urls", action="store_true",
                    help="執行 URL 置換（file:// → GitHub URL）")
parser.add_argument("--old-prefix", default="file:///Users/claw/",
                    help="舊 URL 前綴")
parser.add_argument("--new-prefix",
                    default="https://github.com/openclawchen8-lgtm/openclaw-tasks/blob/main/",
                    help="新 URL 前綴")
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

# ─────────────────────────────────────────
# 收集要更新的 Issues
# ─────────────────────────────────────────

cmd = (f'gh issue list --repo {args.owner}/{args.repo} --state all --limit 100 '
       f'--json number --jq \'.[].number\'')
r = gh_run(cmd)
all_nums = sorted(int(x) for x in r.stdout.strip().split('\n') if x.strip())
target_nums = [n for n in all_nums if args.from_num <= n <= args.to_num]
print(f"目標 Issues: {target_nums[0]}-{target_nums[-1]} ({len(target_nums)} 個)")

# ─────────────────────────────────────────
# 批量更新
# ─────────────────────────────────────────

ok = 0
for num in target_nums:
    # 讀取當前 body
    r = gh_run(f'gh issue view {num} --repo {args.owner}/{args.repo} '
               f'--json body --jq .body')
    if r.returncode != 0:
        print(f"  ⚠️  #{num}: 讀取失敗"); continue

    old_body = r.stdout
    if args.replace_urls:
        # 置換 URL（local path → GitHub URL）
        new_body = old_body
        # 簡單置換：把 old_prefix 換成 new_prefix
        if args.old_prefix in new_body:
            # 從 local path 結構：/Users/claw/{proj}/tasks/{tid}.md
            # 轉成：new_prefix/{proj}/tasks/{tid}.md
            new_body = new_body.replace(args.old_prefix, args.new_prefix)

    if new_body == old_body:
        print(f"  ⏭️  #{num}: 無變化"); continue

    print(f"  📝 #{num}: 更新 body...")
    print(f"     舊: {old_body[:60].replace(chr(10), '|')}")
    print(f"     新: {new_body[:60].replace(chr(10), '|')}")

    if not args.dry_run:
        ok_ = update_issue_body(args.owner, args.repo, num, new_body)
        if ok_:
            ok += 1
            print(f"       ✅")
        else:
            print(f"       ❌")
    else:
        ok += 1  # dry-run 算成功

    time.sleep(0.3)
    if num % 10 == 0:
        time.sleep(0.5)

print(f"\n✅ 完成: {ok}/{len(target_nums)}")
