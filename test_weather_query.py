#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天氣查詢測試模組
測試天氣查詢功能的準確性和完整性
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

from weather_service import handle_weather_query_data, is_weather_related

def test_weather_recognition():
    """測試天氣查詢關鍵詞識別"""
    print("=" * 60)
    print("☁️ 天氣查詢識別測試")
    print("=" * 60)
    
    # 測試天氣相關關鍵詞
    weather_phrases = [
        "今天天氣如何",
        "台北天氣",
        "明天會下雨嗎",
        "氣溫多少",
        "宜蘭天氣怎麼樣",
        "高雄溫度",
        "屏東會不會下雨",
        "嘉義天氣預報",
        "今天溫度",
        "明天天氣"
    ]
    
    results = []
    for phrase in weather_phrases:
        is_weather = is_weather_related(phrase)
        print(f"📝 測試天氣詞: '{phrase}' -> {'✅ 識別' if is_weather else '❌ 未識別'}")
        results.append(is_weather)
    
    # 測試非天氣關鍵詞
    non_weather_phrases = [
        "詐騙案例",
        "分析網站",
        "防詐遊戲",
        "你好"
    ]
    
    for phrase in non_weather_phrases:
        is_weather = is_weather_related(phrase)
        print(f"📝 測試非天氣詞: '{phrase}' -> {'✅ 正確(未識別)' if not is_weather else '❌ 錯誤(意外識別)'}")
        results.append(not is_weather)  # 反向，因為這些不應該觸發
    
    success_count = sum(results)
    total_count = len(results)
    print(f"\n🎯 識別測試結果: {success_count}/{total_count} 正確")
    
    return success_count >= total_count * 0.8  # 80%正確率

def test_target_cities_weather():
    """測試指定城市的天氣查詢"""
    print("\n" + "=" * 60)
    print("🌍 指定城市天氣查詢測試")
    print("=" * 60)
    
    target_cities = [
        ("台北", "今天台北天氣如何"),
        ("宜蘭", "宜蘭天氣預報"),
        ("嘉義", "嘉義氣溫多少"),
        ("高雄", "高雄會下雨嗎"),
        ("屏東", "屏東天氣怎麼樣")
    ]
    
    results = []
    
    for city, query in target_cities:
        print(f"\n📍 測試城市: {city}")
        print(f"🔍 查詢語句: {query}")
        
        try:
            weather_result = handle_weather_query_data(query)
            
            if weather_result["success"]:
                weather_data = weather_result["data"]
                print(f"✅ 成功取得天氣資料")
                print(f"📍 地區: {weather_data.get('location', '未知')}")
                print(f"🌡️ 溫度: {weather_data.get('temperature', '未知')}")
                print(f"☁️ 天氣: {weather_data.get('weather_description', '未知')}")
                print(f"💧 降雨機率: {weather_data.get('rain_probability', '未知')}")
                
                # 檢查資料完整性
                has_location = bool(weather_data.get('location'))
                has_temperature = bool(weather_data.get('temperature'))
                has_description = bool(weather_data.get('weather_description'))
                
                is_complete = has_location and has_temperature and has_description
                results.append({
                    "city": city,
                    "success": True,
                    "complete": is_complete,
                    "data": weather_data
                })
                
                print(f"🎯 資料完整性: {'✅ 完整' if is_complete else '❌ 不完整'}")
            else:
                print(f"❌ 查詢失敗: {weather_result['message']}")
                results.append({
                    "city": city,
                    "success": False,
                    "complete": False,
                    "error": weather_result['message']
                })
                
        except Exception as e:
            print(f"❌ 查詢過程發生錯誤: {e}")
            results.append({
                "city": city,
                "success": False,
                "complete": False,
                "error": str(e)
            })
    
    return results

def test_weather_data_quality():
    """測試天氣資料品質"""
    print("\n" + "=" * 60)
    print("🌟 天氣資料品質測試")
    print("=" * 60)
    
    # 測試不同的查詢方式
    test_queries = [
        "今天天氣",
        "明天台北天氣",
        "高雄溫度",
        "會不會下雨"
    ]
    
    quality_results = []
    
    for query in test_queries:
        print(f"\n🔍 測試查詢: '{query}'")
        
        try:
            weather_result = handle_weather_query_data(query)
            
            if weather_result["success"]:
                data = weather_result["data"]
                
                # 檢查資料品質
                quality_score = 0
                
                # 1. 有溫度資訊
                if data.get('temperature'):
                    quality_score += 1
                    print("✅ 包含溫度資訊")
                else:
                    print("❌ 缺少溫度資訊")
                
                # 2. 有天氣描述
                if data.get('weather_description'):
                    quality_score += 1
                    print("✅ 包含天氣描述")
                else:
                    print("❌ 缺少天氣描述")
                
                # 3. 有地點資訊
                if data.get('location'):
                    quality_score += 1
                    print("✅ 包含地點資訊")
                else:
                    print("❌ 缺少地點資訊")
                
                # 4. 有時間資訊
                if data.get('forecast_time') or data.get('update_time'):
                    quality_score += 1
                    print("✅ 包含時間資訊")
                else:
                    print("❌ 缺少時間資訊")
                
                quality_results.append({
                    "query": query,
                    "score": quality_score,
                    "max_score": 4
                })
                
                print(f"🎯 品質評分: {quality_score}/4")
                
            else:
                print(f"❌ 查詢失敗，無法評估品質")
                quality_results.append({
                    "query": query,
                    "score": 0,
                    "max_score": 4
                })
                
        except Exception as e:
            print(f"❌ 測試過程發生錯誤: {e}")
            quality_results.append({
                "query": query,
                "score": 0,
                "max_score": 4
            })
    
    return quality_results

