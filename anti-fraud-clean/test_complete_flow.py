#!/usr/bin/env python3
"""
測試完整的詐騙檢測流程
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

def simulate_fraud_detection(user_message):
    """模擬完整的詐騙檢測流程"""
    print(f"\n=== 模擬用戶輸入：{user_message} ===")
    
    # 載入安全網域
    safe_domains, donation_domains = load_safe_domains()
    
    # 1. 首先檢查網域變形攻擊
    spoofing_result = detect_domain_spoofing(user_message, safe_domains)
    if spoofing_result['is_spoofed']:
        print("🚨 檢測到網域變形攻擊！")
        print(f"   可疑網域: {spoofing_result['spoofed_domain']}")
        print(f"   模仿網域: {spoofing_result['original_domain']}")
        print(f"   攻擊類型: {spoofing_result['spoofing_type']}")
        return "高風險 - 網域變形攻擊"
    
    # 2. 檢查是否為白名單網域
    import re
    from urllib.parse import urlparse
    
    # 提取URL進行精確匹配
    url_pattern = re.compile(r'https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}[^\s]*')
    urls = url_pattern.findall(user_message)
    
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
            
            # 檢查是否完全匹配白名單網域
            if domain in normalized_safe_domains:
                original_domain, site_description = normalized_safe_domains[domain]
                print(f"✅ 檢測到安全網域: {domain}")
                print(f"   原始網域: {original_domain}")
                print(f"   網站描述: {site_description}")
                return "低風險 - 安全網域"
        except Exception as e:
            continue
    
    # 3. 如果沒有精確匹配，進行包含檢查
    for safe_domain in safe_domains.keys():
        if safe_domain in user_message:
            site_description = safe_domains.get(safe_domain, "台灣常見的可靠網站")
            print(f"✅ 檢測到安全網域（包含匹配）: {safe_domain}")
            print(f"   網站描述: {site_description}")
            return "低風險 - 安全網域（包含匹配）"
    
    print("⚠️ 未檢測到已知的安全網域，需要進一步分析")
    return "需要進一步分析"

def main():
    """主測試函數"""
    print("=== 完整詐騙檢測流程測試 ===")
    
    test_cases = [
        "這是詐騙網站嗎 https://www.shinshingas.com.tw",
        "這是詐騙網站嗎 https://shinshingas.com.tw", 
        "這是詐騙網站嗎 www.twt.com.tw",
        "這是詐騙網站嗎 twt.com.tw",
        "這是詐騙網站嗎 https://google-search.com",
        "這是詐騙網站嗎 https://pchome-24h.com.tw",
        "這是詐騙網站嗎 https://www.google.com",
        "這是詐騙網站嗎 https://unknown-site.com"
    ]
    
    for test_case in test_cases:
        result = simulate_fraud_detection(test_case)
        print(f"   結果: {result}")
        print("-" * 60)

if __name__ == "__main__":
    main() 