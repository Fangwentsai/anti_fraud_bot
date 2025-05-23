#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# 添加當前目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_safe_domains():
    """載入 safe_domains.json 文件"""
    try:
        with open('safe_domains.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ 無法載入 safe_domains.json: {e}")
        return None

def extract_all_domains(safe_domains_data):
    """從 safe_domains.json 中提取所有網域"""
    all_domains = []
    
    if not safe_domains_data or 'safe_domains' not in safe_domains_data:
        print("❌ safe_domains.json 格式錯誤")
        return []
    
    # 提取 safe_domains 中的所有網域
    for category, domains in safe_domains_data['safe_domains'].items():
        if isinstance(domains, dict):
            for domain in domains.keys():
                all_domains.append(domain)
        else:
            print(f"⚠️  類別 '{category}' 格式異常: {type(domains)}")
    
    # 提取 donation_domains 中的網域
    if 'donation_domains' in safe_domains_data:
        for domain in safe_domains_data['donation_domains'].keys():
            # 移除 https:// 前綴
            clean_domain = domain.replace('https://', '').replace('http://', '')
            all_domains.append(clean_domain)
    
    return all_domains

def get_app_safe_domains():
    """從主程式獲取安全網域列表"""
    try:
        # 導入主程式的函數和變數
        from anti_fraud_clean_app import load_safe_domains as app_load_safe_domains
        
        # 載入應用程式的安全網域列表
        app_safe_domains, app_donation_domains = app_load_safe_domains()
        
        return app_safe_domains, app_donation_domains
        
    except Exception as e:
        print(f"❌ 無法從主程式載入安全網域: {e}")
        return {}, {}

def main():
    print("🔍 開始檢查 safe_domains.json 中的所有網站...")
    print("=" * 60)
    
    # 載入 safe_domains.json
    safe_domains_data = load_safe_domains()
    if not safe_domains_data:
        return
    
    # 提取所有網域
    json_domains = extract_all_domains(safe_domains_data)
    print(f"📊 safe_domains.json 中總共有 {len(json_domains)} 個網域")
    
    # 從主程式獲取安全網域
    app_safe_domains, app_donation_domains = get_app_safe_domains()
    print(f"📊 主程式中載入了 {len(app_safe_domains)} 個安全網域和 {len(app_donation_domains)} 個贊助網域")
    print("=" * 60)
    
    # 統計結果
    safe_count = 0
    unsafe_count = 0
    
    unsafe_domains = []
    
    # 逐一檢查每個網域
    for i, domain in enumerate(json_domains, 1):
        print(f"[{i:3d}/{len(json_domains)}] 檢查: {domain}")
        
        # 檢查是否在主程式的安全網域中
        is_in_app_safe = domain in app_safe_domains
        is_in_app_donation = domain in app_donation_domains
        
        if is_in_app_safe or is_in_app_donation:
            if is_in_app_safe:
                print(f"    ✅ 在安全網域白名單中")
            if is_in_app_donation:
                print(f"    ✅ 在贊助網域列表中")
            safe_count += 1
        else:
            print(f"    ⚠️  不在主程式的白名單中")
            unsafe_count += 1
            unsafe_domains.append(domain)
    
    # 輸出統計結果
    print("\n" + "=" * 60)
    print("📈 檢查結果統計:")
    print(f"✅ 在白名單中: {safe_count} 個")
    print(f"⚠️  不在白名單中: {unsafe_count} 個")
    print(f"📊 總計: {len(json_domains)} 個")
    
    # 顯示問題網域
    if unsafe_domains:
        print("\n⚠️  不在主程式白名單中的網域:")
        for domain in unsafe_domains:
            print(f"  - {domain}")
    
    # 反向檢查：主程式中有但JSON中沒有的網域
    print("\n" + "=" * 60)
    print("🔄 反向檢查：主程式中有但 safe_domains.json 中沒有的網域")
    
    missing_in_json = []
    for domain in app_safe_domains.keys():
        if domain not in json_domains:
            missing_in_json.append(domain)
    
    for domain in app_donation_domains.keys():
        clean_domain = domain.replace('https://', '').replace('http://', '')
        if clean_domain not in json_domains:
            missing_in_json.append(domain)
    
    if missing_in_json:
        print(f"⚠️  主程式中有 {len(missing_in_json)} 個網域不在 safe_domains.json 中:")
        for domain in missing_in_json:
            print(f"  - {domain}")
    else:
        print("✅ 主程式中的所有網域都在 safe_domains.json 中")
    
    # 結論
    if unsafe_count == 0 and len(missing_in_json) == 0:
        print("\n🎉 完美！safe_domains.json 與主程式完全同步！")
    else:
        print(f"\n⚠️  發現 {unsafe_count + len(missing_in_json)} 個同步問題需要處理")

if __name__ == "__main__":
    main() 