#!/usr/bin/env python3
import json
import re

# 讀取原始文件
with open('fraud_detection_questions_backup.json', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 基本清理
# 1. 移除尾部的%字符
content = content.rstrip('%\n ')

# 2. 移除所有註釋
content = re.sub(r'//.*?($|\n)', '', content)

# 3. 修復URL問題
content = re.sub(r'https:(?!\S)', 'https://example.com', content)
content = re.sub(r'http:(?!\S)', 'http://example.com', content)

# 4. 移除所有控制字符
content = re.sub(r'[\x00-\x1F\x7F]', '', content)

# 直接嘗試解析JSON
try:
    data = json.loads(content)
    print("成功解析JSON!")
    
    # 保存格式化後的JSON
    with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("成功格式化並保存到fraud_detection_questions.json")
    
except json.JSONDecodeError as e:
    print(f"JSON解析錯誤: {e}")
    
    # 對文件進行更多清理
    # 1. 嘗試移除所有不可打印字符
    printable_content = ''.join(c for c in content if c.isprintable() or c.isspace())
    
    try:
        data = json.loads(printable_content)
        print("第二次嘗試成功!")
        
        with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("成功格式化並保存到fraud_detection_questions.json")
        
    except json.JSONDecodeError as e2:
        print(f"第二次嘗試仍然失敗: {e2}")
        
        # 最後嘗試 - 字符串替換方法
        # 先保存清理過的內容
        with open('cleaned_content.json', 'w', encoding='utf-8') as f:
            f.write(printable_content)
        
        print("已保存清理後的內容到cleaned_content.json")
        print("請手動檢查並修復文件")
        
        # 建議使用一些常見的JSON解析問題修復
        print("\n建議修復方法:")
        print("1. 檢查文件中是否有不匹配的引號")
        print("2. 確保所有的數組和對象都正確關閉")
        print("3. 檢查所有元素之間是否有正確的逗號分隔")
        print("4. 使用專業的JSON編輯器或在線工具格式化和驗證JSON") 