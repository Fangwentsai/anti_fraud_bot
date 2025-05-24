#!/bin/bash

# 🔒 每日核心功能保護檢查腳本
# 用途：自動檢查防詐騙和天氣功能的完整性

echo "🔒 每日核心功能保護檢查 - $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================="

# 檢查Python環境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安裝"
    exit 1
fi

# 檢查核心文件是否存在
CORE_FILES=("anti_fraud_clean_app.py" "weather_service.py")
MISSING_FILES=()

for file in "${CORE_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "❌ 缺少核心文件: ${MISSING_FILES[*]}"
    echo "🆘 請立即恢復文件！"
    exit 1
fi

# 運行保護檢查
echo "🔍 運行核心功能檢查..."
python3 protect_core_functions.py

# 檢查結果
if [ $? -eq 0 ]; then
    echo "✅ 核心功能檢查通過"
    
    # 可選：推送到Git（如果有變更）
    if [ -n "$(git status --porcelain)" ]; then
        echo "📝 發現變更，建議檢查..."
        git status --short
    else
        echo "📋 沒有變更，系統穩定"
    fi
else
    echo "❌ 核心功能檢查失敗"
    echo "🆘 請檢查系統狀態！"
    exit 1
fi

echo "=================================================="
echo "🎯 每日檢查完成 - $(date '+%Y-%m-%d %H:%M:%S')"

# 可以添加到crontab中每日執行：
# 0 9 * * * cd /path/to/your/project && ./daily_protection_check.sh >> protection.log 2>&1 