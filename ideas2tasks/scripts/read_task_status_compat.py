#!/usr/bin/env python3
"""
向後兼容入口點 — 實際邏輯已遷移到 ideas2tasks/read_task_status.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    from ideas2tasks.read_task_status import main
    main()
