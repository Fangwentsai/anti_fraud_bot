#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加當前目錄到Python路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 導入主程式中的expand_short_url函數
from anti_fraud_clean_app import expand_short_url

def test_main_short_url_expansion():
    """測試主程式中的短網址展開功能"""
    test_url = "https://cht.tw/x/7h92p"
    
    print(f"測試主程式中的短網址展開功能")
    print(f"原始短網址: {test_url}")
    
    # 調用主程式中的expand_short_url函數
    original_url, expanded_url, is_short_url, success, page_title = expand_short_url(test_url)
    
    print(f"展開結果:")
    print(f"  原始URL: {original_url}")
    print(f"  展開後URL: {expanded_url}")
    print(f"  是短網址: {is_short_url}")
    print(f"  展開成功: {success}")
    print(f"  頁面標題: {page_title}")
    
    if expanded_url != original_url:
        print(f"✅ 短網址成功展開！")
        print(f"   從 {original_url} 展開到 {expanded_url}")
        
        # 檢查是否展開到最終的中華電信官方網站
        if "vip.cht.com.tw" in expanded_url:
            print(f"✅ 成功展開到中華電信官方VIP網站！")
        else:
            print(f"⚠️  展開結果不是預期的中華電信官方網站")
    else:
        print(f"❌ 短網址展開失敗")

if __name__ == "__main__":
    test_main_short_url_expansion() 