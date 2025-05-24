#!/bin/bash

# 部署腳本 - 確保正確安裝依賴
echo "🚀 開始部署防詐騙LINE Bot..."

# 檢查requirements.txt是否存在
if [ ! -f "requirements.txt" ]; then
    echo "❌ 錯誤: requirements.txt 不存在"
    exit 1
fi

echo "📦 安裝Python依賴..."
pip install -r requirements.txt

echo "🔍 檢查主程式文件..."
if [ ! -f "anti_fraud_clean_app.py" ]; then
    echo "❌ 錯誤: anti_fraud_clean_app.py 不存在"
    exit 1
fi

echo "✅ 部署準備完成！"
echo "🎯 啟動應用程式..."
python anti_fraud_clean_app.py 