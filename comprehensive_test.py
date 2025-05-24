#!/usr/bin/env python3
"""
防詐騙機器人完整功能測試腳本
測試所有核心功能是否正常運作
"""

import sys
import os
import json
import time
from typing import Dict, List, Any

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_section(title: str):
    """打印測試區段標題"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_test(test_name: str, status: str, details: str = ""):
    """打印測試結果"""
    status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{status_emoji} {test_name}: {status}")
    if details:
        print(f"   📝 {details}")

def test_basic_imports():
    """測試基本模組導入"""
    print_section("基本模組導入測試")
    
    tests = [
        ("config 模組", "config"),
        ("fraud_knowledge 模組", "fraud_knowledge"),
        ("weather_service 模組", "weather_service"),
        ("flex_message_service 模組", "flex_message_service"),
        ("game_service 模組", "game_service"),
        ("主程式模組", "anti_fraud_clean_app")
    ]
    
    passed = 0
    for test_name, module_name in tests:
        try:
            __import__(module_name)
            print_test(test_name, "PASS", f"成功導入 {module_name}")
            passed += 1
        except Exception as e:
            print_test(test_name, "FAIL", f"導入失敗: {e}")
    
    return passed, len(tests)

def test_configuration():
    """測試配置功能"""
    print_section("配置功能測試")
    
    try:
        from config import (
            BOT_TRIGGER_KEYWORD, OPENAI_MODEL, SAFE_DOMAINS_FILE,
            MAX_MESSAGE_LENGTH, WEATHER_KEYWORDS, GAME_TRIGGER_KEYWORDS
        )
        
        tests = [
            ("觸發關鍵詞", BOT_TRIGGER_KEYWORD == "土豆", f"關鍵詞: {BOT_TRIGGER_KEYWORD}"),
            ("OpenAI 模型", OPENAI_MODEL in ["gpt-3.5-turbo", "gpt-4"], f"模型: {OPENAI_MODEL}"),
            ("安全網域檔案", SAFE_DOMAINS_FILE == "safe_domains.json", f"檔案: {SAFE_DOMAINS_FILE}"),
            ("訊息長度限制", isinstance(MAX_MESSAGE_LENGTH, int), f"限制: {MAX_MESSAGE_LENGTH}"),
            ("天氣關鍵詞", len(WEATHER_KEYWORDS) > 0, f"關鍵詞數量: {len(WEATHER_KEYWORDS)}"),
            ("遊戲觸發詞", len(GAME_TRIGGER_KEYWORDS) > 0, f"觸發詞數量: {len(GAME_TRIGGER_KEYWORDS)}")
        ]
        
        passed = 0
        for test_name, condition, details in tests:
            if condition:
                print_test(test_name, "PASS", details)
                passed += 1
            else:
                print_test(test_name, "FAIL", details)
        
        return passed, len(tests)
        
    except Exception as e:
        print_test("配置載入", "FAIL", f"錯誤: {e}")
        return 0, 1

def test_safe_domains():
    """測試安全網域功能"""
    print_section("安全網域功能測試")
    
    try:
        import anti_fraud_clean_app
        
        safe_domains = anti_fraud_clean_app.SAFE_DOMAINS
        donation_domains = anti_fraud_clean_app.DONATION_DOMAINS
        
        # 測試網域數量
        domain_count_test = len(safe_domains) > 300
        donation_count_test = len(donation_domains) >= 2
        
        # 測試知名網域
        test_domains = [
            "google.com", "facebook.com", "gov.tw", "pchome.com.tw",
            "cht.com.tw", "bot.com.tw", "youtube.com"
        ]
        
        found_domains = [domain for domain in test_domains if domain in safe_domains]
        domain_coverage_test = len(found_domains) >= 6
        
        # 測試贊助網域
        donation_test = "buymeacoffee.com/todao_antifraud" in donation_domains
        
        tests = [
            ("安全網域數量", domain_count_test, f"載入 {len(safe_domains)} 個網域"),
            ("贊助網域數量", donation_count_test, f"載入 {len(donation_domains)} 個贊助網域"),
            ("知名網域覆蓋", domain_coverage_test, f"找到 {len(found_domains)}/{len(test_domains)} 個測試網域"),
            ("贊助網域檢測", donation_test, "buymeacoffee.com/todao_antifraud 存在")
        ]
        
        passed = 0
        for test_name, condition, details in tests:
            if condition:
                print_test(test_name, "PASS", details)
                passed += 1
            else:
                print_test(test_name, "FAIL", details)
        
        return passed, len(tests)
        
    except Exception as e:
        print_test("安全網域載入", "FAIL", f"錯誤: {e}")
        return 0, 1

def test_fraud_knowledge():
    """測試防詐知識功能"""
    print_section("防詐知識功能測試")
    
    try:
        from fraud_knowledge import (
            get_anti_fraud_tips, load_fraud_tactics, 
            analyze_fraud_keywords, get_fraud_features
        )
        
        # 測試防詐小知識
        tip = get_anti_fraud_tips()
        tip_test = isinstance(tip, str) and len(tip) > 10
        
        # 測試詐騙類型載入
        fraud_types = load_fraud_tactics()
        fraud_types_test = isinstance(fraud_types, dict) and len(fraud_types) > 5
        
        # 測試關鍵詞分析
        test_messages = [
            "投資穩賺不賠，保證獲利",
            "點擊連結領取獎品",
            "您的帳戶異常，請立即處理"
        ]
        
        keyword_results = []
        for msg in test_messages:
            result = analyze_fraud_keywords(msg)
            keyword_results.append(len(result) if result else 0)
        
        keyword_test = any(count > 0 for count in keyword_results)
        
        # 測試詐騙特徵獲取
        try:
            features = get_fraud_features("投資詐騙", "保證獲利的投資機會")
            features_test = isinstance(features, str) and len(features) > 20
        except:
            features_test = False
        
        tests = [
            ("防詐小知識", tip_test, f"獲取到 {len(tip)} 字元的小知識"),
            ("詐騙類型載入", fraud_types_test, f"載入 {len(fraud_types)} 種詐騙類型"),
            ("關鍵詞分析", keyword_test, f"分析結果: {keyword_results}"),
            ("詐騙特徵獲取", features_test, "成功獲取詐騙特徵說明")
        ]
        
        passed = 0
        for test_name, condition, details in tests:
            if condition:
                print_test(test_name, "PASS", details)
                passed += 1
            else:
                print_test(test_name, "FAIL", details)
        
        return passed, len(tests)
        
    except Exception as e:
        print_test("防詐知識模組", "FAIL", f"錯誤: {e}")
        return 0, 1

def test_weather_service():
    """測試天氣服務功能"""
    print_section("天氣服務功能測試")
    
    try:
        from weather_service import (
            handle_weather_query, is_weather_related, 
            get_supported_cities, get_weather_data
        )
        
        # 測試天氣詢問檢測
        weather_queries = [
            "今天台北天氣如何？",
            "明天會下雨嗎？",
            "高雄現在幾度？",
            "這不是天氣問題"
        ]
        
        detection_results = [is_weather_related(q) for q in weather_queries]
        detection_test = detection_results == [True, True, True, False]
        
        # 測試支援城市
        cities = get_supported_cities()
        cities_test = isinstance(cities, list) and len(cities) >= 15
        
        # 測試天氣查詢
        weather_response = handle_weather_query("今天台北天氣如何？", "測試用戶")
        weather_test = isinstance(weather_response, str) and "台北" in weather_response
        
        # 測試天氣資料獲取
        try:
            weather_data = get_weather_data("台北")
            weather_data_test = isinstance(weather_data, dict) and "city" in weather_data
        except:
            weather_data_test = False
        
        tests = [
            ("天氣詢問檢測", detection_test, f"檢測結果: {detection_results}"),
            ("支援城市載入", cities_test, f"支援 {len(cities)} 個城市"),
            ("天氣查詢回應", weather_test, "成功生成天氣回應"),
            ("天氣資料獲取", weather_data_test, "成功獲取天氣資料")
        ]
        
        passed = 0
        for test_name, condition, details in tests:
            if condition:
                print_test(test_name, "PASS", details)
                passed += 1
            else:
                print_test(test_name, "FAIL", details)
        
        return passed, len(tests)
        
    except Exception as e:
        print_test("天氣服務模組", "FAIL", f"錯誤: {e}")
        return 0, 1

def test_flex_message_service():
    """測試 Flex Message 服務功能"""
    print_section("Flex Message 服務功能測試")
    
    try:
        from flex_message_service import (
            create_analysis_flex_message, create_donation_flex_message,
            create_weather_flex_message, create_domain_spoofing_flex_message
        )
        
        # 測試詐騙分析 Flex Message
        analysis_data = {
            "risk_level": "高風險",
            "fraud_type": "假交友投資詐騙",
            "explanation": "這是測試分析說明",
            "suggestions": "請保持警覺"
        }
        
        try:
            analysis_flex = create_analysis_flex_message(
                analysis_data, "測試用戶", "測試訊息"
            )
            analysis_test = hasattr(analysis_flex, 'alt_text')
        except:
            analysis_test = False
        
        # 測試贊助彩蛋 Flex Message
        try:
            donation_flex = create_donation_flex_message()
            donation_test = hasattr(donation_flex, 'alt_text')
        except:
            donation_test = False
        
        # 測試天氣 Flex Message
        weather_data = {
            "city": "台北",
            "date": "2025-05-24",
            "weather": "晴天",
            "temperature": "18-25°C",
            "humidity": "60%",
            "rain_chance": "20%"
        }
        
        try:
            weather_flex = create_weather_flex_message(weather_data, "測試用戶")
            weather_test = hasattr(weather_flex, 'alt_text')
        except:
            weather_test = False
        
        # 測試網域變形攻擊 Flex Message
        spoofing_data = {
            "is_spoofing": True,
            "suspicious_domain": "goog1e.com",
            "similar_domain": "google.com",
            "similarity_score": 0.95,
            "attack_type": "字元替換攻擊"
        }
        
        try:
            spoofing_flex = create_domain_spoofing_flex_message(
                spoofing_data, "測試用戶", "https://goog1e.com"
            )
            spoofing_test = hasattr(spoofing_flex, 'alt_text')
        except:
            spoofing_test = False
        
        tests = [
            ("詐騙分析 Flex Message", analysis_test, "成功創建詐騙分析訊息"),
            ("贊助彩蛋 Flex Message", donation_test, "成功創建贊助彩蛋訊息"),
            ("天氣 Flex Message", weather_test, "成功創建天氣訊息"),
            ("網域變形 Flex Message", spoofing_test, "成功創建網域變形警告訊息")
        ]
        
        passed = 0
        for test_name, condition, details in tests:
            if condition:
                print_test(test_name, "PASS", details)
                passed += 1
            else:
                print_test(test_name, "FAIL", details)
        
        return passed, len(tests)
        
    except Exception as e:
        print_test("Flex Message 服務", "FAIL", f"錯誤: {e}")
        return 0, 1

def test_game_service():
    """測試遊戲服務功能"""
    print_section("遊戲服務功能測試")
    
    try:
        from game_service import (
            start_potato_game, handle_potato_game_answer,
            is_game_trigger, get_user_game_state
        )
        
        # 測試遊戲觸發檢測
        game_triggers = [
            "玩土豆遊戲",
            "選土豆",
            "土豆遊戲",
            "這不是遊戲觸發"
        ]
        
        trigger_results = [is_game_trigger(msg) for msg in game_triggers]
        trigger_test = trigger_results == [True, True, True, False]
        
        # 測試開始遊戲
        test_user_id = "test_user_comprehensive"
        flex_message, error = start_potato_game(test_user_id)
        
        game_start_test = flex_message is not None and error is None
        
        # 測試遊戲狀態
        if game_start_test:
            game_state = get_user_game_state(test_user_id)
            state_test = game_state is not None and "question" in game_state
        else:
            state_test = False
        
        # 測試遊戲回答
        if game_start_test:
            try:
                is_correct, result_flex = handle_potato_game_answer(test_user_id, 0)
                answer_test = isinstance(is_correct, bool) and result_flex is not None
            except:
                answer_test = False
        else:
            answer_test = False
        
        tests = [
            ("遊戲觸發檢測", trigger_test, f"檢測結果: {trigger_results}"),
            ("遊戲開始功能", game_start_test, "成功開始遊戲" if game_start_test else f"錯誤: {error}"),
            ("遊戲狀態記錄", state_test, "成功記錄遊戲狀態"),
            ("遊戲回答處理", answer_test, "成功處理遊戲回答")
        ]
        
        passed = 0
        for test_name, condition, details in tests:
            if condition:
                print_test(test_name, "PASS", details)
                passed += 1
            else:
                print_test(test_name, "FAIL", details)
        
        return passed, len(tests)
        
    except Exception as e:
        print_test("遊戲服務模組", "FAIL", f"錯誤: {e}")
        return 0, 1

def test_main_app_functions():
    """測試主程式核心功能"""
    print_section("主程式核心功能測試")
    
    try:
        import anti_fraud_clean_app
        
        # 測試 URL 檢測
        test_urls = [
            "https://google.com",
            "http://suspicious-site.com",
            "這裡沒有網址",
            "請點擊 https://bit.ly/test123"
        ]
        
        url_detection_results = []
        for url in test_urls:
            result = anti_fraud_clean_app.contains_url(url)
            url_detection_results.append(result)
        
        url_test = url_detection_results == [True, True, False, True]
        
        # 測試詐騙分析觸發
        fraud_messages = [
            "投資穩賺不賠",
            "點擊連結領獎",
            "今天天氣真好",
            "https://suspicious-investment.com"
        ]
        
        fraud_trigger_results = []
        for msg in fraud_messages:
            result = anti_fraud_clean_app.should_perform_fraud_analysis(msg)
            fraud_trigger_results.append(result)
        
        fraud_trigger_test = fraud_trigger_results[0] or fraud_trigger_results[1] or fraud_trigger_results[3]
        
        # 測試用戶個人資料獲取函數存在
        profile_func_test = hasattr(anti_fraud_clean_app, 'get_user_profile')
        
        # 測試詐騙分析解析函數
        test_analysis = '{"risk_level": "高風險", "fraud_type": "投資詐騙", "explanation": "測試", "suggestions": "小心"}'
        try:
            parsed = anti_fraud_clean_app.parse_fraud_analysis(test_analysis)
            parse_test = isinstance(parsed, dict) and "risk_level" in parsed
        except:
            parse_test = False
        
        tests = [
            ("URL 檢測功能", url_test, f"檢測結果: {url_detection_results}"),
            ("詐騙分析觸發", fraud_trigger_test, f"觸發結果: {fraud_trigger_results}"),
            ("用戶資料函數", profile_func_test, "get_user_profile 函數存在"),
            ("分析結果解析", parse_test, "成功解析 JSON 格式分析結果")
        ]
        
        passed = 0
        for test_name, condition, details in tests:
            if condition:
                print_test(test_name, "PASS", details)
                passed += 1
            else:
                print_test(test_name, "FAIL", details)
        
        return passed, len(tests)
        
    except Exception as e:
        print_test("主程式功能", "FAIL", f"錯誤: {e}")
        return 0, 1

def test_integration_scenarios():
    """測試整合情境"""
    print_section("整合情境測試")
    
    try:
        from weather_service import is_weather_related, handle_weather_query
        from game_service import is_game_trigger
        from fraud_knowledge import analyze_fraud_keywords
        import anti_fraud_clean_app
        
        # 情境 1: 天氣查詢流程
        weather_msg = "今天台北天氣如何？"
        weather_detected = is_weather_related(weather_msg)
        weather_response = handle_weather_query(weather_msg, "測試用戶") if weather_detected else None
        weather_scenario_test = weather_detected and weather_response is not None
        
        # 情境 2: 遊戲觸發流程
        game_msg = "玩土豆遊戲"
        game_detected = is_game_trigger(game_msg)
        game_scenario_test = game_detected
        
        # 情境 3: 詐騙檢測流程
        fraud_msg = "投資穩賺不賠，點擊連結 https://fake-investment.com"
        has_url = anti_fraud_clean_app.contains_url(fraud_msg)
        should_analyze = anti_fraud_clean_app.should_perform_fraud_analysis(fraud_msg)
        keywords = analyze_fraud_keywords(fraud_msg)
        fraud_scenario_test = has_url and should_analyze
        
        # 情境 4: 安全網域檢測
        safe_url = "https://google.com"
        safe_detected = "google.com" in anti_fraud_clean_app.SAFE_DOMAINS
        safe_scenario_test = safe_detected
        
        # 情境 5: 贊助網域檢測
        donation_url = "https://buymeacoffee.com/todao_antifraud"
        donation_detected = "buymeacoffee.com/todao_antifraud" in anti_fraud_clean_app.DONATION_DOMAINS
        donation_scenario_test = donation_detected
        
        tests = [
            ("天氣查詢情境", weather_scenario_test, f"檢測: {weather_detected}, 回應: {'有' if weather_response else '無'}"),
            ("遊戲觸發情境", game_scenario_test, f"遊戲觸發檢測: {game_detected}"),
            ("詐騙檢測情境", fraud_scenario_test, f"URL: {has_url}, 分析: {should_analyze}"),
            ("安全網域情境", safe_scenario_test, f"google.com 安全檢測: {safe_detected}"),
            ("贊助網域情境", donation_scenario_test, f"贊助網域檢測: {donation_detected}")
        ]
        
        passed = 0
        for test_name, condition, details in tests:
            if condition:
                print_test(test_name, "PASS", details)
                passed += 1
            else:
                print_test(test_name, "FAIL", details)
        
        return passed, len(tests)
        
    except Exception as e:
        print_test("整合情境測試", "FAIL", f"錯誤: {e}")
        return 0, 1

def main():
    """主測試函數"""
    print("🚀 防詐騙機器人完整功能測試")
    print("=" * 60)
    print("測試開始時間:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # 執行所有測試
    test_functions = [
        ("基本模組導入", test_basic_imports),
        ("配置功能", test_configuration),
        ("安全網域功能", test_safe_domains),
        ("防詐知識功能", test_fraud_knowledge),
        ("天氣服務功能", test_weather_service),
        ("Flex Message 服務", test_flex_message_service),
        ("遊戲服務功能", test_game_service),
        ("主程式核心功能", test_main_app_functions),
        ("整合情境", test_integration_scenarios)
    ]
    
    total_passed = 0
    total_tests = 0
    
    for test_name, test_func in test_functions:
        try:
            passed, tests = test_func()
            total_passed += passed
            total_tests += tests
            print(f"\n📊 {test_name}: {passed}/{tests} 通過")
        except Exception as e:
            print(f"\n❌ {test_name}: 測試執行失敗 - {e}")
            total_tests += 1
    
    # 總結報告
    print_section("測試總結報告")
    
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"📈 總測試數量: {total_tests}")
    print(f"✅ 通過測試: {total_passed}")
    print(f"❌ 失敗測試: {total_tests - total_passed}")
    print(f"📊 成功率: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🎉 優秀！機器人功能運作良好！")
        status = "EXCELLENT"
    elif success_rate >= 80:
        print("\n👍 良好！大部分功能正常運作。")
        status = "GOOD"
    elif success_rate >= 70:
        print("\n⚠️ 尚可，但有一些問題需要修復。")
        status = "FAIR"
    else:
        print("\n🔧 需要修復多個問題。")
        status = "NEEDS_WORK"
    
    print(f"\n測試完成時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"整體狀態: {status}")
    
    return success_rate >= 80

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 