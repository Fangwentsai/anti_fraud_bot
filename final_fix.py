#!/usr/bin/env python3
import json
import re

# 從頭開始修復JSON
with open('fraud_detection_questions_backup.json', 'r', encoding='utf-8') as f:
    content = f.read()

# 移除所有註釋
content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)

# 處理URL和格式問題
content = re.sub(r'https:(?!\S)', 'https://', content)

# 處理JSON結構問題 - 添加缺少的逗號
content = re.sub(r'"correct_option": "C"\s*\n\s*\}(?=\s*\n\s*\})', '"correct_option": "C"\n      },', content)

# 寫入處理後的文件
with open('final_fixed.json', 'w', encoding='utf-8') as f:
    f.write(content)

print("已完成初步修復，保存到final_fixed.json")

# 嘗試驗證JSON
try:
    with open('final_fixed.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("JSON格式驗證成功!")
    
    # 格式化後保存到最終文件
    with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("已成功格式化並保存到fraud_detection_questions.json")
    
except json.JSONDecodeError as e:
    print(f"JSON格式仍有錯誤: {e}")
    
    # 更直接的方法 - 使用一個有效的JSON工具格式化
    import subprocess
    try:
        subprocess.run(["python3", "-c", "import json; content=open('final_fixed.json').read(); print(json.dumps(json.loads(content), ensure_ascii=False, indent=2))", ">", "fraud_detection_questions.json"], check=True, shell=True)
        print("使用系統命令完成格式化")
    except subprocess.CalledProcessError:
        print("系統命令格式化失敗，請手動檢查final_fixed.json文件") 