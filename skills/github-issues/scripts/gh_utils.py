#!/usr/bin/env python3
"""
gh_utils.py — GitHub Projects v2 管理共用工具函式
固化實戰最佳實踐，避免重複踩坑
"""

import subprocess, json, time, re, os
from typing import Optional

# ─────────────────────────────────────────
# 1. 核心執行函式（重要！）
# ─────────────────────────────────────────

def gh_run(cmd: str, timeout: int = 15) -> subprocess.CompletedProcess:
    """
    執行 gh CLI 命令。

    ⚠️  必須用完整 command string + shell=True
    ❌ 錯誤：subprocess.run(['gh', 'issue', ...], shell=True)
    → 會把 ['gh', ...] 的第一個字元 'g' 當成命令執行
    ✅ 正確：subprocess.run('gh issue ...', shell=True, ...)
    """
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def gh_gql(query: str, timeout: int = 30) -> dict:
    """
    執行 GitHub GraphQL query。

    ⚠️  必須用 --method POST --field 'query=...'
    ❌ 錯誤：gh api graphql --field query=@file
    → 拿到 __schema 而非 user data
    ❌ 錯誤：--field query=@file 直接 pipe
    → RCURLY parsing error
    ✅ 正確：gh api graphql --method POST --field 'query={...}'
    """
    cmd = "gh api graphql --method POST --field 'query=" + query + "'"
    r = gh_run(cmd, timeout=timeout)
    if not r.stdout.strip():
        return {}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"[gh_gql] JSON decode error: {r.stdout[:100]}")
        return {}


# ─────────────────────────────────────────
# 2. Issue 操作
# ─────────────────────────────────────────

def get_issue_node_id(owner: str, repo: str, number: int) -> Optional[str]:
    """取得 Issue 的 node_id（用於 GraphQL mutations）"""
    cmd = f'gh api /repos/{owner}/{repo}/issues/{number} --jq .node_id'
    r = gh_run(cmd)
    if r.returncode == 0:
        return r.stdout.strip().strip('"')
    return None


def get_all_issue_numbers(owner: str, repo: str, state: str = "all", limit: int = 100) -> list[int]:
    """取得 repo 中所有 Issue 編號"""
    cmd = (f'gh issue list --repo {owner}/{repo} --state {state}'
           f' --limit {limit} --json number --jq \'.[].number\'')
    r = gh_run(cmd)
    if r.returncode != 0:
        return []
    return sorted(int(x) for x in r.stdout.strip().split('\n') if x.strip())


def create_issue(owner: str, repo: str, title: str, body: str,
                 labels: list = None, dry_run: bool = False) -> Optional[int]:
    """
    建立 GitHub Issue。
    ⚠️  body 換行問題：用 --body-file 寫入真實換行
    """
    title_esc = title.replace('"', '\\"')
    # 寫入 body file（避免 shell 換行問題）
    body_file = "/tmp/gh_issue_body_" + str(os.getpid()) + ".txt"
    with open(body_file, "w") as f:
        f.write(body)

    labels_arg = ""
    if labels:
        for lb in labels:
            labels_arg += f' --label "{lb}"'

    cmd = (f'gh issue create --repo {owner}/{repo}'
           f' --title "{title_esc}" --body-file {body_file}{labels_arg}')
    if dry_run:
        print(f"[dry-run] {cmd}")
        os.unlink(body_file)
        return None

    r = gh_run(cmd)
    os.unlink(body_file)

    if r.returncode == 0:
        # 從 output 抓 issue number
        m = re.search(r'/issues/(\d+)', r.stdout)
        return int(m.group(1)) if m else None
    print(f"[create_issue] error: {r.stderr[:80]}")
    return None


def update_issue_body(owner: str, repo: str, number: int, new_body: str,
                      dry_run: bool = False) -> bool:
    """更新 Issue body。⚠️ 用 --body-file 避免換行問題"""
    body_file = f"/tmp/gh_body_{number}.txt"
    with open(body_file, "w") as f:
        f.write(new_body)

    cmd = f'gh issue edit {number} --repo {owner}/{repo} --body-file {body_file}'
    if dry_run:
        print(f"[dry-run] {cmd}")
        os.unlink(body_file)
        return True

    r = gh_run(cmd)
    os.unlink(body_file)
    return r.returncode == 0


