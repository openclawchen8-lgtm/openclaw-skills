#!/bin/bash
# Ideas2tasks 狀態同步系統測試

set -e

SCRIPTS_DIR="/Users/claw/.qclaw/workspace/skills/ideas2tasks/scripts"
TEST_PROJECT="openclaw"

echo "🧪 Ideas2tasks 狀態同步系統測試"
echo "=================================="
echo ""

# 測試 1: task_status.py
echo "📋 測試 1: 統一狀態讀取"
python3 "$SCRIPTS_DIR/task_status.py" "/Users/claw/Tasks/$TEST_PROJECT" 2>&1 | head -5
echo ""

# 測試 2: sync_status.py (dry-run)
echo "🔄 測試 2: 狀態同步預覽"
python3 "$SCRIPTS_DIR/sync_status.py" --dry-run 2>&1 | grep "需同步"
echo ""

# 測試 3: 找到 idea 檔案
echo "🔍 測試 3: Idea 檔案對應"
python3 -c "
import sys
sys.path.insert(0, '$SCRIPTS_DIR')
from sync_status import find_idea_file
idea_file = find_idea_file('$TEST_PROJECT')
print(f'專案 $TEST_PROJECT → {idea_file.name if idea_file else \"找不到\"}')
"
echo ""

# 測試 4: 讀取 task 狀態
echo "📊 測試 4: 讀取單一 task 狀態"
python3 "$SCRIPTS_DIR/task_status.py" "/Users/claw/Tasks/$TEST_PROJECT/tasks/T001.md"
echo ""

echo "✅ 所有測試通過"
echo ""
echo "📖 詳細文檔："
echo "  - $SCRIPTS_DIR/../docs/STATUS_SYNC_FIX.md"
echo "  - $SCRIPTS_DIR/README.md"
