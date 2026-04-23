"""
sinotrade_scraper.__main__ - CLI 入口點
用法：
  python3 -m sinotrade_scraper
  python3 -m sinotrade_scraper --telegram
  python3 -m sinotrade_scraper --help
"""

import asyncio
import sys
from datetime import datetime

from .scraper import (
    fetch_reports_async,
    enrich_reports_with_preview,
    load_history,
    save_history,
    find_new_reports,
    format_telegram_message,
)
from .telegram import send_telegram
from .config import get_history_file


async def async_main():
    send_notify = "--telegram" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
sinotrade_scraper - 永豐投顧台股報告自動抓取

用法：
  python3 -m sinotrade_scraper           # 抓取並存檔
  python3 -m sinotrade_scraper --telegram # 抓取 + 發 Telegram 通知
  python3 -m sinotrade_scraper --help     # 顯示幫助

環境變數（可覆寫配置）：
  SINOTRADE_CHROME_PATH    Chrome 可執行檔路徑
  SINOTRADE_HISTORY_FILE   歷史記錄檔路徑
  SINOTRADE_TELEGRAM_CONFIG Telegram 配置檔路徑
""")
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_disp = datetime.now().strftime("%Y.%m.%d")
    
    # 抓取報告列表
    reports = await fetch_reports_async()
    
    if not reports:
        print("[結果] 今日無個股報告")
        if send_notify:
            send_telegram(f"📊 永豐投顧 {today_disp}：今日無個股報告")
        return
    
    # 印出列表
    print(f"\n=== {today} 個股報告 ===")
    for r in reports:
        print(f"  {r['code']} {r['name']} | {r['title']}")
    
    # 增量比對
    history = load_history()
    new_reports = find_new_reports(reports, history)
    print(f"\n[增量] 新增報告: {len(new_reports)} 篇（共 {len(reports)} 篇）")
    
    # 為新報告抓預覽
    if new_reports and send_notify:
        print("\n[預覽] 開始抓取新報告預覽摘要...")
        new_reports = await enrich_reports_with_preview(new_reports)
    
    # 寫入歷史（不含 preview / guid 欄位）
    history["reports"][today] = [
        {k: v for k, v in r.items() if k not in ("preview", "guid")} for r in reports
    ]
    history["last_updated"] = datetime.now().isoformat()
    save_history(history)
    print(f"[存檔] 已寫入 {get_history_file()}")
    
    # Telegram 通知
    if send_notify and new_reports:
        msg = format_telegram_message(new_reports, today_disp)
        print("\n=== Telegram 預覽 ===")
        print(msg[:500])
        print("...")
        send_telegram(msg)
    elif send_notify and not new_reports:
        print("[Telegram] 無新報告，跳過通知")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