def replace_urls_in_body(body: str, url_map: dict) -> str:
    """批量置換 body 中的 URL"""
    new_body = body
    for old_url, new_url in url_map.items():
        new_body = new_body.replace(old_url, new_url)
    return new_body


# ─────────────────────────────────────────
# 3. Board (Project) 操作
# ─────────────────────────────────────────

def get_board_items(owner: str, project_number: int,
                    fields: str = "id") -> list[dict]:
    """
    取得 Board 上所有 items。
    ⚠️  content{...} 在複雜 query 中容易 RCURLY error
    → 改用 REST API 或分段查
    """
    gq = (f"{{user(login:\"{owner}\"){{projectV2(number:{project_number})"
          f"{{items(first:50){{nodes{{{fields}}}}}}}}}}}")
    d = gh_gql(gq)
    if "errors" in d:
        print(f"[get_board_items] GraphQL errors: {d['errors']}")
        return []
    try:
        return d["data"]["user"]["projectV2"]["items"]["nodes"]
    except (KeyError, TypeError):
        return []


def add_issue_to_board(owner: str, project_id: str, content_id: str) -> bool:
    """
    將 Issue 加入 Board。
    成功回傳：{"clientMutationId": null}
    → Python dict 中是 None，表示成功
    """
    gql = (f"mutation{{addProjectV2ItemById(input:{{projectId:\"{project_id}\","
           f"contentId:\"{content_id}\"}}){{clientMutationId}}}}")
    d = gh_gql(gql)
    cmi = d.get("data", {}).get("addProjectV2ItemById", {}).get("clientMutationId")
    return cmi is None  # None = 成功，否則失敗


def delete_board_item(project_id: str, item_id: str) -> bool:
    """從 Board 刪除 item"""
    gql = (f"mutation{{deleteProjectV2Item(input:{{projectId:\"{project_id}\","
           f"itemId:\"{item_id}\"}}){{clientMutationId}}}}")
    d = gh_gql(gql)
    cmi = d.get("data", {}).get("deleteProjectV2Item", {}).get("clientMutationId")
    return cmi is None


# ─────────────────────────────────────────
# 4. Task Markdown 解析
# ─────────────────────────────────────────

def read_task_md(path: str) -> dict:
    """
    解析 task markdown 檔，回傳結構化 dict。

    Expected format:
    ## 任務
    任務標題

    ## 狀態
    pending / in-progress / done / skipped

    ## 描述
    ...（可選）
    """
    if not os.path.exists(path):
        return {}

    with open(path) as f:
        raw = f.read()

    result = {"path": path, "raw": raw}

    # 標題
    m = re.search(r"^## (.+)$", raw, re.MULTILINE)
    result["title"] = m.group(1).strip() if m else ""

    # 狀態
    m = re.search(r"^status:\s*(.+)$", raw, re.MULTILINE | re.IGNORECASE)
    result["status"] = (m.group(1).strip().lower() if m else "pending")

    # 描述（取 ## 描述 到下一個 ## 之前）
    m = re.search(r"## 描述\n(.*?)(?=\n## |\Z)", raw, re.DOTALL)
    result["description"] = (m.group(1).strip()[:500] if m else "")

    # 檔案路徑
    m = re.search(r"file:///Users/claw/(.+?/tasks/T\d+\.md)", raw)
    result["local_path"] = ("/Users/claw/" + m.group(1)) if m else ""

    return result


def build_issue_body(title: str, status: str,
                     github_url: str, extra: str = "") -> str:
    """
    組建標準 Issue body。

    Args:
        title: 任務標題
        status: pending / in-progress / done / skipped
        github_url: GitHub blob URL
        extra: 額外內容（可選）
    """
    status_emoji = {
        "pending": "⏳ Pending",
        "in-progress": "🔄 In Progress",
        "done": "✅ Done",
        "skipped": "⏭️ Skipped",
    }.get(status.lower(), "❓ " + status)

    body = (
        "## 任務\n"
        f"{title}\n\n"
        "## 狀態\n"
        f"{status_emoji}\n\n"
        "## 檔案\n"
        f"{github_url}\n\n"
        "---\n"
        f"{extra}"
    ).strip()
    return body


def build_github_url(owner: str, repo: str,
                     proj: str, tid: str) -> str:
    """從 local path 建 GitHub blob URL"""
    return (f"https://github.com/{owner}/{repo}"
            f"/blob/main/{proj}/tasks/{tid}.md")
