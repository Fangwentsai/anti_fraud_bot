#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import datetime

def check_potato_questions():
    """檢查土豆題庫的狀態和數量"""
    try:
        file_path = 'potato_game_questions.json'
        abs_path = os.path.abspath(file_path)
        
        print(f"[{datetime.datetime.now()}] 檢查土豆防詐機器人題庫")
        print(f"文件路徑: {abs_path}")
        print(f"文件大小: {os.path.getsize(file_path)/1024:.2f} KB")
        
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
        has_options_count = sum(1 for q in all_questions if 'options' in q and q['options'] and 'correct_option' in q)
        
        print("\n======== 土豆防詐機器人題庫統計 ========")
        print(f"頂層題目數量: {top_level_count}題")
        print(f"嵌套題目數量: {nested_count}題")
        print(f"整合後總題目數量: {total_questions}題")
        print(f"有預設選項的題目數量: {has_options_count}題")
        print("========================================")
        
        # 檢查是否有ID重複的問題
        ids = [q.get('id') for q in all_questions if 'id' in q]
        unique_ids = set(ids)
        if len(ids) != len(unique_ids):
            print(f"警告：發現重複的ID！總ID數：{len(ids)}，唯一ID數：{len(unique_ids)}")
            
        # 檢查是否有選項格式不正確的問題
        for q in all_questions:
            if 'options' in q and q['options']:
                if not isinstance(q['options'], list):
                    print(f"警告：題目ID:{q.get('id', '未知')}的選項格式不正確！")
                elif 'correct_option' in q and q['correct_option'] not in ['A', 'B', 'C']:
                    print(f"警告：題目ID:{q.get('id', '未知')}的正確答案不是A/B/C！答案是：{q['correct_option']}")
        
        return True
    except Exception as e:
        print(f"錯誤: {e}")
        return False

if __name__ == "__main__":
    # 檢查題庫時自動執行
    check_potato_questions() 