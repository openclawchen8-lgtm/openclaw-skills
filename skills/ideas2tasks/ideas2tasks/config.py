#!/usr/bin/env python3
"""
ideas2tasks/config.py
配置管理模組 — 外部化路徑配置

設計原則：
1. 優先讀取環境變數（IDEAS2TASKS_TASKS_DIR / IDEAS2TASKS_IDEAS_DIR）
2. 其次讀取配置檔（~/.qclaw/ideas2tasks_config.json）
3. 最後使用預設值（/Users/claw/Tasks, /Users/claw/Ideas）

配置檔格式：
{
  "tasks_dir": "/Users/claw/Tasks",
  "ideas_dir": "/Users/claw/Ideas",
  "telegram_config": "~/.qclaw/gold_monitor_config.json"
}
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# ===== 預設值（向後兼容）=====
DEFAULT_TASKS_DIR = Path("/Users/claw/Tasks")
DEFAULT_IDEAS_DIR = Path("/Users/claw/Ideas")
DEFAULT_CONFIG_FILE = Path.home() / ".qclaw" / "ideas2tasks_config.json"

# ===== 配置快取 =====
_config_cache: Optional[dict] = None


def _expand_path(path_str: str) -> Path:
    """展開 ~ 和環境變數"""
    return Path(os.path.expanduser(os.path.expandvars(path_str)))


def load_config(reload: bool = False) -> dict:
    """
    載入配置檔。
    
    Args:
        reload: 強制重新載入（忽略快取）
    
    Returns:
        配置字典
    """
    global _config_cache
    
    if _config_cache is not None and not reload:
        return _config_cache
    
    config = {}
    
    # 嘗試讀取配置檔
    config_file = Path(os.environ.get("IDEAS2TASKS_CONFIG_FILE", DEFAULT_CONFIG_FILE))
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass  # 配置檔損壞時使用預設值
    
    _config_cache = config
    return config


def get_tasks_dir() -> Path:
    """
    取得 Tasks 目錄路徑。
    
    優先順序：
    1. 環境變數 IDEAS2TASKS_TASKS_DIR
    2. 配置檔 tasks_dir
    3. 預設值 /Users/claw/Tasks
    """
    # 環境變數優先
    env_val = os.environ.get("IDEAS2TASKS_TASKS_DIR")
    if env_val:
        return _expand_path(env_val)
    
    # 配置檔次之
    config = load_config()
    if "tasks_dir" in config:
        return _expand_path(config["tasks_dir"])
    
    # 預設值
    return DEFAULT_TASKS_DIR


def get_ideas_dir() -> Path:
    """
    取得 Ideas 目錄路徑。
    
    優先順序：
    1. 環境變數 IDEAS2TASKS_IDEAS_DIR
    2. 配置檔 ideas_dir
    3. 預設值 /Users/claw/Ideas
    """
    # 環境變數優先
    env_val = os.environ.get("IDEAS2TASKS_IDEAS_DIR")
    if env_val:
        return _expand_path(env_val)
    
    # 配置檔次之
    config = load_config()
    if "ideas_dir" in config:
        return _expand_path(config["ideas_dir"])
    
    # 預設值
    return DEFAULT_IDEAS_DIR


def get_telegram_config_path() -> Path:
    """
    取得 Telegram 配置檔路徑。
    
    用於 lifecycle.py 發送通知。
    """
    config = load_config()
    telegram_config = config.get("telegram_config", "~/.qclaw/gold_monitor_config.json")
    return _expand_path(telegram_config)


# ===== 向後兼容：導出常量（但改為函數調用）=====
# 舊代碼可能直接引用 TASKS_DIR / IDEAS_DIR，這裡提供屬性訪問
class _PathAccessor:
    """延遲計算路徑（向後兼容舊代碼）"""
    
    @property
    def TASKS_DIR(self) -> Path:
        return get_tasks_dir()
    
    @property
    def IDEAS_DIR(self) -> Path:
        return get_ideas_dir()


# 導出給舊代碼使用
TASKS_DIR = _PathAccessor().TASKS_DIR
IDEAS_DIR = _PathAccessor().IDEAS_DIR
