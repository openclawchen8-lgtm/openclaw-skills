"""
sinotrade_scraper/telegram.py - Telegram 通知模組
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path


def load_telegram_config(config_path=None):
    """載入 Telegram 配置"""
    if config_path is None:
        from .config import get_telegram_config
        config_path = get_telegram_config()
    
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        token = cfg.get("telegram_bot_token") or cfg.get("telegram_token") or cfg.get("bot_token")
        chat_id = cfg.get("telegram_chat_id") or cfg.get("chat_id")
        return token, chat_id
    except Exception:
        return None, None


def send_telegram(message, config_path=None):
    """發送 Telegram 通知"""
    token, chat_id = load_telegram_config(config_path)
    if not token or not chat_id:
        print("[Telegram] 配置檔缺少 token/chat_id，跳過通知")
        return False
    
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data
        )
        urllib.request.urlopen(req, timeout=10)
        print("[Telegram] 通知已發送")
        return True
    except Exception as e:
        print(f"[Telegram] 發送失敗: {e}")
        return False


if __name__ == "__main__":
    # 測試發送
    send_telegram("📊 測試通知：sinotrade_scraper Telegram 模組正常運作")
