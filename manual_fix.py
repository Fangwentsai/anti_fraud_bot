#!/usr/bin/env python3

# 讀取文件
with open('fraud_detection_questions_fixed.json', 'r', encoding='utf-8') as f:
    content = f.read()

# 移除文件尾部的奇怪字符
if content.endswith('%\n\n'):
    content = content[:-3]  # 去掉最後的 %\n\n

# 確保文件末尾是正確的格式 }
if not content.strip().endswith('}'):
    content = content.rstrip() + '}'

# 寫入修復後的文件
with open('fraud_detection_questions_fixed2.json', 'w', encoding='utf-8') as f:
    f.write(content)

print("已手動修復文件結尾格式，保存到 fraud_detection_questions_fixed2.json")

# 嘗試驗證JSON格式
import json
try:
    with open('fraud_detection_questions_fixed2.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("JSON格式驗證成功!")
    
    # 格式化後保存到最終文件
    with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("已成功格式化並保存到最終文件 fraud_detection_questions.json")
    
except json.JSONDecodeError as e:
    print(f"JSON格式錯誤: {e}")
    # 顯示錯誤位置的內容
    with open('fraud_detection_questions_fixed2.json', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    error_line = e.lineno
    start = max(0, error_line - 5)
    end = min(len(lines), error_line + 5)
    
    print(f"\n錯誤位置附近的內容 (行 {start+1} 到 {end}):")
    for i in range(start, end):
        prefix = ">> " if i == error_line - 1 else "   "
        print(f"{prefix}{i+1}: {lines[i] if i < len(lines) else ''}") 