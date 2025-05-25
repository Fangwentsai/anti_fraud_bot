#!/usr/bin/env python3
import json

# 創建一個空的JSON結構
empty_json = {
    "questions": []
}

# 保存到文件
with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
    json.dump(empty_json, f, ensure_ascii=False, indent=2)

print("已創建一個空的但有效的JSON文件: fraud_detection_questions.json")
print("請手動將您的問題數據添加到這個文件中，或使用專業JSON工具修復原始文件。") 