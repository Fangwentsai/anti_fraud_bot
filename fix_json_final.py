#!/usr/bin/env python3
import json
import re

# 讀取清理過註釋的文件
with open('fraud_detection_questions_fixed.json', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到最後一個問題並修復 - 這是最常見的JSON結構問題
pattern = r'\}\s*\]\s*\}'
match = re.search(pattern, content)
if match:
    # 文件末尾的結構應該是 }]} 而不是 }]}
    fixed_content = content[:match.start()] + '}]}' + content[match.end():]
else:
    fixed_content = content

# 嘗試解析修復後的JSON
try:
    json_data = json.loads(fixed_content)
    print("JSON格式檢查通過")
    
    # 如果解析成功，格式化並保存
    with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print("已成功修復並保存到fraud_detection_questions.json")
    
except json.JSONDecodeError as e:
    print(f"JSON解析錯誤: {e}")
    
    # 手動修復最常見的問題 - 缺少逗號
    if "Expecting ',' delimiter" in str(e):
        error_pos = e.pos
        fixed_content = fixed_content[:error_pos] + ',' + fixed_content[error_pos:]
        
        try:
            json_data = json.loads(fixed_content)
            print("第二次嘗試 - JSON格式檢查通過")
            
            # 如果解析成功，格式化並保存
            with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            print("已成功修復並保存到fraud_detection_questions.json")
            
        except json.JSONDecodeError as e2:
            print(f"第二次嘗試 - JSON解析錯誤: {e2}")
            
            # 顯示錯誤附近的內容
            error_line = e2.lineno
            lines = fixed_content.split('\n')
            start = max(0, error_line - 5)
            end = min(len(lines), error_line + 5)
            
            print(f"\n錯誤位置附近的內容 (行 {start+1} 到 {end}):")
            for i in range(start, end):
                prefix = ">> " if i == error_line - 1 else "   "
                print(f"{prefix}{i+1}: {lines[i] if i < len(lines) else ''}")
            
            with open('fraud_detection_questions_final_attempt.json', 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print("最終嘗試的文件已保存到fraud_detection_questions_final_attempt.json") 