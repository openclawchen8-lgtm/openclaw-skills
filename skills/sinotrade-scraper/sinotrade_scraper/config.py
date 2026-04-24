"""
sinotrade_scraper/config.py - 配置管理模組
支援環境變數 + 配置文件雙重覆寫機制
"""

import json
import os
from pathlib import Path

# 配置優先級：
# 1. 環境變數（最高）
# 2. 配置文件 ~/.qclaw/sinotrade_config.json
# 3. 預設值（最低）

DEFAULT_CONFIG = {
    "chrome_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "history_file": "~/.qclaw/sinotrade_history.json",
    "telegram_config": "~/.qclaw/gold_monitor_config.json",
    "base_url": "https://scm.sinotrade.com.tw/",
}

CONFIG_FILE = Path.home() / ".qclaw" / "sinotrade_config.json"


def load_config_file():
    """載入配置文件（若存在）"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] 配置文件讀取失敗: {e}")
    return {}


def get_chrome_path():
    """取得 Chrome 可執行檔路徑"""
    # 1. 環境變數
    if os.environ.get("SINOTRADE_CHROME_PATH"):
        return os.environ["SINOTRADE_CHROME_PATH"]
    
    # 2. 配置文件
    config = load_config_file()
    if config.get("chrome_path"):
        return str(Path(config["chrome_path"]).expanduser())
    
    # 3. 預設值
    return DEFAULT_CONFIG["chrome_path"]


def get_history_file():
    """取得歷史記錄檔路徑"""
    # 1. 環境變數
    if os.environ.get("SINOTRADE_HISTORY_FILE"):
        return os.environ["SINOTRADE_HISTORY_FILE"]
    
    # 2. 配置文件
    config = load_config_file()
    if config.get("history_file"):
        return str(Path(config["history_file"]).expanduser())
    
    # 3. 預設值
    return str(Path(DEFAULT_CONFIG["history_file"]).expanduser())


def get_telegram_config():
    """取得 Telegram 配置檔路徑"""
    # 1. 環境變數
    if os.environ.get("SINOTRADE_TELEGRAM_CONFIG"):
        return os.environ["SINOTRADE_TELEGRAM_CONFIG"]
    
    # 2. 配置文件
    config = load_config_file()
    if config.get("telegram_config"):
        return str(Path(config["telegram_config"]).expanduser())
    
    # 3. 預設值（復用 gold_monitor_config.json）
    return str(Path(DEFAULT_CONFIG["telegram_config"]).expanduser())


def get_base_url():
    """取得基礎 URL"""
    # 1. 環境變數
    if os.environ.get("SINOTRADE_BASE_URL"):
        return os.environ["SINOTRADE_BASE_URL"]
    
    # 2. 配置文件
    config = load_config_file()
    if config.get("base_url"):
        return config["base_url"]
    
    # 3. 預設值
    return DEFAULT_CONFIG["base_url"]


# 模組級快取（避免重複載入）
_chrome_path = None
_history_file = None
_telegram_config = None
_base_url = None


def get_config():
    """取得完整配置（快取版本）"""
    global _chrome_path, _history_file, _telegram_config, _base_url
    
    if _chrome_path is None:
        _chrome_path = get_chrome_path()
        _history_file = get_history_file()
        _telegram_config = get_telegram_config()
        _base_url = get_base_url()
    
    return {
        "chrome_path": _chrome_path,
        "history_file": _history_file,
        "telegram_config": _telegram_config,
        "base_url": _base_url,
    }


if __name__ == "__main__":
    # 測試配置載入
    import json
    config = get_config()
    print(json.dumps(config, indent=2, ensure_ascii=False))
