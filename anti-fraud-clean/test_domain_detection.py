#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from domain_spoofing_detector import detect_domain_spoofing
import json

# 載入安全網域
def load_safe_domains():
    try:
        with open('safe_domains.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['safe_domains']
    except Exception as e:
        print(f"載入安全網域失敗: {e}")
        return {}

def test_domain(test_url, safe_domains):
    print(f"\n=== 測試網域: {test_url} ===")
    
    result = detect_domain_spoofing(test_url, safe_domains)
    
    if result['is_spoofed']:
        print(f"✅ 檢測到變形攻擊!")
        print(f"   原始網域: {result['original_domain']}")
        print(f"   可疑網域: {result['spoofed_domain']}")
        print(f"   攻擊類型: {result['spoofing_type']}")
        print(f"   風險說明: {result['risk_explanation'][:100]}...")
    else:
        print(f"❌ 未檢測到變形攻擊")
    
    return result

if __name__ == "__main__":
    print("=== 網域變形攻擊檢測測試 ===")
    
    # 載入安全網域
    safe_domains = load_safe_domains()
    print(f"已載入 {len(safe_domains)} 個安全網域")
    
    # 測試用戶提供的網域
    test_urls = [
        "https://www.ruten-tw.com.tw/m/",
        "apples.com/tw"
    ]
    
    for test_url in test_urls:
        test_domain(test_url, safe_domains)
    
    # 額外測試一些已知應該被檢測到的變形網域
    print("\n=== 額外測試已知變形網域 ===")
    additional_tests = [
        "google-search.com",
        "pchome-24h.com.tw", 
        "cht-tw.com.tw",
        "goog1e.com",
        "apple.com.tw"
    ]
    
    for test_url in additional_tests:
        test_domain(test_url, safe_domains) 