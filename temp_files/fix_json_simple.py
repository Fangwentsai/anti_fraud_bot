#!/usr/bin/env python3
import json
import re

# 讀取原始JSON文件
with open('fraud_detection_questions_backup.json', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("開始修復JSON...")

# 處理URL問題 - 處理截斷的URL
content = re.sub(r'https:(?!\S)', 'https://example.com', content)
content = re.sub(r'http:(?!\S)', 'http://example.com', content)

# 移除所有註釋
content = re.sub(r'//.*?($|\n)', '', content)

# 移除所有非法控制字符
content = re.sub(r'[\x00-\x09\x0B\x0C\x0E-\x1F\x7F]', '', content)

# 修復常見的JSON結構問題
# 1. 最後一個項目後的逗號問題
content = re.sub(r'"correct_option": "C"\s*\n\s*\}(?=\s*\n\s*\])', '"correct_option": "C"\n      },', content)
content = re.sub(r'"correct_option": "A"\s*\n\s*\}(?=\s*\n\s*\])', '"correct_option": "A"\n      },', content)
content = re.sub(r'"correct_option": "B"\s*\n\s*\}(?=\s*\n\s*\])', '"correct_option": "B"\n      },', content)

# 確保最後一個數組項不帶逗號
content = re.sub(r',(\s*\n\s*\]\s*\n\s*\})', r'\1', content)

# 寫入修復後的文件
with open('fixed_with_simple.json', 'w', encoding='utf-8') as f:
    f.write(content)

print("基本修復完成，已保存到fixed_with_simple.json")

# 嘗試一種更直接的方法
try:
    # 使用正則表達式處理JSON
    # 1. 移除所有註釋
    content_clean = re.sub(r'//.*?($|\n)', '', content)
    # 2. 確保JSON結構正確，通過修復最後一個元素
    json_str = re.sub(r',\s*\]\s*\}$', ']}', content_clean)
    
    # 嘗試解析
    data = json.loads(json_str)
    print("JSON解析成功!")
    
    # 保存格式化後的JSON
    with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("成功修復並格式化JSON，已保存到fraud_detection_questions.json")

except json.JSONDecodeError as e:
    print(f"JSON仍有格式錯誤: {e}")
    
    # 嘗試使用字符串替換方法修復常見錯誤
    try:
        # 使用字符串操作修復
        with open('fraud_detection_questions_backup.json', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # 移除註釋
        clean_lines = []
        for line in lines:
            # 移除註釋
            if '//' in line:
                line = line.split('//')[0]
            # 修復URL
            if 'https:' in line and not 'https://' in line:
                line = line.replace('https:', 'https://example.com')
            clean_lines.append(line)
        
        # 手動修復JSON結構
        json_text = ''.join(clean_lines)
        # 替換控制字符
        json_text = re.sub(r'[\x00-\x1F\x7F]', '', json_text)
        
        # 寫入臨時文件
        with open('manually_cleaned.json', 'w', encoding='utf-8') as f:
            f.write(json_text)
        
        print("已保存手動清理的JSON到manually_cleaned.json")
        
        # 嘗試解析 - 如果成功就格式化並保存
        with open('manually_cleaned.json', 'r', encoding='utf-8') as f:
            json_content = f.read()
            # 移除最後可能存在的百分號
            if '%' in json_content[-10:]:
                json_content = json_content.rstrip('%\n ')
            # 確保花括號正確關閉
            if not json_content.rstrip().endswith('}'):
                json_content = json_content.rstrip() + '}'
            
            data = json.loads(json_content)
        
        print("成功解析手動清理的JSON!")
        # 保存格式化的JSON
        with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("成功修復並格式化JSON，已保存到fraud_detection_questions.json")
        
    except Exception as e2:
        print(f"手動修復嘗試失敗: {e2}")
        print("請嘗試使用專業JSON編輯器打開並修復文件") 