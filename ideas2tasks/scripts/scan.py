#!/usr/bin/env python3
"""
ideas2tasks scan.py
掃描 /Users/claw/Ideas/*.txt，回傳待處理 idea 檔案列表（排除 _done/ 和空檔案）
"""

import os
import sys
import json
from pathlib import Path


def scan_ideas(ideas_dir: str = "/Users/claw/Ideas") -> list[dict]:
    """
    掃描 Ideas 目錄，回傳候選 idea 檔案列表。
    
    規則：
    - 排除 _done/ 子目錄
    - 只處理 .txt 檔案
    - 跳過 0 bytes 空檔案
    - 依修改時間倒序排列（最新優先）
    """
    ideas_path = Path(ideas_dir)
    if not ideas_path.exists():
        print(json.dumps({"error": f"Ideas 目錄不存在: {ideas_dir}"}))
        return []

    results = []
    done_dir = ideas_path / "_done"

    for txt_file in sorted(ideas_path.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True):
        # 跳過 _done 目錄（不論是檔案還是目錄本身）
        if done_dir in txt_file.resolve().parents:
            continue

        # 跳過空檔案（0 bytes）
        if txt_file.stat().st_size == 0:
            continue

        content = txt_file.read_text(encoding="utf-8").strip()
        
        # 再次確認：讀取後為空也跳過
        if not content:
            continue

        results.append({
            "filename": txt_file.name,
            "path": str(txt_file.resolve()),
            "size": txt_file.stat().st_size,
            "modified": txt_file.stat().st_mtime,
            "content": content,
            "line_count": len(content.splitlines()),
        })

    return results


def main():
    ideas_dir = sys.argv[1] if len(sys.argv) > 1 else "/Users/claw/Ideas"
    ideas = scan_ideas(ideas_dir)
    
    print(json.dumps({
        "ideas_dir": ideas_dir,
        "count": len(ideas),
        "ideas": ideas
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
