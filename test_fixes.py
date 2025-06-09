#!/usr/bin/env python3
"""
測試修正後的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anti_fraud_clean_app import detect_fraud_with_chatgpt, expand_short_url
import time

def test_fixes():
    """測試修正後的功能"""
    print("測試修正後的功能...")
    print("=" * 60)
    
    # 測試1: tinyurl 展開和分析
    print("1. 測試 tinyurl 展開和分析")
    print("-" * 40)
    
    tinyurl_test = "https://tinyurl.com/yww5aasm"
    print(f"測試短網址: {tinyurl_test}")
    
    # 先測試展開功能
    original, expanded, is_short, success, title = expand_short_url(tinyurl_test)
    print(f"展開結果: {original} -> {expanded}")
    print(f"是短網址: {is_short}, 展開成功: {success}")
    print(f"頁面標題: {title}")
    print()
    
    # 測試完整分析
    print("🤖 完整詐騙分析...")
    start_time = time.time()
    result = detect_fraud_with_chatgpt(tinyurl_test, "測試用戶")
    end_time = time.time()
    
    print(f"分析時間: {end_time - start_time:.2f} 秒")
    
    if result["success"]:
        analysis = result["result"]
        print("📊 分析結果:")
        print(f"風險等級: {analysis.get('risk_level', '未知')}")
        print(f"詐騙類型: {analysis.get('fraud_type', '未知')}")
        print()
        print("📝 分析說明:")
        print(analysis.get('explanation', '無說明'))
    else:
        print("❌ 分析失敗:")
        print(result.get("message", "未知錯誤"))
    
    print()
    print("=" * 60)
    print()
    
    # 測試2: reurl.cc 展開
    print("2. 測試 reurl.cc 展開")
    print("-" * 40)
    
    reurl_test = "https://reurl.cc/9Rad8O"
    print(f"測試短網址: {reurl_test}")
    
    # 測試展開功能
    original, expanded, is_short, success, title = expand_short_url(reurl_test)
    print(f"展開結果: {original} -> {expanded}")
    print(f"是短網址: {is_short}, 展開成功: {success}")
    print(f"頁面標題: {title}")
    print()
    
    # 測試完整分析
    print("🤖 完整詐騙分析...")
    start_time = time.time()
    result = detect_fraud_with_chatgpt(reurl_test, "測試用戶")
    end_time = time.time()
    
    print(f"分析時間: {end_time - start_time:.2f} 秒")
    
    if result["success"]:
        analysis = result["result"]
        print("📊 分析結果:")
        print(f"風險等級: {analysis.get('risk_level', '未知')}")
        print(f"詐騙類型: {analysis.get('fraud_type', '未知')}")
        print()
        print("📝 分析說明:")
        print(analysis.get('explanation', '無說明'))
    else:
        print("❌ 分析失敗:")
        print(result.get("message", "未知錯誤"))
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    test_fixes() 