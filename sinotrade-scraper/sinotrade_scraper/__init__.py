"""
sinotrade_scraper - 永豐投顧台股報告自動抓取系統
"""

from .config import get_config
from .scraper import fetch_reports_async, enrich_reports_with_preview
from .telegram import send_telegram

__version__ = "1.1.0"
__all__ = [
    "get_config",
    "fetch_reports_async",
    "enrich_reports_with_preview",
    "send_telegram",
]
