#!/usr/bin/env python3
"""
模組化系統測試腳本
測試各個模組的功能是否正常
"""

import sys
import os

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config_module():
    """測試配置模組"""
    print("🧪 測試配置模組...")
    try:
        from config import BOT_TRIGGER_KEYWORD, OPENAI_MODEL, SAFE_DOMAINS_FILE
        print(f"✅ 觸發關鍵詞: {BOT_TRIGGER_KEYWORD}")
        print(f"✅ OpenAI 模型: {OPENAI_MODEL}")
        print(f"✅ 安全網域檔案: {SAFE_DOMAINS_FILE}")
        return True
    except Exception as e:
        print(f"❌ 配置模組測試失敗: {e}")
        return False

def test_fraud_knowledge_module():
    """測試防詐知識模組"""
    print("\n🧪 測試防詐知識模組...")
    try:
        from fraud_knowledge import get_anti_fraud_tips, load_fraud_tactics, analyze_fraud_keywords
        
        # 測試防詐小知識
        tip = get_anti_fraud_tips()
        print(f"✅ 防詐小知識: {tip[:50]}...")
        
        # 測試詐騙類型載入
        fraud_types = load_fraud_tactics()
        print(f"✅ 載入詐騙類型數量: {len(fraud_types)}")
        
        # 測試關鍵詞分析
        test_message = "投資穩賺不賠，保證獲利"
        keywords = analyze_fraud_keywords(test_message)
        print(f"✅ 關鍵詞分析結果: {len(keywords)} 個匹配類型")
        
        return True
    except Exception as e:
        print(f"❌ 防詐知識模組測試失敗: {e}")
        return False

def test_weather_service_module():
    """測試天氣服務模組"""
    print("\n🧪 測試天氣服務模組...")
    try:
        from weather_service import handle_weather_query, is_weather_related, get_supported_cities
        
        # 測試天氣詢問檢測
        weather_msg = "今天台北天氣如何？"
        is_weather = is_weather_related(weather_msg)
        print(f"✅ 天氣詢問檢測: '{weather_msg}' -> {is_weather}")
        
        # 測試支援城市
        cities = get_supported_cities()
        print(f"✅ 支援城市數量: {len(cities)}")
        
        # 測試天氣查詢
        weather_response = handle_weather_query(weather_msg, "測試用戶")
        if weather_response:
            print(f"✅ 天氣查詢回應: {weather_response[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ 天氣服務模組測試失敗: {e}")
        return False

def test_flex_message_service():
    """測試 Flex Message 服務"""
    print("\n🧪 測試 Flex Message 服務...")
    try:
        from flex_message_service import (
            create_analysis_flex_message, create_donation_flex_message
        )
        
        # 測試詐騙分析 Flex Message
        test_analysis_data = {
            "risk_level": "高",
            "fraud_type": "假交友投資詐騙",
            "explanation": "這是測試分析",
            "suggestions": "請保持警覺"
        }
        
        analysis_flex = create_analysis_flex_message(
            test_analysis_data, "測試用戶", "測試訊息"
        )
        print("✅ 詐騙分析 Flex Message 創建成功")
        
        # 測試贊助彩蛋 Flex Message
        donation_flex = create_donation_flex_message()
        print("✅ 贊助彩蛋 Flex Message 創建成功")
        
        return True
    except Exception as e:
        print(f"❌ Flex Message 服務測試失敗: {e}")
        return False

def test_game_service():
    """測試遊戲服務"""
    print("\n🧪 測試遊戲服務...")
    try:
        from game_service import start_potato_game, is_game_trigger, get_user_game_state
        
        # 測試遊戲觸發檢測
        game_msg = "玩土豆遊戲"
        is_trigger = is_game_trigger(game_msg)
        print(f"✅ 遊戲觸發檢測: '{game_msg}' -> {is_trigger}")
        
        # 測試開始遊戲
        test_user_id = "test_user_123"
        flex_message, error = start_potato_game(test_user_id)
        
        if flex_message:
            print("✅ 遊戲開始成功")
            
            # 檢查遊戲狀態
            game_state = get_user_game_state(test_user_id)
            if game_state:
                print("✅ 遊戲狀態記錄正常")
        else:
            print(f"⚠️ 遊戲開始失敗: {error}")
        
        return True
    except Exception as e:
        print(f"❌ 遊戲服務測試失敗: {e}")
        return False

def test_safe_domains_loading():
    """測試安全網域載入"""
    print("\n🧪 測試安全網域載入...")
    try:
        # 直接測試主程式的安全網域載入
        import anti_fraud_clean_app
        
        safe_domains = anti_fraud_clean_app.SAFE_DOMAINS
        donation_domains = anti_fraud_clean_app.DONATION_DOMAINS
        
        print(f"✅ 安全網域數量: {len(safe_domains)}")
        print(f"✅ 贊助網域數量: {len(donation_domains)}")
        
        # 測試一些知名網域
        test_domains = ["google.com", "facebook.com", "gov.tw"]
        for domain in test_domains:
            if domain in safe_domains:
                print(f"✅ 找到安全網域: {domain}")
            else:
                print(f"⚠️ 未找到網域: {domain}")
        
        return True
    except Exception as e:
        print(f"❌ 安全網域載入測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始模組化系統測試\n")
    
    tests = [
        ("配置模組", test_config_module),
        ("防詐知識模組", test_fraud_knowledge_module),
        ("天氣服務模組", test_weather_service_module),
        ("Flex Message 服務", test_flex_message_service),
        ("遊戲服務", test_game_service),
        ("安全網域載入", test_safe_domains_loading)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 測試通過")
            else:
                print(f"❌ {test_name} 測試失敗")
        except Exception as e:
            print(f"❌ {test_name} 測試異常: {e}")
        
        print("-" * 50)
    
    print(f"\n📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有模組測試通過！模組化系統運作正常。")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查相關模組。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 