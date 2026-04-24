#!/usr/bin/env python3
"""
test_project_api.py — 測試 GitHub Projects v2 GraphQL API 各項功能

用於探索 API 限制，保留每次測試的結果作為參考。
"""

import subprocess, json, time, sys, os

# ─────────────────────────────────────────
# 工具函式
# ─────────────────────────────────────────

def gh_gql(query: str) -> dict:
    """執行 GraphQL query，失敗時印出錯誤並返回空 dict"""
    cmd = "gh api graphql --method POST --field 'query=" + query + "'"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    if not r.stdout.strip():
        print(f"[gh_gql] empty response, stderr: {r.stderr[:100]}")
        return {}
    try:
        d = json.loads(r.stdout)
        if "errors" in d:
            print(f"[gh_gql] GraphQL errors: {d['errors']}")
        return d
    except json.JSONDecodeError as e:
        print(f"[gh_gql] JSON decode error: {e}, output: {r.stdout[:100]}")
        return {}


def gh_run(cmd: str) -> subprocess.CompletedProcess:
    """執行 gh CLI 命令"""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)


# ─────────────────────────────────────────
# 測試 1：基本專案查詢（確認 auth）
# ─────────────────────────────────────────

def test_basic_auth():
    print("\n[TEST 1] 基本 auth + 專案查詢")
    d = gh_gql('{user{login}}')
    login = d.get("data", {}).get("user", {}).get("login", "")
    print(f"  ✅ Logged in as: {login}")
    return login


# ─────────────────────────────────────────
# 測試 2：查 Board items（不帶 content）
# ─────────────────────────────────────────

def test_board_items_simple(owner: str, project_num: int):
    print(f"\n[TEST 2] 查 Board items（無 content 欄位）")
    gql = (f"{{user(login:\"{owner}\"){{projectV2(number:{project_num})"
           f"{{items(first:50){{nodes{{id type}}}}}}}}}}")
    d = gh_gql(gql)
    try:
        items = d["data"]["user"]["projectV2"]["items"]["nodes"]
        print(f"  ✅ {len(items)} items found")
        for it in items[:3]:
            print(f"     - {it['id'][:20]}... type={it.get('type')}")
        return items
    except (KeyError, TypeError) as e:
        print(f"  ❌ Failed: {e}")
        return []


# ─────────────────────────────────────────
# 測試 3：查 Board items（帶 content{__typename}）
# ─────────────────────────────────────────

def test_board_items_with_typename(owner: str, project_num: int):
    print(f"\n[TEST 3] 查 Board items（帶 content{{__typename}}）")
    gql = (f"{{user(login:\"{owner}\"){{projectV2(number:{project_num})"
           f"{{items(first:50){{nodes{{id content{{__typename}}}}}}}}}}}")
    d = gh_gql(gql)
    if not d:
        print("  ❌ empty response — likely RCURLY or parsing error")
        return []
    try:
        items = d["data"]["user"]["projectV2"]["items"]["nodes"]
        print(f"  ✅ {len(items)} items found")
        for it in items[:3]:
            print(f"     - {it['id'][:20]}... type={it.get('content',{}).get('__typename')}")
        return items
    except (KeyError, TypeError) as e:
        print(f"  ❌ Failed: {e}, data={d}")
        return []


# ─────────────────────────────────────────
# 測試 4：查 Board items（帶完整 Issue content）
# ─────────────────────────────────────────

def test_board_items_with_issue(owner: str, project_num: int):
    print(f"\n[TEST 4] 查 Board items（帶 content{{...on Issue}}）")
    gql = (f"{{user(login:\"{owner}\"){{projectV2(number:{project_num})"
           f"{{items(first:50){{nodes{{id content{{__typename ... on Issue{{number title}}}}}}}}}}}}}}")
    d = gh_gql(gql)
    if not d:
        print("  ❌ empty response")
        return []
    try:
        items = d["data"]["user"]["projectV2"]["items"]["nodes"]
        print(f"  ✅ {len(items)} items found")
        for it in items[:3]:
            c = it.get("content") or {}
            print(f"     - {it['id'][:20]}... issue=#{c.get('number')} {c.get('title','')[:30]}")
        return items
    except (KeyError, TypeError) as e:
        print(f"  ❌ Failed: {e}, data keys={list(d.get('data',{}).keys())}")
        return []


