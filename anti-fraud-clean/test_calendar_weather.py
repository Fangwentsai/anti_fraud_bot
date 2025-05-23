# -*- coding: utf-8 -*-
"""
國曆農曆天氣服務測試文件
Test file for Calendar Weather Service
"""

import unittest
from datetime import datetime
from calendar_weather_service import (
    CalendarWeatherService,
    get_today_info,
    get_weather,
    get_date_info,
    get_solar_terms
)

class TestCalendarWeatherService(unittest.TestCase):
    """國曆農曆天氣服務測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.service = CalendarWeatherService()
    
    def test_get_current_date_info(self):
        """測試獲取當前日期資訊"""
        result = self.service.get_current_date_info()
        
        self.assertTrue(result.get("success"))
        self.assertIn("gregorian", result)
        self.assertIn("lunar", result)
        self.assertIn("solar_term", result)
        
        # 檢查國曆資訊
        gregorian = result["gregorian"]
        self.assertIn("year", gregorian)
        self.assertIn("month", gregorian)
        self.assertIn("day", gregorian)
        self.assertIn("weekday", gregorian)
        self.assertIn("formatted", gregorian)
        
        # 檢查農曆資訊
        lunar = result["lunar"]
        self.assertIn("year", lunar)
        self.assertIn("month", lunar)
        self.assertIn("day", lunar)
        self.assertIn("formatted", lunar)
    
    def test_get_weather_forecast_supported_city(self):
        """測試支援城市的天氣預報"""
        result = self.service.get_weather_forecast("台北", 3)
        
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("city"), "台北")
        self.assertIn("forecast", result)
        self.assertEqual(len(result["forecast"]), 3)
        
        # 檢查預報資料格式
        for day_forecast in result["forecast"]:
            self.assertIn("date", day_forecast)
            self.assertIn("weekday", day_forecast)
            self.assertIn("weather", day_forecast)
            self.assertIn("temperature", day_forecast)
    
    def test_get_weather_forecast_unsupported_city(self):
        """測試不支援城市的天氣預報"""
        result = self.service.get_weather_forecast("不存在的城市", 3)
        
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
        self.assertIn("supported_cities", result)
    
    def test_convert_date_gregorian_to_lunar(self):
        """測試國曆轉農曆"""
        result = self.service.convert_date("2024-01-01", "gregorian")
        
        self.assertTrue(result.get("success"))
        self.assertIn("input", result)
        self.assertIn("output", result)
        
        input_data = result["input"]
        self.assertEqual(input_data["type"], "國曆")
        self.assertEqual(input_data["date"], "2024-01-01")
        
        output_data = result["output"]
        self.assertEqual(output_data["type"], "農曆")
        self.assertIn("lunar", output_data)
    
    def test_convert_date_invalid_format(self):
        """測試無效日期格式"""
        result = self.service.convert_date("invalid-date", "gregorian")
        
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
    
    def test_get_solar_terms_info(self):
        """測試獲取二十四節氣資訊"""
        result = self.service.get_solar_terms_info(2024)
        
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("year"), 2024)
        self.assertIn("solar_terms", result)
        self.assertEqual(len(result["solar_terms"]), 24)
        
        # 檢查節氣資料格式
        for term in result["solar_terms"]:
            self.assertIn("name", term)
            self.assertIn("date", term)
            self.assertIn("description", term)
    
    def test_get_holiday_info(self):
        """測試獲取節日資訊"""
        # 測試元旦
        result = self.service.get_holiday_info("2024-01-01")
        
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("date"), "2024-01-01")
        self.assertIn("holidays", result)
        
        # 檢查是否包含元旦
        holidays = result["holidays"]
        holiday_names = [h["name"] for h in holidays]
        self.assertIn("元旦", holiday_names)
    
    def test_format_weather_message(self):
        """測試天氣訊息格式化"""
        # 模擬天氣資料
        weather_data = {
            "success": True,
            "city": "台北",
            "forecast": [
                {
                    "date": "2024-01-01",
                    "weekday": "星期一",
                    "weather": "晴天",
                    "temperature": {"high": 25, "low": 18},
                    "rain_probability": "10%"
                }
            ],
            "update_time": "2024-01-01 12:00:00"
        }
        
        message = self.service.format_weather_message(weather_data)
        
        self.assertIn("台北天氣預報", message)
        self.assertIn("2024-01-01", message)
        self.assertIn("星期一", message)
        self.assertIn("晴天", message)
        self.assertIn("25°C", message)
        self.assertIn("18°C", message)
    
    def test_format_date_message(self):
        """測試日期訊息格式化"""
        # 模擬日期資料
        date_data = {
            "success": True,
            "gregorian": {
                "formatted": "2024年01月01日",
                "weekday": "星期一"
            },
            "lunar": {
                "formatted": "農曆2024年正月初一"
            },
            "solar_term": {
                "name": "小寒",
                "description": "天氣寒冷，但非最冷"
            }
        }
        
        message = self.service.format_date_message(date_data)
        
        self.assertIn("今日日期資訊", message)
        self.assertIn("2024年01月01日", message)
        self.assertIn("星期一", message)
        self.assertIn("農曆2024年正月初一", message)
        self.assertIn("小寒", message)


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函數測試類"""
    
    def test_get_today_info(self):
        """測試獲取今日完整資訊"""
        result = get_today_info()
        
        self.assertIsInstance(result, str)
        self.assertIn("今日日期資訊", result)
        self.assertIn("天氣預報", result)
    
    def test_get_weather(self):
        """測試獲取天氣預報"""
        result = get_weather("台北", 3)
        
        self.assertIsInstance(result, str)
        self.assertIn("台北天氣預報", result)
    
    def test_get_date_info_without_param(self):
        """測試獲取今日日期資訊"""
        result = get_date_info()
        
        self.assertIsInstance(result, str)
        self.assertIn("今日日期資訊", result)
    
    def test_get_date_info_with_param(self):
        """測試日期轉換"""
        result = get_date_info("2024-01-01")
        
        self.assertIsInstance(result, str)
        self.assertIn("日期轉換結果", result)
    
    def test_get_solar_terms(self):
        """測試獲取二十四節氣"""
        result = get_solar_terms(2024)
        
        self.assertIsInstance(result, str)
        self.assertIn("2024年二十四節氣", result)
        self.assertIn("立春", result)
        self.assertIn("春分", result)
        self.assertIn("夏至", result)
        self.assertIn("冬至", result)


