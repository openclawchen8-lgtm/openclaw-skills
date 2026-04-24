#!/usr/bin/env python3
"""Markdown to PDF converter using pandoc + Chrome headless."""
import sys
import os
import subprocess
import shutil
import webbrowser

def main():
    if len(sys.argv) < 2:
        print("用法: python3 md_to_pdf.py <input.md> [output.pdf]", file=sys.stderr)
        sys.exit(1)

    input_md = os.path.abspath(sys.argv[1])

    if len(sys.argv) >= 3:
        output_pdf = os.path.abspath(sys.argv[2])
    else:
        output_pdf = os.path.splitext(input_md)[0] + ".pdf"

    output_dir = os.path.dirname(output_pdf)
    tmp_html = os.path.join("/tmp", os.path.basename(input_md).replace(".md", "_to_pdf.html"))

    # Check pandoc
    if not shutil.which("pandoc"):
        print("錯誤: pandoc 未安裝，請先執行: brew install pandoc", file=sys.stderr)
        sys.exit(1)

    # Check Chrome
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_path):
        print("錯誤: Google Chrome 未找到", file=sys.stderr)
        sys.exit(1)

    # Step 1: md → html
    try:
        subprocess.run(
            ["pandoc", input_md, "-o", tmp_html],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Pandoc 轉換失敗: {e.stderr.decode()}", file=sys.stderr)
        sys.exit(1)

    # Step 2: html → pdf (Chrome headless)
    file_url = f"file://{tmp_html}"
    try:
        result = subprocess.run(
            [
                chrome_path,
                "--headless",
                f"--print-to-pdf={output_pdf}",
                file_url,
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            # Chrome 出現 ERROR 但不一定是真的錯誤，檢查檔案是否存在
            if not os.path.exists(output_pdf):
                print(f"Chrome 轉換失敗: {stderr[:500]}", file=sys.stderr)
                sys.exit(1)
    except subprocess.TimeoutExpired:
        print("錯誤: Chrome 執行逾時", file=sys.stderr)
        sys.exit(1)

    print(f"✅ PDF 已產生: {output_pdf}")
    print(f"   大小: {os.path.getsize(output_pdf) / 1024:.0f} KB")

    # Open Finder and select the file
    subprocess.run(["open", "-R", output_pdf])

if __name__ == "__main__":
    main()
