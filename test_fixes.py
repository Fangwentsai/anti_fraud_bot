#!/usr/bin/env python3
"""
測試修復後的網域檢測邏輯
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from domain_spoofing_detector import detect_domain_spoofing
import json

def load_safe_domains():
    """載入安全網域列表"""
    try:
        with open('safe_domains.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('safe_domains', {})
    except Exception as e:
        print(f"載入安全網域失敗: {e}")
        return {}

def test_domain_detection():
    """測試網域檢測邏輯"""
    print("=== 測試網域變形檢測修復 ===\n")
    
    # 載入安全網域
    safe_domains = load_safe_domains()
    
    # 將嵌套的字典展平
    flat_safe_domains = {}
    for category, domains in safe_domains.items():
        if isinstance(domains, dict):
            flat_safe_domains.update(domains)
    
    print(f"載入了 {len(flat_safe_domains)} 個安全網域")
    
    # 測試案例
    test_cases = [
        {
            "name": "正常的安全網域 - www.shinshingas.com.tw",
            "input": "這是詐騙網站嗎 https://www.shinshingas.com.tw",
            "expected": False,
            "description": "應該被識別為安全網域，不是變形攻擊"
        },
        {
            "name": "正常的安全網域 - shinshingas.com.tw",
            "input": "這是詐騙網站嗎 https://shinshingas.com.tw",
            "expected": False,
            "description": "應該被識別為安全網域，不是變形攻擊"
        },
        {
            "name": "正常的安全網域 - www.twt.com.tw",
            "input": "這是詐騙網站嗎 www.twt.com.tw",
            "expected": False,
            "description": "應該被識別為安全網域，不是變形攻擊"
        },
        {
            "name": "正常的安全網域 - twt.com.tw",
            "input": "這是詐騙網站嗎 twt.com.tw",
            "expected": False,
            "description": "應該被識別為安全網域，不是變形攻擊"
        },
        {
            "name": "真正的變形攻擊 - google-search.com",
            "input": "這是詐騙網站嗎 https://google-search.com",
            "expected": True,
            "description": "應該被識別為變形攻擊"
        }
    ]
    
    print("\n=== 開始測試 ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"測試 {i}: {test_case['name']}")
        print(f"輸入: {test_case['input']}")
        print(f"預期: {'變形攻擊' if test_case['expected'] else '安全網域'}")
        
        result = detect_domain_spoofing(test_case['input'], flat_safe_domains)
        is_spoofed = result.get('is_spoofed', False)
        
        print(f"結果: {'變形攻擊' if is_spoofed else '安全網域'}")
        
        if is_spoofed == test_case['expected']:
            print("✅ 測試通過")
        else:
            print("❌ 測試失敗")
            if is_spoofed:
                print(f"   檢測到變形: {result.get('spoofed_domain')} 模仿 {result.get('original_domain')}")
                print(f"   變形類型: {result.get('spoofing_type')}")
        
        print(f"說明: {test_case['description']}")
        print("-" * 50)

def test_safe_domain_lookup():
    """測試安全網域查找邏輯"""
    print("\n=== 測試安全網域查找 ===\n")
    
    safe_domains = load_safe_domains()
    
    # 將嵌套的字典展平
    flat_safe_domains = {}
    for category, domains in safe_domains.items():
        if isinstance(domains, dict):
            flat_safe_domains.update(domains)
    
    test_domains = [
        "www.shinshingas.com.tw",
        "shinshingas.com.tw", 
        "www.twt.com.tw",
        "twt.com.tw"
    ]
    
    for domain in test_domains:
        if domain in flat_safe_domains:
            print(f"✅ {domain}: {flat_safe_domains[domain]}")
        else:
            print(f"❌ {domain}: 未找到")

if __name__ == "__main__":
    test_safe_domain_lookup()
    test_domain_detection() 