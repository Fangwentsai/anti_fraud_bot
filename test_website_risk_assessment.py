#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網站風險評估測試模組
測試網域分析功能的準確性
"""

import sys
import os
import json

# 添加當前目錄到Python路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 設置環境變數
os.environ['CWB_API_KEY'] = 'CWA-E3034BF2-AE4B-4D55-B6AA-1BDC01372CF7'
os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'test_token'
os.environ['LINE_CHANNEL_SECRET'] = 'test_secret'
os.environ['OPENAI_API_KEY'] = 'test_openai_key'

from anti_fraud_clean_app import detect_fraud_with_chatgpt
from domain_spoofing_detector import detect_domain_spoofing

def load_safe_domains():
    """載入安全網域列表"""
    try:
        with open('safe_domains.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            flattened_safe_domains = {}
            for category, domains in data['safe_domains'].items():
                if isinstance(domains, dict):
                    flattened_safe_domains.update(domains)
            return flattened_safe_domains
    except Exception as e:
        print(f"載入safe_domains.json失敗: {e}")
        return {}

def test_random_suspicious_domains():
    """測試5個隨機可疑網域"""
    print("=" * 60)
    print("🔍 測試隨機可疑網域")
    print("=" * 60)
    
    # 5個明顯可疑的隨機網域
    suspicious_domains = [
        "https://free-money-now.scamsite.com/get-rich-quick",
        "https://urgent-bank-verification.fake-site.net/login",
        "https://crypto-invest-guaranteed.scam123.org/signup", 
        "https://win-iphone-now.suspicious-domain.info/claim",
        "https://government-tax-refund.fake-gov.tw/verify"
    ]
    
    results = []
    for i, domain in enumerate(suspicious_domains, 1):
        print(f"\n📍 測試 {i}: {domain}")
        
        try:
            result = detect_fraud_with_chatgpt(f"這個網站安全嗎？{domain}", "測試用戶")
            
            if result["success"]:
                risk_level = result["result"]["risk_level"]
                fraud_type = result["result"]["fraud_type"]
                explanation = result["result"]["explanation"][:100] + "..."
                
                print(f"✅ 風險等級: {risk_level}")
                print(f"✅ 詐騙類型: {fraud_type}")
                print(f"✅ 說明: {explanation}")
                
                # 判斷是否正確識別為高風險
                is_correct = "高" in risk_level or "中" in risk_level
                results.append({
                    "domain": domain,
                    "risk_level": risk_level,
                    "fraud_type": fraud_type,
                    "is_correct": is_correct
                })
                
                print(f"🎯 識別結果: {'✅ 正確' if is_correct else '❌ 錯誤'}")
            else:
                print(f"❌ 分析失敗: {result['message']}")
                results.append({"domain": domain, "is_correct": False, "error": result["message"]})
                
        except Exception as e:
            print(f"❌ 測試過程發生錯誤: {e}")
            results.append({"domain": domain, "is_correct": False, "error": str(e)})
    
    return results

def test_safe_domains_variants():
    """測試5個從safe_domains變異的網域"""
    print("\n" + "=" * 60)
    print("🔍 測試safe_domains變異網域")
    print("=" * 60)
    
    safe_domains = load_safe_domains()
    
    # 選擇5個知名網域並創建變異版本
    base_domains = ["google.com", "facebook.com", "youtube.com", "gov.tw", "shopee.tw"]
    variant_domains = [
        "https://g00gle.com/search",  # google.com 變異
        "https://faceb00k.com/login", # facebook.com 變異
        "https://y0utube.com/watch",  # youtube.com 變異
        "https://g0v.tw/news",        # gov.tw 變異
        "https://sh0pee.tw/buy"       # shopee.tw 變異
    ]
    
    results = []
    for i, (variant, original) in enumerate(zip(variant_domains, base_domains), 1):
        print(f"\n📍 測試 {i}: {variant} (模仿 {original})")
        
        try:
            # 首先測試網域變形檢測
            spoofing_result = detect_domain_spoofing(variant, safe_domains)
            
            if spoofing_result['is_spoofed']:
                print(f"✅ 網域變形檢測: 檢測到變形攻擊")
                print(f"✅ 原始網域: {spoofing_result['original_domain']}")
                print(f"✅ 變形類型: {spoofing_result['spoofing_type']}")
                is_correct = True
            else:
                print(f"❌ 網域變形檢測: 未檢測到變形")
                # 再用一般詐騙檢測
                result = detect_fraud_with_chatgpt(f"這個網站安全嗎？{variant}", "測試用戶")
                
                if result["success"]:
                    risk_level = result["result"]["risk_level"]
                    is_correct = "高" in risk_level or "中" in risk_level
                    print(f"✅ 一般檢測風險等級: {risk_level}")
                else:
                    is_correct = False
                    print(f"❌ 檢測失敗: {result['message']}")
            
            results.append({
                "variant": variant,
                "original": original,
                "is_correct": is_correct,
                "spoofing_detected": spoofing_result['is_spoofed']
            })
            
            print(f"🎯 識別結果: {'✅ 正確' if is_correct else '❌ 錯誤'}")
            
        except Exception as e:
            print(f"❌ 測試過程發生錯誤: {e}")
            results.append({
                "variant": variant, 
                "original": original, 
                "is_correct": False, 
                "error": str(e)
            })
    
    return results

def test_legitimate_domains():
    """測試合法網域（應該被識別為安全）"""
    print("\n" + "=" * 60)
    print("🔍 測試合法網域")
    print("=" * 60)
    
    legitimate_domains = [
        "https://www.google.com/search?q=test",
        "https://www.facebook.com/",
        "https://www.gov.tw/",
        "https://shopee.tw/",
        "https://www.youtube.com/"
    ]
    
    results = []
    for i, domain in enumerate(legitimate_domains, 1):
        print(f"\n📍 測試 {i}: {domain}")
        
        try:
            result = detect_fraud_with_chatgpt(f"這個網站安全嗎？{domain}", "測試用戶")
            
            if result["success"]:
                risk_level = result["result"]["risk_level"]
                print(f"✅ 風險等級: {risk_level}")
                
                # 合法網域應該被識別為低風險
                is_correct = "低" in risk_level or "非詐騙" in result["result"]["fraud_type"]
                results.append({
                    "domain": domain,
                    "risk_level": risk_level,
                    "is_correct": is_correct
                })
                
                print(f"🎯 識別結果: {'✅ 正確' if is_correct else '❌ 錯誤'}")
            else:
                print(f"❌ 分析失敗: {result['message']}")
                results.append({"domain": domain, "is_correct": False})
                
        except Exception as e:
            print(f"❌ 測試過程發生錯誤: {e}")
            results.append({"domain": domain, "is_correct": False})
    
    return results

def main():
    """主測試函數"""
    print("🚀 開始網站風險評估測試")
    
    # 測試1: 隨機可疑網域
    suspicious_results = test_random_suspicious_domains()
    
    # 測試2: safe_domains變異網域
    variant_results = test_safe_domains_variants()
    
    # 測試3: 合法網域
    legitimate_results = test_legitimate_domains()
    
    # 統計結果
    print("\n" + "=" * 60)
    print("📊 測試結果統計")
    print("=" * 60)
    
    total_tests = len(suspicious_results) + len(variant_results) + len(legitimate_results)
    correct_count = (
        sum(1 for r in suspicious_results if r.get("is_correct", False)) +
        sum(1 for r in variant_results if r.get("is_correct", False)) +
        sum(1 for r in legitimate_results if r.get("is_correct", False))
    )
    
    accuracy = (correct_count / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"總測試數: {total_tests}")
    print(f"正確識別: {correct_count}")
    print(f"準確率: {accuracy:.1f}%")
    
    if accuracy >= 80:
        print("🎉 網站風險評估功能測試通過！")
        return True
    else:
        print("❌ 網站風險評估功能需要改進")
        return False

if __name__ == "__main__":
    main() 