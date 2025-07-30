#!/usr/bin/env python3
import re
import json
from pathlib import Path

# 創建一個新的JSON數據結構
questions_data = {
    "questions": []
}

# 讀取原始文件
with open('fraud_detection_questions_backup.json', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 移除註釋
content = re.sub(r'//.*?($|\n)', '', content)

# 修復URL問題
content = re.sub(r'https:(?!\S)', 'https://example.com', content)
content = re.sub(r'http:(?!\S)', 'http://example.com', content)

# 移除所有控制字符
content = re.sub(r'[\x00-\x1F\x7F]', '', content)

# 拆分成單獨的問題
# 首先，找到開始和結束大括號
start_bracket = content.find('{"questions": [')
end_bracket = content.rfind('}')

if start_bracket == -1 or end_bracket == -1:
    print("無法找到JSON數據的開始或結束")
    exit(1)

# 提取問題數組的內容
questions_content = content[start_bracket + len('{"questions": ['):end_bracket-1]

# 嘗試拆分成單獨的問題對象
import re
question_pattern = r'\{\s*"id":\s*"[^"]*".*?correct_option[^}]*\}'
question_matches = re.findall(question_pattern, questions_content, re.DOTALL)

if not question_matches:
    print("無法找到任何問題")
    exit(1)

print(f"找到 {len(question_matches)} 個問題")

# 收集所有問題並嘗試解析
valid_questions = []
for i, q in enumerate(question_matches):
    try:
        # 嘗試解析單個問題
        q_fixed = q.strip().rstrip(',')
        question_data = json.loads('{' + q_fixed + '}')
        valid_questions.append(question_data)
    except json.JSONDecodeError as e:
        print(f"問題 #{i+1} 解析錯誤: {e}")
        print(f"問題內容: {q[:100]}...")
        continue

print(f"成功解析 {len(valid_questions)} 個問題")

# 創建新的完整JSON
questions_data["questions"] = valid_questions

# 保存新的JSON文件
with open('fraud_detection_questions.json', 'w', encoding='utf-8') as f:
    json.dump(questions_data, f, ensure_ascii=False, indent=2)

print("成功創建新的JSON文件: fraud_detection_questions.json")

# 驗證新文件
try:
    with open('fraud_detection_questions.json', 'r', encoding='utf-8') as f:
        json.load(f)
    print("成功驗證JSON格式正確!")
except json.JSONDecodeError as e:
    print(f"新文件仍有格式錯誤: {e}") 