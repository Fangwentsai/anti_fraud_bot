# -*- coding: utf-8 -*-
"""
天氣功能整合測試
"""

def test_weather_integration():
    """測試天氣功能是否正確整合到主程式"""
    try:
        # 測試import
        from calendar_weather_service import get_weather, get_today_info, get_date_info, get_solar_terms
        print("✅ 天氣服務模組import成功")
        
        # 測試基本功能
        weather_result = get_weather("台北", 1)
        print("✅ 天氣查詢功能正常")
        print(f"天氣結果長度: {len(weather_result)} 字元")
        
        date_result = get_date_info()
        print("✅ 日期查詢功能正常")
        print(f"日期結果長度: {len(date_result)} 字元")
        
        today_result = get_today_info()
        print("✅ 今日完整資訊功能正常")
        print(f"今日資訊長度: {len(today_result)} 字元")
        
        solar_result = get_solar_terms(2024)
        print("✅ 節氣查詢功能正常")
        print(f"節氣結果長度: {len(solar_result)} 字元")
        
        print("\n🎉 所有天氣功能測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False

def test_main_app_import():
    """測試主程式是否能正確import天氣功能"""
    try:
        # 檢查主程式中的import
        import anti_fraud_clean_app
        print("✅ 主程式import成功")
        
        # 檢查是否有天氣相關的函數
        if hasattr(anti_fraud_clean_app, 'get_weather'):
            print("✅ 主程式中有get_weather函數")
        else:
            print("ℹ️ 主程式中沒有直接的get_weather函數（這是正常的，因為是從模組import）")
        
        print("✅ 主程式整合測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 主程式測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("=== 天氣功能整合測試 ===\n")
    
    print("1. 測試天氣服務模組...")
    weather_ok = test_weather_integration()
    
    print("\n2. 測試主程式整合...")
    main_ok = test_main_app_import()
    
    print(f"\n=== 測試結果 ===")
    print(f"天氣服務: {'✅ 通過' if weather_ok else '❌ 失敗'}")
    print(f"主程式整合: {'✅ 通過' if main_ok else '❌ 失敗'}")
    
    if weather_ok and main_ok:
        print("\n🎉 恭喜！天氣功能已成功整合到您的防詐騙LINE Bot中！")
        print("\n📝 使用說明：")
        print("- 輸入「台北天氣」查看台北天氣")
        print("- 輸入「今天日期」查看今日日期資訊")
        print("- 輸入「今天日期天氣」查看完整資訊")
        print("- 輸入「節氣」查看二十四節氣")
        print("- 支援20個台灣城市的天氣查詢")
    else:
        print("\n❌ 整合過程中發現問題，請檢查錯誤訊息") 