#!/usr/bin/env python3
import json

# 創建一個空的JSON結構
empty_json = {
    "questions": []
}

# 保存到文件
with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
    json.dump(empty_json, f, indent=2)

print("已創建乾淨的JSON文件")

# 驗證
with open('fraud_detection_questions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print("JSON格式驗證成功") 