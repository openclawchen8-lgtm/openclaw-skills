#!/usr/bin/env python3
from __future__ import annotations
"""
ideas2tasks state_sync.py
狀態同步核心：Tasks/ 目錄 ↔ Idea 檔的雙向同步

重要設計原則：
- Tasks/ 是事實來源（task 檔的 Status: done 是 ground truth）
- Idea 檔的 task.N done 標記是輔助（lifecycle.py 依賴它做分類）
- 兩者必須同步：任一方變 done，另一方也要更新
"""

import re
from pathlib import Path

# ===== 路徑設定（與 executor/lifecycle 共用）=====
TASKS_DIR = Path("/Users/claw/Tasks")
IDEAS_DIR = Path("/Users/claw/Ideas")


# ===== 1. Status 讀取（正規化）=====

def read_task_status(task_file: Path) -> str:
    """
    讀取 task 檔的 Status，正規化輸出。
    忽略大小寫、emoji、前後空白。
    回傳: "pending" | "in-progress" | "done"
    """
    if not task_file.exists():
        return "pending"
    try:
        content = task_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            # 支援：**Status**: done / Status: done / status: done 等格式
            m = re.match(r'^\-?\s*(\*+\s*)?Status(\s*\*+)?\s*:\s*(.+)', stripped, re.IGNORECASE)
            if m:
                raw = re.sub(r'[\U00010000-\U0010ffff]', '', m.group(3).strip())
                # 去除行內註解（# 之後的內容）
                raw = raw.split('#')[0].strip()
                raw_lower = raw.lower()
                if raw_lower in ("done", "✅", "✅ done", "done ✅"):
                    return "done"
                if raw_lower in ("in-progress", "in progress", "progress", "🔄", "🔄 in-progress"):
                    return "in-progress"
                if raw_lower in ("pending", "todo", "待處理"):
                    return "pending"
                if raw_lower in ("skip", "skipped", "⏭️"):
                    return "skip"
    except Exception:
        pass
    return "pending"


