#!/usr/bin/env python3
"""
測試真實中央氣象署API整合
"""

import os
import json
from weather_service import WeatherService, handle_weather_query

def test_real_api():
    """測試真實API（需要設定API金鑰）"""
    print("=== 中央氣象署 F-C0032-001 API 測試 ===\n")
    
    # 檢查API金鑰
    api_key = os.environ.get('CWB_API_KEY', '')
    if not api_key:
        print("❌ 未設定 CWB_API_KEY 環境變數")
        print("💡 請先設定API金鑰：export CWB_API_KEY='你的API金鑰'")
        print("📋 申請網址：https://opendata.cwa.gov.tw/")
        return
    
    print(f"✅ 已設定API金鑰：{api_key[:10]}...")
    
    # 測試不同城市
    test_cities = ["台北", "台中", "高雄", "花蓮"]
    
    weather_service = WeatherService()
    
    for city in test_cities:
        print(f"\n🌤️ 測試 {city} 天氣預報...")
        
        try:
            # 獲取天氣資料
            weather_data = weather_service.get_weather_forecast(city, 2)
            
            if weather_data.get("success"):
                print(f"✅ {city} 天氣資料獲取成功")
                print(f"📡 資料來源：{weather_data.get('source')}")
                print(f"⏰ 更新時間：{weather_data.get('update_time')}")
                
                # 顯示預報資料
                forecast = weather_data.get("forecast", [])
                for day_data in forecast:
                    print(f"📅 {day_data.get('date')} {day_data.get('weekday')}")
                    print(f"☁️ 天氣：{day_data.get('weather')}")
                    print(f"🌡️ 溫度：{day_data.get('temperature', {}).get('low')}°C - {day_data.get('temperature', {}).get('high')}°C")
                    print(f"☔ 降雨機率：{day_data.get('rain_probability')}")
                    if day_data.get('time_period'):
                        print(f"⏰ 時段：{day_data.get('time_period')}")
                    print()
            else:
                print(f"❌ {city} 天氣資料獲取失敗：{weather_data.get('error')}")
                
        except Exception as e:
            print(f"❌ {city} 測試發生錯誤：{e}")
        
        print("-" * 50)

def test_api_response_format():
    """測試API回應格式解析"""
    print("\n=== API 回應格式測試 ===\n")
    
    # 模擬API回應格式（根據官方文件）
    mock_response = {
        "success": "true",
        "result": {
            "resource_id": "F-C0032-001",
            "fields": [
                {"id": "locationName", "type": "text"},
                {"id": "startTime", "type": "timestamp"},
                {"id": "endTime", "type": "timestamp"},
                {"id": "elementName", "type": "text"},
                {"id": "parameterName", "type": "text"}
            ]
        },
        "records": {
            "datasetDescription": "36小時天氣預報",
            "location": [
                {
                    "locationName": "臺北市",
                    "weatherElement": [
                        {
                            "elementName": "Wx",
                            "time": [
                                {
                                    "startTime": "2025-05-24T06:00:00+08:00",
                                    "endTime": "2025-05-24T18:00:00+08:00",
                                    "parameter": {
                                        "parameterName": "多雲時晴",
                                        "parameterValue": "3"
                                    }
                                }
                            ]
                        },
                        {
                            "elementName": "PoP",
                            "time": [
                                {
                                    "startTime": "2025-05-24T06:00:00+08:00",
                                    "endTime": "2025-05-24T18:00:00+08:00",
                                    "parameter": {
                                        "parameterName": "20",
                                        "parameterUnit": "percent"
                                    }
                                }
                            ]
                        },
                        {
                            "elementName": "MinT",
                            "time": [
                                {
                                    "startTime": "2025-05-24T06:00:00+08:00",
                                    "endTime": "2025-05-24T18:00:00+08:00",
                                    "parameter": {
                                        "parameterName": "18",
                                        "parameterUnit": "C"
                                    }
                                }
                            ]
                        },
                        {
                            "elementName": "MaxT",
                            "time": [
                                {
                                    "startTime": "2025-05-24T06:00:00+08:00",
                                    "endTime": "2025-05-24T18:00:00+08:00",
                                    "parameter": {
                                        "parameterName": "25",
                                        "parameterUnit": "C"
                                    }
                                }
                            ]
                        },
                        {
                            "elementName": "CI",
                            "time": [
                                {
                                    "startTime": "2025-05-24T06:00:00+08:00",
                                    "endTime": "2025-05-24T18:00:00+08:00",
                                    "parameter": {
                                        "parameterName": "舒適"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    print("📋 模擬API回應格式：")
    print(json.dumps(mock_response, indent=2, ensure_ascii=False))
    
    # 測試解析
    weather_service = WeatherService()
    try:
        parsed_data = weather_service._parse_cwb_weather_data(mock_response, "台北", 1)
        print("\n✅ 解析成功：")
        print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\n❌ 解析失敗：{e}")

def test_city_mapping():
    """測試城市名稱映射"""
    print("\n=== 城市名稱映射測試 ===\n")
    
    weather_service = WeatherService()
    
    print("📍 支援的城市映射：")
    for user_city, standard_city in weather_service.city_mapping.items():
        print(f"  {user_city} → {standard_city}")
    
    print(f"\n📊 總共支援 {len(weather_service.city_mapping)} 個城市")

if __name__ == "__main__":
    test_city_mapping()
    test_api_response_format()
    test_real_api() 