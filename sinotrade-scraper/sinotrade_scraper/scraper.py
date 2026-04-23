"""
sinotrade_scraper/scraper.py - 核心抓取邏輯
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

from .config import get_config


# 個股報告識別 pattern（Company (Code TT)｜Title YYYYMMDD）
STOCK_REPORT_PATTERN = re.compile(r"^(.+?)\s*\((\d{4,5})\s*TT\)｜(.+?)\s*(\d{8})$")

# 噪音關鍵字（正文外的干擾文字）
NAV_NOISE = {
    "永豐投顧 SinoPac Inv.Service", "會員申請", "會員訂閱", "訂閱介紹",
    "研究報告", "永續ESG", "登入", "觀看收聽", "報告下載",
    "推薦更多", "關於永豐投顧", "最新公告", "羅素基金",
    "隱私權聲明", "客戶資料保密措施", "金融友善服務專區",
    "企業團網站", "永豐證券投資顧問股份有限公司",
    "SinoPac Securities Investment Service Corporation",
    "台北市忠孝西路一段80號14樓", "110年金管投顧新字第024號",
    "© 永豐投顧版權所有",
}
HEADER_NOISE = {
    "譜瑞-KY (4966 TT)｜毛利率承壓 20260423",
    "宏捷科 (8086 TT)｜2026 年獲利迎來歷史高峰 20260423",
    "聯亞 (3081 TT)｜訂單能見度已看到 2028 年 20260423",
}

# 正文截止關鍵字
CONTENT_END_MARKERS = ["登入會員，看更多", "登入會員", "看更多", "完整報告", "►"]


async def fetch_report_preview(page, guid: str) -> str:
    """
    訪問報告詳情頁，抓取「登入會員，看更多」之前的公開預覽文字。
    """
    config = get_config()
    article_url = f"{config['base_url']}Article/Inner/{guid}"
    
    await page.goto(article_url, timeout=15000)
    await page.wait_for_load_state("domcontentloaded", timeout=12000)
    await page.wait_for_timeout(2000)

    body = await page.locator("body").inner_text()
    lines = body.splitlines()

    # 過濾導航/頁尾噪音
    content_lines = []
    skip_tail = False
    for line in lines:
        stripped = line.strip()
        if any(m in stripped for m in CONTENT_END_MARKERS):
            skip_tail = True
        if skip_tail:
            continue
        if stripped in NAV_NOISE or stripped in HEADER_NOISE:
            continue
        if stripped and len(stripped) > 15:
            content_lines.append(stripped)

    raw = " ".join(content_lines)
    raw = re.sub(r"\s{2,}", " ", raw).strip()

    return raw if len(raw) > 50 else ""


async def fetch_reports_async():
    """用 async Playwright 抓取報告列表。"""
    config = get_config()
    reports = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=config["chrome_path"],
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = await browser.new_page()

        print(f"[抓取] 開啟 {config['base_url']}")
        await page.goto(config["base_url"], timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        # Hover「研究報告」觸發 dropdown
        await page.locator("text=研究報告").first.hover()
        await page.wait_for_timeout(2000)

        links = await page.query_selector_all("a")
        print(f"[抓取] 找到 {len(links)} 個連結")

        for link in links:
            try:
                text = (await link.inner_text()).strip()
                href = await link.get_attribute("href") or ""
                m = STOCK_REPORT_PATTERN.match(text)
                if m:
                    guid = href.rstrip("/").split("/")[-1]
                    reports.append({
                        "name": m.group(1).strip(),
                        "code": m.group(2),
                        "title": m.group(3).strip(),
                        "date": m.group(4),
                        "url": href,
                        "guid": guid,
                        "raw": text,
                    })
            except Exception:
                continue

        await browser.close()

    print(f"[抓取] 共找到 {len(reports)} 篇個股報告")
    return reports


async def enrich_reports_with_preview(reports: list) -> list:
    """為每篇報告抓取預覽摘要。"""
    config = get_config()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=config["chrome_path"],
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = await browser.new_page()

        for i, r in enumerate(reports):
            guid = r.get("guid") or r.get("url", "").split("/")[-1]
            if not guid:
                r["preview"] = ""
                continue
            try:
                print(f"[預覽] [{i+1}/{len(reports)}] 抓取 {r['code']} {r['name']}...")
                preview = await fetch_report_preview(page, guid)
                r["preview"] = preview
                if preview:
                    print(f"  → 預覽長度: {len(preview)} 字")
                else:
                    print(f"  → 無公開正文")
            except Exception as e:
                print(f"  → 預覽抓取失敗: {e}")
                r["preview"] = ""

        await browser.close()
    
    return reports


def load_history(history_file=None):
    """載入歷史記錄。"""
    if history_file is None:
        from .config import get_history_file
        history_file = get_history_file()
    
    if os.path.exists(history_file):
        try:
            with open(history_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {"reports": {}}


def save_history(history, history_file=None):
    """儲存歷史記錄。"""
    if history_file is None:
        from .config import get_history_file
        history_file = get_history_file()
    
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def find_new_reports(today_reports, history):
    """比對歷史記錄，找出新增報告。"""
    today = datetime.now().strftime("%Y-%m-%d")
    prev_urls = set()
    for date_key, reps in history.get("reports", {}).items():
        if date_key != today:
            for rep in reps:
                prev_urls.add(rep.get("url", ""))
    return [r for r in today_reports if r.get("url") not in prev_urls]


def _truncate(preview: str, max_chars: int = 200) -> str:
    """截斷預覽至 max_chars 字。"""
    if len(preview) <= max_chars:
        return preview
    return preview[:max_chars].rstrip() + "..."


def format_telegram_message(new_reports, today_disp: str) -> str:
    """格式化 Telegram 通知訊息。"""
    lines = [f"📊 <b>永豐投顧台股報告</b>｜{today_disp}\n"]
    lines.append(f"共 {len(new_reports)} 篇新報告\n")

    for r in new_reports:
        code = r.get("code", "")
        name = r.get("name", "")
        title = r.get("title", "")
        date_raw = r.get("date", "")
        date_fmt = f"{date_raw[:4]}.{date_raw[4:6]}.{date_raw[6:8]}" if len(date_raw) == 8 else date_raw
        url = r.get("url", "")
        preview = r.get("preview", "")

        lines.append(f"📊 <b>{name} ({code} TT)</b>")
        lines.append(f"📅 {date_fmt}｜個股脈動")
        lines.append(f"📝 {title}")

        if preview:
            lines.append(f"🔍 預覽：{_truncate(preview, 200)}")
        else:
            lines.append("🔍 預覽：（無公開摘要，請登入會員閱讀完整內容）")

        if url:
            lines.append(f"🔗 <a href=\"{url}\">閱讀報告</a>")

        lines.append("─" * 20)
        lines.append("")

    return "\n".join(lines)
