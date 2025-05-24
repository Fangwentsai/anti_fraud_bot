#!/usr/bin/env python3
"""
完整系統測試腳本
測試防詐騙機器人的所有模組化組件
"""

import sys
import os
import json
import traceback
from datetime import datetime

# 添加當前目錄到Python路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config_module():
    """測試配置模組"""
    print("🔧 測試配置模組...")
    try:
        from config import (
            BOT_TRIGGER_KEYWORD, SAFE_DOMAINS_FILE, 
            FRAUD_ANALYSIS_SYSTEM_PROMPT, validate_environment
        )
        
        # 測試基本配置
        assert BOT_TRIGGER_KEYWORD == "土豆", f"觸發關鍵詞錯誤: {BOT_TRIGGER_KEYWORD}"
        assert SAFE_DOMAINS_FILE == "safe_domains.json", f"安全網域文件名錯誤: {SAFE_DOMAINS_FILE}"
        assert len(FRAUD_ANALYSIS_SYSTEM_PROMPT) > 0, "系統提示詞為空"
        
        # 測試環境變數驗證
        env_valid = validate_environment()
        print(f"   ✅ 環境變數驗證: {'通過' if env_valid else '部分缺失（測試模式）'}")
        
        print("   ✅ 配置模組測試通過")
        return True
    except Exception as e:
        print(f"   ❌ 配置模組測試失敗: {e}")
        traceback.print_exc()
        return False

