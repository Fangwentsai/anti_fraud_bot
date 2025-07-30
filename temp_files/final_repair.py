#!/usr/bin/env python3
import json
import re

# 讀取原始文件
with open('fraud_detection_questions_backup.json', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("開始修復...")

# 1. 移除所有註釋
content = re.sub(r'//.*?($|\n)', '', content)

# 2. 修復文件尾部
content = content.rstrip('%\n ')
if not content.endswith('}'):
    content = content + '}'

# 3. 移除控制字符
content = re.sub(r'[\x00-\x1F\x7F]', '', content)

# 4. 修復URL問題 - 針對性處理
content = re.sub(r'https:(?!["/])', 'https://example.com"', content)
content = re.sub(r'http:(?!["/])', 'http://example.com"', content)

# 5. 查找並修復截斷的URL字符串 - 這是關鍵修復點
def fix_truncated_urls(match):
    url_part = match.group(1)
    return f'{url_part}"\n      "explanation"'

content = re.sub(r'(https?://[^"\s]+)(\s+)"explanation"', fix_truncated_urls, content)

# 特別處理第111行附近的問題
content = re.sub(r'(https?:)(\s+)"explanation"', r'\1//example.com"\n      "explanation"', content)

# 6. 修復JSON結構 - 處理缺少的逗號
content = re.sub(r'"correct_option": "([ABC])"\s*\n\s*\}(?=\s*\n\s*\{)', r'"correct_option": "\1"\n      },', content)

# 7. 確保數組中的最後一個項目沒有逗號
content = re.sub(r',(\s*\n\s*\]\s*\n\s*\})', r'\1', content)

# 將修復後的內容保存到文件
with open('fixed_final.json', 'w', encoding='utf-8') as f:
    f.write(content)

print("初步修復完成，保存到fixed_final.json")

# 針對特定問題的最後修復嘗試
try:
    with open('fixed_final.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("JSON格式驗證成功!")
    
    # 保存格式化後的JSON
    with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("成功格式化並保存到fraud_detection_questions.json")
    
except json.JSONDecodeError as e:
    print(f"JSON解析仍有錯誤: {e}")
    
    try:
        # 嘗試手動修復格式
        # 1. 從頭構建一個有效的JSON
        with open('fraud_detection_questions_backup.json', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # 構建一個新的JSON對象
        new_json = {
            "questions": []
        }
        
        # 將這個對象寫入文件
        with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
            json.dump(new_json, f, ensure_ascii=False, indent=2)
        
        print("已創建一個空的但有效的JSON文件。請手動將數據添加到這個文件中。")
        
    except Exception as e2:
        print(f"最終嘗試失敗: {e2}")
        print("請使用專業JSON編輯器修復文件。") 