def test_weather_edge_cases():
    """測試天氣查詢的邊際案例"""
    print("\n" + "=" * 60)
    print("🧪 天氣查詢邊際案例測試")
    print("=" * 60)
    
    edge_cases = [
        "今天",  # 只有時間，沒有明確的天氣關鍵詞
        "天氣",  # 只有天氣關鍵詞，沒有地點
        "台北",  # 只有地點，沒有天氣關鍵詞
        "不知道什麼地方的天氣",  # 模糊查詢
        "火星天氣"  # 不存在的地點
    ]
    
    edge_results = []
    
    for case in edge_cases:
        print(f"\n🧪 測試案例: '{case}'")
        
        try:
            # 先檢查是否被識別為天氣查詢
            is_weather = is_weather_related(case)
            print(f"🔍 天氣識別: {'是' if is_weather else '否'}")
            
            if is_weather:
                weather_result = handle_weather_query_data(case)
                
                if weather_result["success"]:
                    print("✅ 成功處理邊際案例")
                    edge_results.append(True)
                else:
                    print(f"❌ 處理失敗: {weather_result['message']}")
                    edge_results.append(False)
            else:
                print("✅ 正確識別為非天氣查詢")
                edge_results.append(True)
                
        except Exception as e:
            print(f"❌ 測試過程發生錯誤: {e}")
            edge_results.append(False)
    
    success_count = sum(edge_results)
    total_count = len(edge_results)
    print(f"\n🎯 邊際案例測試結果: {success_count}/{total_count} 成功")
    
    return success_count >= total_count * 0.6  # 60%成功率就算通過

def main():
    """主測試函數"""
    print("🚀 開始天氣查詢功能測試")
    
    # 測試1: 天氣關鍵詞識別
    recognition_ok = test_weather_recognition()
    
    # 測試2: 指定城市天氣查詢
    city_results = test_target_cities_weather()
    
    # 測試3: 天氣資料品質
    quality_results = test_weather_data_quality()
    
    # 測試4: 邊際案例
    edge_ok = test_weather_edge_cases()
    
    # 統計結果
    print("\n" + "=" * 60)
    print("📊 測試結果統計")
    print("=" * 60)
    
    # 城市查詢成功率
    if city_results:
        successful_cities = sum(1 for r in city_results if r.get("success", False))
        complete_cities = sum(1 for r in city_results if r.get("complete", False))
        total_cities = len(city_results)
        
        print(f"城市查詢成功率: {successful_cities}/{total_cities}")
        print(f"資料完整性: {complete_cities}/{total_cities}")
        
        # 顯示成功的城市
        print("✅ 成功查詢的城市:")
        for result in city_results:
            if result.get("success", False):
                print(f"   - {result['city']}: {result['data'].get('location', '未知地區')}")
    else:
        successful_cities = 0
        complete_cities = 0
        total_cities = 5
    
    # 資料品質評分
    if quality_results:
        total_quality_score = sum(r["score"] for r in quality_results)
        max_quality_score = sum(r["max_score"] for r in quality_results)
        quality_percentage = (total_quality_score / max_quality_score) * 100 if max_quality_score > 0 else 0
        print(f"天氣資料品質: {total_quality_score}/{max_quality_score} ({quality_percentage:.1f}%)")
    else:
        quality_percentage = 0
    
    # 綜合評估
    tests = [
        ("天氣識別", recognition_ok),
        ("城市查詢", successful_cities >= 3),  # 至少3個城市成功
        ("資料完整性", complete_cities >= 3),  # 至少3個城市資料完整
        ("邊際案例", edge_ok)
    ]
    
    passed_tests = sum(1 for _, result in tests if result)
    total_tests = len(tests)
    
    for test_name, result in tests:
        print(f"{test_name}: {'✅ 通過' if result else '❌ 失敗'}")
    
    print(f"\n總通過率: {passed_tests}/{total_tests}")
    print(f"天氣查詢品質: {quality_percentage:.1f}%")
    
    if passed_tests >= 3 and quality_percentage >= 60:
        print("🎉 天氣查詢功能測試通過！")
        return True
    else:
        print("❌ 天氣查詢功能需要改進")
        return False

if __name__ == "__main__":
    main() 