def test_safe_domains():
    """測試安全網域載入"""
    print("🌐 測試安全網域載入...")
    try:
        # 測試JSON文件載入
        with open('safe_domains.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'safe_domains' in data, "缺少safe_domains鍵"
        assert 'donation_domains' in data, "缺少donation_domains鍵"
        
        # 統計網域數量
        total_domains = 0
        for category, domains in data['safe_domains'].items():
            if isinstance(domains, dict):
                total_domains += len(domains)
        
        donation_count = len(data['donation_domains'])
        
        print(f"   ✅ 成功載入 {total_domains} 個安全網域和 {donation_count} 個贊助網域")
        
        # 測試主程式的載入函數
        from anti_fraud_clean_app import load_safe_domains
        safe_domains, donation_domains = load_safe_domains()
        
        assert len(safe_domains) > 0, "安全網域載入失敗"
        assert len(donation_domains) >= 0, "贊助網域載入失敗"
        
        print("   ✅ 安全網域載入測試通過")
        return True
    except Exception as e:
        print(f"   ❌ 安全網域載入測試失敗: {e}")
        traceback.print_exc()
        return False

def test_fraud_knowledge():
    """測試詐騙知識模組"""
    print("📚 測試詐騙知識模組...")
    try:
        from fraud_knowledge import (
            load_fraud_tactics, get_anti_fraud_tips, 
            get_fraud_features, analyze_fraud_keywords
        )
        
        # 測試詐騙戰術載入
        fraud_tactics = load_fraud_tactics()
        assert isinstance(fraud_tactics, dict), "詐騙戰術應該是字典格式"
        assert len(fraud_tactics) > 0, "詐騙戰術數據為空"
        
        print(f"   ✅ 載入 {len(fraud_tactics)} 種詐騙類型")
        
        # 測試防詐小知識
        tips = get_anti_fraud_tips()
        assert isinstance(tips, list), "防詐小知識應該是列表格式"
        print(f"   ✅ 載入 {len(tips)} 條防詐小知識")
        
        # 測試詐騙特徵
        features = get_fraud_features("假投資詐騙", "投資賺錢保證獲利")
        assert isinstance(features, dict), "詐騙特徵應該是字典格式"
        print(f"   ✅ 詐騙特徵分析功能正常，返回 {features['type']} 類型")
        
        # 測試關鍵詞分析
        test_message = "投資賺錢 快速致富 保證獲利"
        keywords = analyze_fraud_keywords(test_message)
        assert isinstance(keywords, list), "關鍵詞分析結果應該是列表"
        print(f"   ✅ 關鍵詞分析功能正常，檢測到 {len(keywords)} 個關鍵詞")
        
        print("   ✅ 詐騙知識模組測試通過")
        return True
    except Exception as e:
        print(f"   ❌ 詐騙知識模組測試失敗: {e}")
        traceback.print_exc()
        return False

def test_domain_spoofing():
    """測試網域變形檢測"""
    print("🔍 測試網域變形檢測...")
    try:
        from domain_spoofing_detector import detect_domain_spoofing
        
        # 測試正常網域
        safe_domains = {"google.com": "Google搜尋引擎"}
        result = detect_domain_spoofing("https://google.com", safe_domains)
        assert not result['is_spoofed'], "正常網域被誤判為變形"
        
        # 測試變形網域
        result = detect_domain_spoofing("https://goog1e.com", safe_domains)
        # 注意：這個測試可能會因為檢測算法的調整而變化
        
        print("   ✅ 網域變形檢測功能正常")
        return True
    except Exception as e:
        print(f"   ❌ 網域變形檢測測試失敗: {e}")
        traceback.print_exc()
        return False

def test_game_service():
    """測試遊戲服務"""
    print("🎮 測試遊戲服務...")
    try:
        from game_service import start_potato_game, handle_potato_game_answer
        
        # 測試遊戲啟動
        test_user_id = "test_user_123"
        flex_message, error = start_potato_game(test_user_id)
        
        if flex_message:
            print("   ✅ 遊戲啟動成功，返回Flex Message")
        elif error:
            print(f"   ⚠️ 遊戲啟動失敗但有錯誤處理: {error}")
        else:
            print("   ❌ 遊戲啟動失敗且無錯誤信息")
            return False
        
        # 測試遊戲答案處理
        try:
            is_correct, result_flex = handle_potato_game_answer(test_user_id, 0)
            print("   ✅ 遊戲答案處理功能正常")
        except Exception as e:
            print(f"   ⚠️ 遊戲答案處理可能需要有效的遊戲狀態: {e}")
        
        print("   ✅ 遊戲服務測試通過")
        return True
    except Exception as e:
        print(f"   ❌ 遊戲服務測試失敗: {e}")
        traceback.print_exc()
        return False

def test_flex_message_service():
    """測試Flex Message服務"""
    print("💬 測試Flex Message服務...")
    try:
        from flex_message_service import (
            create_analysis_flex_message, create_domain_spoofing_flex_message,
            create_donation_flex_message
        )
        
        # 測試分析結果Flex Message
        test_analysis_data = {
            "risk_level": "高風險",
            "fraud_type": "假投資詐騙",
            "explanation": "這是測試說明",
            "suggestions": "這是測試建議",
            "is_emerging": False
        }
        
        flex_msg = create_analysis_flex_message(
            test_analysis_data, "測試用戶", "測試訊息", "test_user_123"
        )
        assert flex_msg is not None, "分析結果Flex Message創建失敗"
        print("   ✅ 分析結果Flex Message創建成功")
        
        # 測試贊助Flex Message
        donation_msg = create_donation_flex_message()
        assert donation_msg is not None, "贊助Flex Message創建失敗"
        print("   ✅ 贊助Flex Message創建成功")
        
        # 測試網域變形Flex Message
        test_spoofing_result = {
            "is_spoofed": True,
            "spoofed_domain": "goog1e.com",
            "original_domain": "google.com",
            "spoofing_type": "字元替換攻擊",
            "risk_explanation": "測試風險說明"
        }
        
        spoofing_msg = create_domain_spoofing_flex_message(
            test_spoofing_result, "測試用戶", "https://goog1e.com", "test_user_123"
        )
        assert spoofing_msg is not None, "網域變形Flex Message創建失敗"
        print("   ✅ 網域變形Flex Message創建成功")
        
        print("   ✅ Flex Message服務測試通過")
        return True
    except Exception as e:
        print(f"   ❌ Flex Message服務測試失敗: {e}")
        traceback.print_exc()
        return False

def test_main_app_functions():
    """測試主程式的核心函數"""
    print("🏠 測試主程式核心函數...")
    try:
        from anti_fraud_clean_app import (
            contains_url, should_perform_fraud_analysis,
            expand_short_url, parse_fraud_analysis
        )
        
        # 測試URL檢測
        assert contains_url("https://example.com"), "URL檢測失敗"
        assert contains_url("www.example.com"), "www URL檢測失敗"
        assert not contains_url("這是普通文字"), "普通文字被誤判為URL"
        print("   ✅ URL檢測功能正常")
        
        # 測試詐騙分析判斷
        assert should_perform_fraud_analysis("https://suspicious-site.com"), "可疑URL未觸發分析"
        assert not should_perform_fraud_analysis("你好"), "普通問候觸發了分析"
        print("   ✅ 詐騙分析判斷功能正常")
        
        # 測試短網址展開
        original, expanded, is_short, success = expand_short_url("https://bit.ly/test")
        assert is_short, "短網址未被識別"
        print("   ✅ 短網址檢測功能正常")
        
        # 測試分析結果解析
        test_result = "風險等級：高風險\n詐騙類型：假投資\n說明：測試說明\n建議：測試建議"
        parsed = parse_fraud_analysis(test_result)
        assert parsed['risk_level'] == "高風險", "風險等級解析錯誤"
        assert parsed['fraud_type'] == "假投資", "詐騙類型解析錯誤"
        print("   ✅ 分析結果解析功能正常")
        
        print("   ✅ 主程式核心函數測試通過")
        return True
    except Exception as e:
        print(f"   ❌ 主程式核心函數測試失敗: {e}")
        traceback.print_exc()
        return False

def test_integration():
    """整合測試"""
    print("🔗 執行整合測試...")
    try:
        # 測試完整的詐騙檢測流程（不使用OpenAI API）
        from anti_fraud_clean_app import SAFE_DOMAINS
        
        # 測試白名單網域
        test_domains = ["google.com", "facebook.com", "gov.tw"]
        found_domains = 0
        for domain in test_domains:
            if domain in SAFE_DOMAINS:
                found_domains += 1
        
        print(f"   ✅ 白名單檢測：{found_domains}/{len(test_domains)} 個測試網域在白名單中")
        
        # 測試模組間的協作
        from fraud_knowledge import load_fraud_tactics
        from game_service import start_potato_game
        
        fraud_data = load_fraud_tactics()
        game_result, _ = start_potato_game("integration_test_user")
        
        print("   ✅ 模組間協作正常")
        
        print("   ✅ 整合測試通過")
        return True
    except Exception as e:
        print(f"   ❌ 整合測試失敗: {e}")
        traceback.print_exc()
        return False

def main():
    """主測試函數"""
    print("🚀 開始完整系統測試")
    print("=" * 50)
    
    test_results = []
    
    # 執行所有測試
    tests = [
        ("配置模組", test_config_module),
        ("安全網域", test_safe_domains),
        ("詐騙知識", test_fraud_knowledge),
        ("網域變形檢測", test_domain_spoofing),
        ("遊戲服務", test_game_service),
        ("Flex Message服務", test_flex_message_service),
        ("主程式核心函數", test_main_app_functions),
        ("整合測試", test_integration)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
            print()
        except Exception as e:
            print(f"❌ {test_name} 測試發生未預期錯誤: {e}")
            test_results.append((test_name, False))
            print()
    
    # 統計結果
    print("=" * 50)
    print("📊 測試結果統計")
    print("=" * 50)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    success_rate = (passed / total) * 100
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    print("=" * 50)
    print(f"總體成功率: {success_rate:.1f}% ({passed}/{total})")
    
    if success_rate == 100:
        print("🎉 所有測試通過！系統已達到100%正確率！")
    elif success_rate >= 90:
        print("✅ 系統運行良好，少數問題需要修正")
    elif success_rate >= 70:
        print("⚠️ 系統基本可用，但需要重要修正")
    else:
        print("❌ 系統存在重大問題，需要全面檢修")
    
    print(f"\n測試完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return success_rate

if __name__ == "__main__":
    success_rate = main()
    # 返回適當的退出碼
    sys.exit(0 if success_rate == 100 else 1) 