def run_manual_tests():
    """手動測試函數"""
    print("=== 手動測試國曆農曆天氣服務 ===\n")
    
    # 測試1：今日完整資訊
    print("1. 今日完整資訊：")
    print(get_today_info())
    print("\n" + "="*50 + "\n")
    
    # 測試2：天氣查詢
    print("2. 台北3天天氣：")
    print(get_weather("台北", 3))
    print("\n" + "="*50 + "\n")
    
    # 測試3：高雄天氣
    print("3. 高雄天氣：")
    print(get_weather("高雄", 2))
    print("\n" + "="*50 + "\n")
    
    # 測試4：日期轉換
    print("4. 日期轉換（2024-01-01）：")
    print(get_date_info("2024-01-01"))
    print("\n" + "="*50 + "\n")
    
    # 測試5：今日日期
    print("5. 今日日期資訊：")
    print(get_date_info())
    print("\n" + "="*50 + "\n")
    
    # 測試6：二十四節氣
    print("6. 2024年二十四節氣：")
    print(get_solar_terms(2024))
    print("\n" + "="*50 + "\n")
    
    # 測試7：不支援的城市
    print("7. 不支援的城市測試：")
    print(get_weather("不存在的城市", 1))
    print("\n" + "="*50 + "\n")
    
    # 測試8：服務實例直接測試
    print("8. 服務實例測試：")
    service = CalendarWeatherService()
    
    # 測試節日資訊
    holiday_info = service.get_holiday_info("2024-01-01")
    print(f"元旦節日資訊：{holiday_info}")
    
    # 測試支援的城市列表
    print(f"支援的城市：{list(service.city_codes.keys())}")


if __name__ == "__main__":
    # 選擇測試模式
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        # 手動測試模式
        run_manual_tests()
    else:
        # 單元測試模式
        unittest.main() 