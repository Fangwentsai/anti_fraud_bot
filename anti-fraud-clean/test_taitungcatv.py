#!/usr/bin/env python3
"""
測試 www.taitungcatv.com.tw 的檢測
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
from domain_spoofing_detector import detect_domain_spoofing

def load_safe_domains():
    """載入安全網域列表"""
    try:
        with open('safe_domains.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 扁平化分類的安全網域字典
            flattened_safe_domains = {}
            for category, domains in data['safe_domains'].items():
                if isinstance(domains, dict):
                    flattened_safe_domains.update(domains)
            
            return flattened_safe_domains, data['donation_domains']
    except Exception as e:
        print(f"載入安全網域失敗: {e}")
        return {}, {}

def test_taitungcatv():
    """測試 taitungcatv 檢測"""
    print("=== 測試 www.taitungcatv.com.tw 檢測 ===\n")
    
    # 載入安全網域
    safe_domains, donation_domains = load_safe_domains()
    
    # 檢查是否在白名單中
    target_domain = "www.taitungcatv.com.tw"
    if target_domain in safe_domains:
        print(f"✅ {target_domain} 在白名單中")
        print(f"   描述: {safe_domains[target_domain]}")
    else:
        print(f"❌ {target_domain} 不在白名單中")
    
    # 測試網域變形檢測
    test_message = "這是詐騙網站嗎 https://www.taitungcatv.com.tw"
    print(f"\n測試訊息: {test_message}")
    
    spoofing_result = detect_domain_spoofing(test_message, safe_domains)
    if spoofing_result['is_spoofed']:
        print("🚨 誤判為網域變形攻擊！")
        print(f"   可疑網域: {spoofing_result['spoofed_domain']}")
        print(f"   模仿網域: {spoofing_result['original_domain']}")
        print(f"   攻擊類型: {spoofing_result['spoofing_type']}")
    else:
        print("✅ 正確識別為安全網域")
    
    # 測試白名單匹配邏輯
    print(f"\n=== 測試白名單匹配邏輯 ===")
    
    import re
    from urllib.parse import urlparse
    
    # 提取URL進行精確匹配
    url_pattern = re.compile(r'https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}[^\s]*')
    urls = url_pattern.findall(test_message)
    print(f"提取的URLs: {urls}")
    
    # 創建標準化的安全網域列表（包含www和非www版本）
    normalized_safe_domains = {}
    for safe_domain, description in safe_domains.items():
        safe_domain_lower = safe_domain.lower()
        normalized_safe_domains[safe_domain_lower] = (safe_domain, description)
        
        # 添加www和非www版本
        if safe_domain_lower.startswith('www.'):
            normalized_safe_domains[safe_domain_lower[4:]] = (safe_domain, description)
        else:
            normalized_safe_domains['www.' + safe_domain_lower] = (safe_domain, description)
    
    # 檢查每個提取的URL
    for url in urls:
        # 標準化URL
        if not url.startswith(('http://', 'https://')):
            if url.startswith('www.'):
                url = 'https://' + url
            else:
                url = 'https://' + url
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            print(f"解析的網域: {domain}")
            
            # 檢查是否完全匹配白名單網域
            if domain in normalized_safe_domains:
                original_domain, site_description = normalized_safe_domains[domain]
                print(f"✅ 匹配成功: {domain} -> {original_domain}")
                print(f"   描述: {site_description}")
            else:
                print(f"❌ 未匹配: {domain}")
        except Exception as e:
            print(f"❌ URL解析失敗: {e}")

if __name__ == "__main__":
    test_taitungcatv() 