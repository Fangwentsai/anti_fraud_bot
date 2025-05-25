#!/usr/bin/env python3
import json
import re

# 讀取上一步修復後的文件
with open('fixed_final.json', 'r', encoding='utf-8') as f:
    content = f.read()

print("開始最終修復...")

# 專門針對缺少逗號的問題
# 找到 ".com" 後面緊跟著 "explanation" 的位置，插入逗號
content = re.sub(r'\.com"\s+"explanation"', '.com",\n      "explanation"', content)

# 針對性處理3082位置附近的問題
if len(content) > 3081:
    part1 = content[:3081]
    part2 = content[3081:]
    if '",\n' not in part1[-5:] and '"explanation"' in part2[:20]:
        content = part1 + ',\n      ' + part2

# 保存修復後的內容
with open('final_fixed2.json', 'w', encoding='utf-8') as f:
    f.write(content)

print("最終修復完成，保存到final_fixed2.json")

# 嘗試解析JSON
try:
    with open('final_fixed2.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("JSON格式驗證成功!")
    
    # 保存格式化後的JSON
    with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("成功格式化並保存到fraud_detection_questions.json")
    
except json.JSONDecodeError as e:
    print(f"JSON解析仍有錯誤: {e}")
    print("請使用專業JSON編輯器手動修復文件。") 