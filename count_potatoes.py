#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

def count_all_potatoes():
    try:
        file_path = 'potato_game_questions.json'
        print(f"讀取文件: {os.path.abspath(file_path)}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 處理不同的JSON結構
        all_questions = []
        top_level_count = 0
        nested_count = 0
        
        if isinstance(data, dict) and "questions" in data:
            # 處理頂層questions
            top_questions = data.get("questions", [])
            top_level_count = len(top_questions)
            print(f"頂層題目數量: {top_level_count}")
            
            for i, q in enumerate(top_questions):
                # 檢查是否有嵌套的questions數組
                if isinstance(q, dict) and "questions" in q:
                    # 發現嵌套題目
                    nested_questions = q.get("questions", [])
                    nested_count += len(nested_questions)
                    print(f"在第{i+1}個題目中發現嵌套題目：{len(nested_questions)}題")
                    all_questions.extend(nested_questions)
                else:
                    # 將頂層題目添加到總題庫
                    all_questions.append(q)
        
        # 總結
        total_questions = len(all_questions)
        print("\n======== 題庫統計 ========")
        print(f"頂層題目數量: {top_level_count}題")
        print(f"嵌套題目數量: {nested_count}題")
        print(f"整合後總題目數量: {total_questions}題")
        print(f"有預設選項的題目數量: {sum(1 for q in all_questions if 'options' in q and q['options'] and 'correct_option' in q)}題")
        print("=========================")
        
        # 列出前三個題目
        if all_questions:
            print("\n前三個題目示例:")
            for i, q in enumerate(all_questions[:3]):
                print(f"{i+1}. ID:{q.get('id', '未知')}, 類型:{q.get('fraud_type', '未知')}")
        
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    count_all_potatoes() 