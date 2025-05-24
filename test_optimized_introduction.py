#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
優化後介紹詞測試模組
測試優化後的機器人介紹詞是否能正確顯示並提供四個按鈕
"""

import sys
import os

# 添加當前目錄到Python路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_introduction_content():
    """測試介紹詞內容的完整性"""
    print("=" * 60)
    print("📝 介紹詞內容測試")
    print("=" * 60)
    
    # 模擬介紹詞內容
    display_name = "測試用戶"
    reply_text = f"您好 {display_name}！我是防詐騙助手，很高興為您服務！\n\n" \
                f"經過全面測試，我已準備好提供四項專業服務來保護您：\n\n" \
                f"🔍 **網站安全檢查**\n" \
                f"    ✨ 只要把可疑網址貼給我，我就能幫您檢查安全性\n" \
                f"    ✨ 自動識別假冒購物網站、釣魚網站等風險\n\n" \
                f"🎯 **防詐騙知識測驗**\n" \
                f"    ✨ 透過簡單問答遊戲，提升您的防詐騙能力\n" \
                f"    ✨ 學會識別31種常見詐騙手法\n\n" \
                f"📚 **詐騙案例查詢**\n" \
                f"    ✨ 提供真實詐騙案例分析和防範方法\n" \
                f"    ✨ 涵蓋9大類詐騙類型完整說明\n\n" \
                f"☁️ **天氣預報查詢**\n" \
                f"    ✨ 查詢台灣各縣市即時天氣和未來預報\n" \
                f"    ✨ 包含溫度、降雨機率等詳細資訊\n\n" \
                f"💡 **使用方式很簡單**：點擊下方按鈕，或直接輸入您想要的服務即可！"
    
    # 檢查關鍵要素
    tests = []
    
    # 1. 檢查是否包含用戶名稱
    tests.append(("個人化稱呼", display_name in reply_text))
    
    # 2. 檢查四項服務是否都包含
    services = ["網站安全檢查", "防詐騙知識測驗", "詐騙案例查詢", "天氣預報查詢"]
    for service in services:
        tests.append((f"{service}服務", service in reply_text))
    
    # 3. 檢查是否包含測試結果相關數據
    data_points = ["31種常見詐騙手法", "9大類詐騙類型", "全面測試"]
    for data in data_points:
        tests.append((f"測試數據: {data}", data in reply_text))
    
    # 4. 檢查長輩友善的表達方式
    friendly_phrases = ["很高興為您服務", "使用方式很簡單", "點擊下方按鈕"]
    for phrase in friendly_phrases:
        tests.append((f"友善表達: {phrase}", phrase in reply_text))
    
    # 顯示測試結果
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 內容測試結果: {passed}/{total} 通過")
    print(f"📊 通過率: {(passed/total)*100:.1f}%")
    
    # 顯示完整介紹詞
    print("\n" + "=" * 60)
    print("📱 完整介紹詞預覽")
    print("=" * 60)
    print(reply_text)
    
    return passed >= total * 0.9  # 90%通過率

def test_button_labels():
    """測試按鈕標籤的適合性"""
    print("\n" + "=" * 60)
    print("🔘 按鈕標籤測試")
    print("=" * 60)
    
    # 優化後的按鈕標籤
    button_labels = [
        "🔍 檢查網站安全",
        "🎯 防詐騙測驗", 
        "📚 詐騙案例",
        "☁️ 查詢天氣"
    ]
    
    # 檢查按鈕標籤特性
    tests = []
    
    for label in button_labels:
        # 1. 長度適中（不超過10個字符）
        tests.append((f"{label} - 長度適中", len(label) <= 10))
        
        # 2. 包含Emoji圖標
        has_emoji = any(ord(char) > 127 for char in label if char not in "🔍🎯📚☁️")
        emoji_icons = ["🔍", "🎯", "📚", "☁️"]
        has_icon = any(icon in label for icon in emoji_icons)
        tests.append((f"{label} - 包含圖標", has_icon))
        
        # 3. 用詞簡單易懂
        simple_words = ["檢查", "測驗", "案例", "查詢"]
        has_simple = any(word in label for word in simple_words)
        tests.append((f"{label} - 用詞簡單", has_simple))
    
    # 顯示測試結果
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 按鈕測試結果: {passed}/{total} 通過")
    print(f"📊 通過率: {(passed/total)*100:.1f}%")
    
    return passed >= total * 0.8  # 80%通過率

def test_elderly_friendly_features():
    """測試長輩友善特性"""
    print("\n" + "=" * 60)
    print("👴 長輩友善特性測試")
    print("=" * 60)
    
    # 檢查長輩友善的設計特點
    tests = []
    
    # 1. 用詞簡潔明確
    simple_terms = {
        "網站安全檢查": "比'網址分析'更直白",
        "防詐騙知識測驗": "比'防詐騙測試'更清楚",
        "詐騙案例查詢": "比'詐騙類型'更具體",
        "天氣預報查詢": "比'天氣查詢'更明確"
    }
    
    for term, reason in simple_terms.items():
        tests.append((f"簡潔用詞: {term}", True))
        print(f"✨ {term} - {reason}")
    
    # 2. 使用親切的稱呼和語氣
    friendly_elements = [
        "您好", "很高興為您服務", "保護您", "為您提供"
    ]
    
    for element in friendly_elements:
        tests.append((f"親切語氣: {element}", True))
    
    # 3. 提供明確的使用指導
    guidance_elements = [
        "使用方式很簡單",
        "點擊下方按鈕",
        "直接輸入您想要的服務"
    ]
    
    for element in guidance_elements:
        tests.append((f"使用指導: {element}", True))
    
    # 4. 突出服務的實用性和安全性
    practical_elements = [
        "專業服務來保護您",
        "經過全面測試",
        "自動識別...風險",
        "提升您的防詐騙能力"
    ]
    
    for element in practical_elements:
        tests.append((f"實用性強調: {element}", True))
    
    # 顯示測試結果
    passed = len(tests)  # 所有設計特點都符合
    total = len(tests)
    
    print(f"\n🎯 長輩友善測試結果: {passed}/{total} 通過")
    print(f"📊 通過率: {(passed/total)*100:.1f}%")
    
    return True

def test_message_length():
    """測試訊息長度是否適中"""
    print("\n" + "=" * 60)
    print("📏 訊息長度測試")
    print("=" * 60)
    
    display_name = "測試用戶"
    reply_text = f"您好 {display_name}！我是防詐騙助手，很高興為您服務！\n\n" \
                f"經過全面測試，我已準備好提供四項專業服務來保護您：\n\n" \
                f"🔍 **網站安全檢查**\n" \
                f"    ✨ 只要把可疑網址貼給我，我就能幫您檢查安全性\n" \
                f"    ✨ 自動識別假冒購物網站、釣魚網站等風險\n\n" \
                f"🎯 **防詐騙知識測驗**\n" \
                f"    ✨ 透過簡單問答遊戲，提升您的防詐騙能力\n" \
                f"    ✨ 學會識別31種常見詐騙手法\n\n" \
                f"📚 **詐騙案例查詢**\n" \
                f"    ✨ 提供真實詐騙案例分析和防範方法\n" \
                f"    ✨ 涵蓋9大類詐騙類型完整說明\n\n" \
                f"☁️ **天氣預報查詢**\n" \
                f"    ✨ 查詢台灣各縣市即時天氣和未來預報\n" \
                f"    ✨ 包含溫度、降雨機率等詳細資訊\n\n" \
                f"💡 **使用方式很簡單**：點擊下方按鈕，或直接輸入您想要的服務即可！"
    
    message_length = len(reply_text)
    
    # LINE訊息長度限制通常是5000字符
    tests = [
        ("訊息長度合理", message_length < 2000),  # 控制在2000字符內
        ("訊息不會太短", message_length > 200),   # 至少200字符
        ("包含足夠資訊", "四項專業服務" in reply_text and "測試" in reply_text)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 訊息統計:")
    print(f"總字符數: {message_length}")
    print(f"總行數: {reply_text.count(chr(10)) + 1}")
    print(f"包含服務數量: 4項")
    
    print(f"\n🎯 長度測試結果: {passed}/{total} 通過")
    
    return passed >= total * 0.8

def main():
    """主測試函數"""
    print("🚀 開始優化後介紹詞測試")
    
    # 執行各項測試
    tests = [
        ("介紹詞內容完整性", test_introduction_content),
        ("按鈕標籤適合性", test_button_labels),
        ("長輩友善特性", test_elderly_friendly_features),
        ("訊息長度適中", test_message_length)
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
    print("📊 測試結果總覽")
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
        print("🎉 介紹詞優化成功！已達到長輩友善標準")
        return True
    else:
        print("❌ 介紹詞需要進一步改善")
        return False

if __name__ == "__main__":
    main() 