def write_task_status(task_file: Path, status: str):
    """
    寫入 task 檔的 Status，統一格式。
    status: "pending" | "in-progress" | "done"
    """
    if not task_file.exists():
        return
    try:
        content = task_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        new_lines = []
        found = False
        for line in lines:
            stripped = line.strip()
            m = re.match(r'^(\-?\s*(\*+\s*)?Status(\s*\*+)?\s*:\s*)(.+)', stripped, re.IGNORECASE)
            if m:
                new_lines.append(f"- **Status**: {status}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            # Status 行不存在，插到基本資訊 block 之後
            result_lines = []
            inserted = False
            for line in lines:
                result_lines.append(line)
                if not inserted and "**Assignee**" in line:
                    result_lines.append(f"- **Status**: {status}")
                    inserted = True
            new_lines = result_lines if inserted else lines + [f"- **Status**: {status}"]
        task_file.write_text("\n".join(new_lines), encoding="utf-8")
    except Exception:
        pass


# ===== 2. 讀取 Tasks/ 目錄狀態 =====

def get_tasks_dir_status(project_name: str) -> dict:
    """
    掃描 /Users/claw/Tasks/{project}/tasks/，回傳每個 task 的狀態。
    回傳: { "T001": "done", "T002": "pending", ... }
    """
    tasks_dir = TASKS_DIR / project_name / "tasks"
    status = {}
    if not tasks_dir.exists():
        return status
    for f in sorted(tasks_dir.glob("T*.md")):
        num = f.stem  # "T001"
        status[num] = read_task_status(f)
    return status


# ===== 3. 雙向同步 =====

def _find_idea_file(project_name: str) -> Path | None:
    """根據專案名稱找 idea 檔（支援 dash/underscore 轉換）"""
    for stem in [project_name, project_name.replace("-", "_"), project_name.replace("_", "-")]:
        f = IDEAS_DIR / f"{stem}.txt"
        if f.exists():
            return f
    return None


def sync_idea_to_task_done(project_name: str) -> dict:
    """
    將 Tasks/ 目錄中 Status: done 的 tasks，回寫 idea 檔的 done 標記。
    例如：task.1 → task.1 done
    回傳: { "done": N, "skipped": M }
    """
    idea_file = _find_idea_file(project_name)
    if not idea_file:
        return {"done": 0, "skipped": 0, "reason": "idea file not found"}

    tasks_status = get_tasks_dir_status(project_name)
    done_tasks = [num for num, s in tasks_status.items() if s == "done"]
    if not done_tasks:
        return {"done": 0, "skipped": 0}

    content = idea_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    marked = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 匹配 task.N 但還沒標 done（排除 task.N done）
        m = re.match(r'^task\.(\d+)(\s+)(?!done)', stripped, re.IGNORECASE)
        if m:
            # 只有當這個 task.N 對應的 T### 在 Tasks/ 是 done 時才標
            # 簡化：用行號順序對應。假設 idea 檔的 task.N 按順序對應 T001, T002...
            task_n = int(m.group(1))
            t_num = f"T{task_n:03d}"
            if t_num in done_tasks:
                lines[i] = re.sub(r'(task\.\d+\s+)(?!done)', r'\1done ', lines[i], flags=re.IGNORECASE)
                marked += 1
    if marked > 0:
        idea_file.write_text("\n".join(lines), encoding="utf-8")
    return {"done": marked, "skipped": len(done_tasks) - marked}


def sync_task_to_idea_pending(project_name: str, task_num: int) -> bool:
    """
    當某個 task 從 done 改回 pending，反寫 idea 檔的 done 標記。
    task_num: 任務編號（如 1 → task.1 done → task.1）
    回傳是否成功。
    """
    idea_file = _find_idea_file(project_name)
    if not idea_file:
        return False
    content = idea_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    changed = False
    pattern = rf'^task\.({task_num})(\s+done\s+)'
    for i, line in enumerate(lines):
        if re.match(pattern, line.strip(), re.IGNORECASE):
            lines[i] = re.sub(r'(\s+)done(\s+)', r'\1\2', lines[i], flags=re.IGNORECASE)
            changed = True
    if changed:
        idea_file.write_text("\n".join(lines), encoding="utf-8")
    return changed


# ===== 4. 分類結果合併（lifecycle.py 用）=====

def merge_classify_with_tasks_status(classify_result: dict) -> dict:
    """
    接收 classify_idea 的結果，合併 Tasks/ 目錄的實際狀態。
    
    重要原則：
    - Tasks/ 目錄是 ground truth：task 檔 Status: done = 該任務已完成
    - Idea 檔的 task.N done 是輔助資訊
    - merge 只管 idea 檔能對應到的 tasks（按順序 T001↔task.1）
    - 但 done/pending/in-progress 統計要包含 Tasks/ 全部 tasks
    
    對應關係：idea 檔 task.N（N=1,2,...）→ Tasks/ T001, T002, ...
    超出 idea 檔 task 數量的 Tasks/ tasks → 視為獨立的額外任務
    """
    project_name = classify_result["project_name"]
    tasks_status = get_tasks_dir_status(project_name)
    r = dict(classify_result)

    if not tasks_status:
        # 沒有 Tasks/，直接用 idea 檔的判斷
        r["done_in_tasks"] = 0
        r["pending_in_tasks"] = 0
        r["in_progress_in_tasks"] = 0
        return r

    # 統計 Tasks/ 中各狀態（涵蓋所有 tasks）
    done_in_tasks = sum(1 for s in tasks_status.values() if s == "done")
    pending_in_tasks = sum(1 for s in tasks_status.values() if s == "pending")
    inprog_in_tasks = sum(1 for s in tasks_status.values() if s == "in-progress")

    r["done_in_tasks"] = done_in_tasks
    r["pending_in_tasks"] = pending_in_tasks
    r["in_progress_in_tasks"] = inprog_in_tasks

    # 從 tasks 列表移除已在 Tasks/ 為 done/in-progress 的任務
    # 按 task num 對應：classify tasks[i] → T{001+i:03d}
    idea_task_count = len(r["tasks"])
    merged_tasks = []
    for i, task in enumerate(r["tasks"]):
        t_num = f"T{i+1:03d}"
        task_status = tasks_status.get(t_num, "pending")
        if task_status == "pending":
            merged_tasks.append(task)
    r["tasks"] = merged_tasks

    # 計算剩餘的 pending tasks（idea 可對應的 + Tasks/ 中不在 idea 對應範圍內的）
    # 例如：idea 有 3 tasks (T001-T003)，但 Tasks/ 有 T013
    # merged tasks 已移除 done/in-progress，剩餘的加上 Tasks/ 的 extra pending
    idea_pending_remaining = len(merged_tasks)

    # Tasks/ 中超出 idea task 數量範圍的 tasks（T{idea_task_count+1} 以上）
    extra_pending = 0
    for t_num, status in tasks_status.items():
        m = re.match(r'T(\d+)', t_num)
        if m and int(m.group(1)) > idea_task_count and status == "pending":
            extra_pending += 1

    total_pending = idea_pending_remaining + extra_pending
    r["pending_count"] = total_pending
    r["total_actionable_tasks"] = total_pending
    r["idea_file"] = str(_find_idea_file(project_name) or "")
    r["_tasks_status"] = tasks_status
    r["_extra_pending"] = extra_pending

    return r


# ===== 5. 批量同步（executor 或 agent 完成後呼叫）=====

def on_task_done(project_name: str, task_num: int) -> dict:
    """
    當某個 task 標為 done，呼叫此函數確保雙向同步。
    1. 將 Tasks/ task 檔 Status 寫為 done（已由 agent 完成，此為保險）
    2. 回寫 idea 檔的 done 標記
    """
    task_file = TASKS_DIR / project_name / "tasks" / f"T{task_num:03d}.md"
    if task_file.exists():
        write_task_status(task_file, "done")

    idea_sync = sync_idea_to_task_done(project_name)
    return {
        "task_file_status": "done",
        "idea_marked": idea_sync.get("done", 0),
        "idea_skipped": idea_sync.get("skipped", 0),
    }


# ===== 6. 去重輔助（前置：比對工具函式）=====

# ===== 7. 去重輔助（executor.py 用）=====

import re as _re

def _normalize_title(title: str) -> str:
    """
    正規化標題：移除數字、特殊符號、空白，統一大小寫。
    用於跨 task 比對相似標題。
    例如：
      "T002 - 請檢查及修正 黃金存摺價格監控 的問題"
    → "請檢查及修正黃金存摺價格監控的問題"
    """
    t = title.strip()
    t = _re.sub(r'^T\d+\s*[-–—:]\s*', '', t)  # 移除 T001 - 前綴
    t = _re.sub(r'\d{4}[-/]\d{2}[-/]\d{2}', '', t)  # 移除日期
    t = _re.sub(r'https?://\S+', '', t)  # 移除 URL
    t = _re.sub(r'[^\w\u4e00-\u9fff]', '', t)  # 移除特殊符號
    t = _re.sub(r'\s+', '', t)  # 移除空白
    return t.lower()


def get_existing_titles(project_dir: Path | str) -> dict:
    """
    取得專案現有 tasks 的標題和描述。
    回傳 dict：
      - "exact_set": 原始標題集合
      - "norm_set":  正規化標題集合
      - "desc_norm_set": 正規化描述前 100 字元集合（防內容重複但標題不同）
    
    修正紀錄（2026-04-14）：
    舊版回傳 set，只存標題。
    新版回傳 dict，新增 desc_norm_set 做描述比對。
    """
    if isinstance(project_dir, str):
        project_dir = Path(project_dir)
    tasks_dir = project_dir / "tasks"

    result = {"exact_set": set(), "norm_set": set(), "desc_norm_set": set()}

    if not tasks_dir.exists():
        return result

    for f in sorted(tasks_dir.glob("T*.md")):
        try:
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            # 取標題行（# T001 - ...）
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("# T"):
                    m = _re.match(r'^#\s*T\d+\s*[-–—:]\s*(.+)', stripped)
                    if m:
                        title = m.group(1).strip()
                        result["exact_set"].add(title)
                        result["norm_set"].add(_normalize_title(title))
                    break
            
            # 取描述（## 描述 後的第一段）
            desc = _extract_description(content)
            if desc:
                result["desc_norm_set"].add(_normalize_title(desc[:100]))
        except Exception:
            pass

    return result


def _extract_description(content: str) -> str:
    """從 T*.md 內容提取描述段落。"""
    in_desc = False
    desc_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## 描述") or stripped.startswith("## 描"):
            in_desc = True
            continue
        if in_desc:
            if stripped.startswith("## ") or stripped.startswith("---"):
                break
            if stripped:
                desc_lines.append(stripped)
    return " ".join(desc_lines)


def is_title_duplicate(new_title: str, existing_set: set) -> bool:
    """
    檢查新標題是否與現有任務重複。
    用正規化比對，避免「T002 - xxx」vs「xxx」這類變體重複。
    """
    norm_new = _normalize_title(new_title)
    if norm_new in existing_set:
        return True
    return False


def should_skip_task(new_title: str, project_dir: Path | str, extra_norm_set: set = None, new_desc: str = "") -> tuple:
    """
    判斷是否應跳過（不建立）這個 task。
    回傳 (skip: bool, reason: str)
    
    策略：
    1. 標題完全一致 → 跳過
    2. 標題正規化後一致 → 跳過
    3. 描述前 100 字元正規化後一致 → 跳過（防標題截斷但內容相同）
    4. 相似度 > 0.85 → 跳過（警告）
    
    修正紀錄（2026-04-14）：
    新增第 3 層描述比對，防止標題被截斷但內容完全相同的重複。
    """
    existing = get_existing_titles(project_dir)
    if extra_norm_set:
        # 向下兼容：extra_norm_set 是舊的 set 格式
        existing["norm_set"] = existing["norm_set"] | extra_norm_set

    norm_new = _normalize_title(new_title)

    if new_title in existing["exact_set"]:
        return True, "標題完全一致"
    if norm_new in existing["norm_set"]:
        return True, "正規化後標題一致"
    
    # 第 3 層：描述比對
    if new_desc:
        norm_desc = _normalize_title(new_desc[:100])
        if norm_desc and norm_desc in existing["desc_norm_set"]:
            return True, "描述內容重複"

    # 相似度檢查（簡單）
    for existing_title in list(existing["exact_set"])[:20]:
        norm_ex = _normalize_title(existing_title)
        common = set(norm_new) & set(norm_ex)
        if len(common) >= max(len(norm_new), len(norm_ex)) * 0.8 and len(norm_new) > 10:
            return True, f"相似標題：「{existing_title[:30]}」"

    return False, ""


# ===== 8. 批量狀態格式統一（修復歷史 Status）=====

def normalize_all_task_statuses(project_name: str = None):
    """
    遍歷所有或指定專案的 task 檔，統一 Status 格式。
    修復：status: done（小寫）、Status: ✅ done（多 emoji）等問題。
    """
    if project_name:
        dirs = [TASKS_DIR / project_name]
    else:
        dirs = [d for d in TASKS_DIR.iterdir() if d.is_dir() and d.name != "_done" and d.name != "_inbox"]

    fixed = 0
    for proj_dir in dirs:
        tasks_dir = proj_dir / "tasks"
        if not tasks_dir.exists():
            continue
        for f in tasks_dir.glob("T*.md"):
            current = read_task_status(f)
            if current != "pending":
                write_task_status(f, current)
                fixed += 1
    return fixed


# ===== 9. Tasks/ 目錄掃描（lifecycle.py 待處理追蹤用）=====

def _read_task_title(task_file: Path) -> str:
    """讀取 task 檔的標題。
    支援兩種格式：
    1. Markdown 標題行：# T001 - 標題
    2. YAML frontmatter：title: 標題
    """
    try:
        content = task_file.read_text(encoding="utf-8")
        in_frontmatter = False
        for line in content.splitlines():
            stripped = line.strip()
            # YAML frontmatter
            if stripped == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                m = re.match(r'^title:\s*(.+)', stripped)
                if m:
                    return m.group(1).strip()
            # Markdown 標題行（非 frontmatter 區）
            if not in_frontmatter and stripped.startswith("# T"):
                m = re.match(r'^#\s*T\d+\s*[-–—:]\s*(.+)', stripped)
                if m:
                    return m.group(1).strip()
                return stripped.lstrip("# ").strip()
    except Exception:
        pass
    return task_file.stem


def scan_tasks_dir() -> list[dict]:
    """
    掃描 /Users/claw/Tasks/ 下所有專案，
    找出有 pending 或 in-progress 任務的專案。
    
    這是「待處理」的唯一事實來源。
    Idea 檔只負責初始建立，追蹤一律從 Tasks/。
    
    設計原則（2026-04-20 修正）：
    - Ideas → 單向 → 建立 tasks/專案，之後 idea 檔完成使命
    - 追蹤一律從 Tasks/ 目錄來，無需雙向同步
    - lifecycle.py 的「待處理」報表應從此函數取值
    """
    results = []

    if not TASKS_DIR.exists():
        return results

    for project_dir in sorted(TASKS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        if project_dir.name.startswith("_"):
            continue

        tasks_dir = project_dir / "tasks"
        if not tasks_dir.exists():
            continue

        pending_tasks = []
        in_progress_tasks = []
        done_count = 0
        skip_count = 0

        for task_file in sorted(tasks_dir.glob("T*.md")):
            status = read_task_status(task_file)
            title = _read_task_title(task_file)

            if status == "pending":
                pending_tasks.append({
                    "num": task_file.stem,
                    "title": title,
                    "file": str(task_file),
                })
            elif status == "in-progress":
                in_progress_tasks.append({
                    "num": task_file.stem,
                    "title": title,
                    "file": str(task_file),
                })
            elif status == "done":
                done_count += 1
            elif status == "skip":
                skip_count += 1

        if pending_tasks or in_progress_tasks:
            results.append({
                "project_name": project_dir.name,
                "pending_count": len(pending_tasks),
                "in_progress_count": len(in_progress_tasks),
                "done_count": done_count,
                "skip_count": skip_count,
                "pending_tasks": pending_tasks,
                "in_progress_tasks": in_progress_tasks,
            })

    return results


# ===== CLI 入口 =====
if __name__ == "__main__":
    import argparse, json, sys

    parser = argparse.ArgumentParser(description="state_sync.py CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_sync = sub.add_parser("sync", help="同步指定專案的 idea 檔")
    p_sync.add_argument("project", help="專案名稱（如 gold-monitor-issue）")

    p_on_done = sub.add_parser("on_done", help="task 標 done 時的同步鉤子")
    p_on_done.add_argument("project", help="專案名稱")
    p_on_done.add_argument("task_num", type=int, help="任務編號（1,2,...）")

    p_norm = sub.add_parser("normalize", help="統一所有 task 的 Status 格式")
    p_norm.add_argument("project", nargs="?", default=None, help="專案名稱（可省略=全部）")

    args = parser.parse_args()

    if args.cmd == "sync":
        result = sync_idea_to_task_done(args.project)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    elif args.cmd == "on_done":
        result = on_task_done(args.project, args.task_num)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    elif args.cmd == "normalize":
        fixed = normalize_all_task_statuses(args.project)
        print(json.dumps({"fixed": fixed}, ensure_ascii=False))
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)
