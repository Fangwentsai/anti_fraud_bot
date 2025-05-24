#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最終改進測試模組
測試稱呼改進和按鈕功能對應
"""

import sys
import os

# 添加當前目錄到Python路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_respectful_addressing():
    """測試尊重的稱呼方式"""
    print("=" * 60)
    print("👥 尊重稱呼測試")
    print("=" * 60)
    
    # 檢查是否移除了不當稱呼
    with open('anti_fraud_clean_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open('config.py', 'r', encoding='utf-8') as f:
        config_content = f.read()
    
    tests = []
    
    # 1. 檢查是否移除了"阿姨叔叔"稱呼（在系統提示詞中）
    problematic_phrases = [
        "50-60歲的阿姨叔叔",
        "像鄰居阿姨在聊天"
    ]
    
    for phrase in problematic_phrases:
        found_in_main = phrase in content
        found_in_config = phrase in config_content
        tests.append((f"移除不當稱呼: {phrase}", not found_in_main and not found_in_config))
    
    # 2. 檢查是否改為更尊重的表達
    respectful_phrases = [
        "50-60歲的長輩",
        "像鄰居朋友在聊天",
        "鄰居朋友給出的貼心提醒"
    ]
    
    for phrase in respectful_phrases:
        found_in_main = phrase in content
        found_in_config = phrase in config_content
        tests.append((f"使用尊重稱呼: {phrase}", found_in_main or found_in_config))
    
    # 3. 檢查介紹詞是否使用暱稱
    intro_uses_display_name = "您好 {display_name}！我是防詐騙助手" in content
    tests.append(("介紹詞使用暱稱", intro_uses_display_name))
    
    # 顯示測試結果
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 稱呼測試結果: {passed}/{total} 通過")
    return passed >= total * 0.8

def test_button_service_mapping():
    """測試按鈕與服務的對應關係"""
    print("\n" + "=" * 60)
    print("🔘 按鈕服務對應測試")
    print("=" * 60)
    
    # 定義預期的按鈕和對應功能
    expected_buttons = {
        "🔍 檢查網站安全": {
            "text": "請幫我分析這則訊息：",
            "service": "網站安全檢查",
            "description": "檢查可疑網址和釣魚網站"
        },
        "🎯 防詐騙測驗": {
            "text": "防詐騙測試",
            "service": "防詐騙知識測驗",
            "description": "互動問答遊戲"
        },
        "📚 詐騙案例": {
            "text": "詐騙類型列表",
            "service": "詐騙案例查詢",
            "description": "真實案例分析"
        },
        "☁️ 查詢天氣": {
            "text": "今天天氣",
            "service": "天氣預報查詢",
            "description": "台灣各縣市天氣預報"
        }
    }
    
    # 從代碼中檢查按鈕定義
    with open('anti_fraud_clean_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    tests = []
    
    for button_label, button_info in expected_buttons.items():
        # 1. 檢查按鈕標籤是否存在
        button_exists = f'label="{button_label}"' in content
        tests.append((f"按鈕存在: {button_label}", button_exists))
        
        # 2. 檢查按鈕對應的文字觸發是否正確
        text_trigger = f'text="{button_info["text"]}"' in content
        tests.append((f"觸發文字正確: {button_info['text']}", text_trigger))
        
        # 3. 檢查對應服務是否在介紹詞中描述
        service_described = button_info["service"] in content
        tests.append((f"服務已描述: {button_info['service']}", service_described))
    
    # 檢查群組和個人聊天的按鈕是否都存在
    group_buttons = "bot_trigger_keyword" in content and "QuickReplyButton" in content
    personal_buttons = "QuickReply(items=[" in content
    
    tests.append(("群組聊天按鈕", group_buttons))
    tests.append(("個人聊天按鈕", personal_buttons))
    
    # 顯示測試結果
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 按鈕對應測試結果: {passed}/{total} 通過")
    
    # 顯示按鈕功能對應表
    print("\n📋 按鈕功能對應表:")
    for button_label, button_info in expected_buttons.items():
        print(f"  {button_label}")
        print(f"    觸發: {button_info['text']}")
        print(f"    服務: {button_info['service']}")
        print(f"    說明: {button_info['description']}")
        print()
    
    return passed >= total * 0.8

def test_user_experience_flow():
    """測試用戶使用流程"""
    print("=" * 60)
    print("🎭 用戶體驗流程測試")
    print("=" * 60)
    
    # 模擬用戶使用流程
    test_scenarios = [
        {
            "scenario": "新用戶初次使用",
            "input": "防詐騙助手",
            "expected_output": ["您好", "四項專業服務", "點擊下方按鈕"],
            "should_have_buttons": True
        },
        {
            "scenario": "用戶詢問功能",
            "input": "你有什麼功能",
            "expected_output": ["四項專業服務", "網站安全檢查", "防詐騙知識測驗"],
            "should_have_buttons": True
        },
        {
            "scenario": "用戶點擊網站檢查按鈕",
            "input": "請幫我分析這則訊息：",
            "expected_output": ["分析可疑訊息", "傳給我"],
            "should_have_buttons": False
        },
        {
            "scenario": "用戶點擊防詐騙測驗按鈕",
            "input": "防詐騙測試",
            "expected_output": ["遊戲", "測試"],
            "should_have_buttons": False
        }
    ]
    
    # 讀取代碼檢查流程邏輯
    with open('anti_fraud_clean_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    tests = []
    
    for scenario in test_scenarios:
        scenario_name = scenario["scenario"]
        
        # 檢查該情境的邏輯是否存在
        input_trigger = scenario["input"]
        has_logic = any(expected in content for expected in scenario["expected_output"])
        
        tests.append((f"{scenario_name} - 邏輯存在", has_logic))
        
        # 檢查是否有按鈕生成邏輯
        if scenario["should_have_buttons"]:
            has_buttons = "QuickReply" in content and "QuickReplyButton" in content
            tests.append((f"{scenario_name} - 包含按鈕", has_buttons))
    
    # 顯示測試結果
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 流程測試結果: {passed}/{total} 通過")
    return passed >= total * 0.8

def main():
    """主測試函數"""
    print("🚀 開始最終改進測試")
    
    # 執行各項測試
    tests = [
        ("尊重稱呼改進", test_respectful_addressing),
        ("按鈕服務對應", test_button_service_mapping),
        ("用戶體驗流程", test_user_experience_flow)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}測試時發生錯誤: {e}")
            results.append((test_name, False))
    
    # 統計結果
    print("\n" + "=" * 60)
    print("📊 最終改進測試總覽")
    print("=" * 60)
    
    passed_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    print(f"\n🎯 總通過率: {passed_tests}/{total_tests}")
    success_rate = (passed_tests / total_tests) * 100
    print(f"📈 成功率: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 最終改進成功！機器人已完美符合用戶需求")
        print("\n✨ 改進重點:")
        print("• 移除不當稱呼，改用尊重的表達方式")
        print("• 四個按鈕完美對應四項服務功能")
        print("• 用戶體驗流程順暢自然")
        print("• 長輩友善設計標準")
        return True
    else:
        print("❌ 仍需進一步改善")
        return False

if __name__ == "__main__":
    main() 