# ─────────────────────────────────────────
# 測試 5：REST fallback — gh project item-get
# ─────────────────────────────────────────

def test_rest_item_get(owner: str, project_num: int, item_ids: list):
    print(f"\n[TEST 5] REST fallback — gh project item-get")
    if not item_ids:
        print("  ⏭️  No items provided")
        return

    item_id = item_ids[0]
    cmd = (f'gh project item-get {project_num} --owner {owner} '
           f'--format json --id {item_id}')
    r = gh_run(cmd)
    if r.returncode == 0:
        try:
            data = json.loads(r.stdout)
            print(f"  ✅ REST item-get 成功")
            print(f"     content: {json.dumps(data.get('content'), ensure_ascii=False)[:150]}")
        except json.JSONDecodeError:
            print(f"  ❌ JSON parse error: {r.stdout[:100]}")
    else:
        print(f"  ❌ {r.stderr[:100]}")


# ─────────────────────────────────────────
# 測試 6：addProjectV2ItemById 回傳值
# ─────────────────────────────────────────

def test_add_item_response(project_id: str, content_id: str):
    print(f"\n[TEST 6] addProjectV2ItemById 回傳值測試")
    gql = (f"mutation{{addProjectV2ItemById(input:{{projectId:\"{project_id}\","
           f"contentId:\"{content_id}\"}}){{clientMutationId}}}}")
    d = gh_gql(gql)
    try:
        payload = d["data"]["addProjectV2ItemById"]
        print(f"  回傳: {payload}")
        print(f"  clientMutationId is None: {payload.get('clientMutationId') is None}")
        print(f"  'projectV2Item' in payload: {'projectV2Item' in payload}")
        # 測試 projectV2Item 是否存在
        try:
            _ = payload["projectV2Item"]
            print("  ⚠️  projectV2Item 存在（預期外）")
        except KeyError:
            print("  ✅ projectV2Item 不存在（符合預期）")
    except (KeyError, TypeError) as e:
        print(f"  ❌ Failed: {e}, d={d}")


# ─────────────────────────────────────────
# 測試 7：Schema introspection
# ─────────────────────────────────────────

def test_schema_introspection(type_name: str):
    print(f"\n[TEST 7] Schema introspection — {type_name}")
    gql = (f"{{__type(name:\"{type_name}\"){{name fields{{name type{{name}}}}}}}}")
    d = gh_gql(gql)
    try:
        fields = d["data"]["__type"]["fields"]
        print(f"  ✅ {type_name} 有 {len(fields)} 個欄位:")
        for f in fields:
            print(f"     - {f['name']} ({f['type']['name']})")
    except (KeyError, TypeError) as e:
        print(f"  ❌ Failed: {e}")


# ─────────────────────────────────────────
# 執行所有測試
# ─────────────────────────────────────────

if __name__ == "__main__":
    OWNER = "openclawchen8-lgtm"
    PROJECT_NUM = 1
    # 從環境或直接指定 project ID（可在 GitHub Board URL 找到）
    PROJECT_ID = os.environ.get("GITHUB_PROJECT_ID", "PVT_xxx")
    # 測試用的 content_id（隨便一個 Issue node_id）
    TEST_CONTENT_ID = os.environ.get("TEST_CONTENT_ID", "IC_kwDOGQ")

    login = test_basic_auth()
    if not login:
        print("❌ Auth failed"); sys.exit(1)

    items_simple = test_board_items_simple(OWNER, PROJECT_NUM)
    items_typename = test_board_items_with_typename(OWNER, PROJECT_NUM)
    items_issue = test_board_items_with_issue(OWNER, PROJECT_NUM)

    # REST fallback test
    if items_simple:
        test_rest_item_get(OWNER, PROJECT_NUM, [items_simple[0]["id"]])

    # Add item response test
    if TEST_CONTENT_ID != "IC_kwDOGQ":
        test_add_item_response(PROJECT_ID, TEST_CONTENT_ID)

    # Schema introspection
    test_schema_introspection("AddProjectV2ItemByIdPayload")
    test_schema_introspection("DraftIssue")
    test_schema_introspection("AddProjectV2DraftIssueItemPayload")
