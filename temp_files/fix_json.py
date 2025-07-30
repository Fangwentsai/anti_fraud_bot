#!/usr/bin/env python3
import json
import re

# 讀取原始JSON文件
with open('fraud_detection_questions_backup.json', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 一行行處理，移除所有註釋
fixed_lines = []
for line in lines:
    # 如果行中有註釋標記，移除它
    if '// 假設的' in line:
        line = line.split('// 假設的')[0].rstrip() + '\n'
    fixed_lines.append(line)

# 將修復後的行寫入新文件
with open('fraud_detection_questions_fixed.json', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

# 嘗試驗證JSON是否有效
try:
    with open('fraud_detection_questions_fixed.json', 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    print("JSON格式檢查通過")
    
    # 如果解析成功，格式化並保存
    with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print("已成功修復並保存到fraud_detection_questions.json")
    
except json.JSONDecodeError as e:
    print(f"JSON解析錯誤: {e}")
    
    # 顯示錯誤附近的內容
    error_line = e.lineno
    with open('fraud_detection_questions_fixed.json', 'r', encoding='utf-8') as f:
        fixed_content = f.read()
    lines = fixed_content.split('\n')
    start = max(0, error_line - 5)
    end = min(len(lines), error_line + 5)
    
    print(f"\n錯誤位置附近的內容 (行 {start+1} 到 {end}):")
    for i in range(start, end):
        prefix = ">> " if i == error_line - 1 else "   "
        print(f"{prefix}{i+1}: {lines[i] if i < len(lines) else ''}")
    
    print("部分修復的文件已保存到fraud_detection_questions_fixed.json") 