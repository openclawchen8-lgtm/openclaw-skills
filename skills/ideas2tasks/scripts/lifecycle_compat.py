#!/usr/bin/env python3
"""
向後兼容入口點 — 實際邏輯已遷移到 ideas2tasks/lifecycle.py
"""

import sys
from pathlib import Path

# 將父目錄加入 path（舊版行為）
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接調用新模組
if __name__ == "__main__":
    from ideas2tasks.lifecycle import main
    main()
