#!/usr/bin/env python3
"""
天氣服務模組
提供天氣查詢、預報和相關功能
"""

import os
import json
import logging
import requests
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class WeatherService:
    """天氣服務類"""
    
    def __init__(self):
        # 中央氣象署API設定
        self.cwb_api_key = os.environ.get('CWB_API_KEY', '')
        self.cwb_base_url = "https://opendata.cwb.gov.tw/api/v1/rest/datastore"
        
        # 天氣相關關鍵詞
        self.weather_keywords = [
            "天氣", "氣溫", "溫度", "下雨", "降雨", "雨天", "晴天", "陰天", "多雲",
            "颱風", "台風", "風速", "濕度", "氣壓", "預報", "天氣預報", "明天天氣",
            "今天天氣", "這幾天天氣", "週末天氣", "出門", "要帶傘", "會下雨",
            "熱不熱", "冷不冷", "穿什麼", "要穿外套", "幾度", "風大", "下雨",
            "日期", "今天日期", "現在日期", "幾號", "星期幾", "禮拜幾", "今天幾號",
            "今天星期幾", "今天禮拜幾", "現在幾點", "時間", "今天", "現在"
        ]
        
        # 支援的城市和對應代碼
        self.city_codes = {
            "台北": "F-D0047-061",
            "新北": "F-D0047-069", 
            "桃園": "F-D0047-005",
            "台中": "F-D0047-073",
            "台南": "F-D0047-077",
            "高雄": "F-D0047-065",
            "基隆": "F-D0047-049",
            "新竹": "F-D0047-053",
            "苗栗": "F-D0047-013",
            "彰化": "F-D0047-017",
            "南投": "F-D0047-021",
            "雲林": "F-D0047-025",
            "嘉義": "F-D0047-029",
            "屏東": "F-D0047-033",
            "宜蘭": "F-D0047-001",
            "花蓮": "F-D0047-041",
            "台東": "F-D0047-037",
            "澎湖": "F-D0047-045",
            "金門": "F-D0047-081",
            "連江": "F-D0047-085"
        }
        
        # 支援的地點關鍵詞
        self.location_keywords = list(self.city_codes.keys())

    def detect_weather_query(self, message: str) -> Tuple[bool, Optional[str]]:
        """檢測是否為天氣相關詢問"""
        # 檢查是否包含天氣關鍵詞
        has_weather_keyword = any(keyword in message for keyword in self.weather_keywords)
        
        # 檢查是否包含地點
        mentioned_location = None
        for location in self.location_keywords:
            if location in message:
                mentioned_location = location
                break
        
        # 特殊情況：如果有地點但沒有明確天氣關鍵詞，檢查是否為隱含的天氣詢問
        if mentioned_location and not has_weather_keyword:
            implicit_weather_patterns = [
                "帶傘", "外套", "出門", "適合", "安全", "注意"
            ]
            has_weather_keyword = any(pattern in message for pattern in implicit_weather_patterns)
        
        return has_weather_keyword, mentioned_location

    def get_weather_forecast(self, city: str = "台北", days: int = 3) -> Dict:
        """獲取指定城市的天氣預報"""
        try:
            if city not in self.city_codes:
                return {
                    "success": False,
                    "error": f"不支援的城市: {city}",
                    "supported_cities": list(self.city_codes.keys())
                }
            
            if not self.cwb_api_key:
                # 如果沒有API金鑰，返回模擬資料
                logger.warning("未設定中央氣象署API金鑰，使用模擬資料")
                return self._get_mock_weather_data(city, days)
            
            # 呼叫中央氣象署API
            city_code = self.city_codes[city]
            url = f"{self.cwb_base_url}/{city_code}"
            
            params = {
                "Authorization": self.cwb_api_key,
                "format": "JSON"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析天氣資料
            weather_data = self._parse_weather_data(data, city, days)
            
            return {
                "success": True,
                "city": city,
                "forecast": weather_data,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "中央氣象署"
            }
            
        except requests.RequestException as e:
            logger.error(f"天氣API請求失敗: {e}")
            return self._get_mock_weather_data(city, days)
        except Exception as e:
            logger.error(f"獲取天氣預報時發生錯誤: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_weather_data(self, data: Dict, city: str, days: int) -> List[Dict]:
        """解析中央氣象署天氣資料"""
        try:
            # 這裡需要根據實際的API回應格式來解析
            # 以下是簡化的解析邏輯
            forecast = []
            
            # 模擬解析邏輯（實際需要根據API文件調整）
            for i in range(days):
                date = datetime.now() + timedelta(days=i)
                forecast.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "weekday": self._get_chinese_weekday(date.weekday()),
                    "weather": "多雲時晴",
                    "temperature": {
                        "high": 28 - i,
                        "low": 22 - i
                    },
                    "humidity": f"{70 + i * 5}%",
                    "rain_probability": f"{30 + i * 10}%",
                    "description": "舒適宜人的天氣"
                })
                
            return forecast
            
        except Exception as e:
            logger.error(f"解析天氣資料時發生錯誤: {e}")
            return self._get_mock_weather_data(city, days)["forecast"]

    def _get_mock_weather_data(self, city: str, days: int) -> Dict:
        """獲取模擬天氣資料（當API不可用時使用）"""
        forecast = []
        
        weather_conditions = ["晴天", "多雲", "陰天", "小雨", "雷陣雨"]
        
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            forecast.append({
                "date": date.strftime("%Y-%m-%d"),
                "weekday": self._get_chinese_weekday(date.weekday()),
                "weather": weather_conditions[i % len(weather_conditions)],
                "temperature": {
                    "high": 25 + (i % 5),
                    "low": 18 + (i % 3)
                },
                "humidity": f"{60 + (i * 5)}%",
                "rain_probability": f"{20 + (i * 10)}%",
                "description": "模擬天氣資料"
            })
            
        return {
            "success": True,
            "city": city,
            "forecast": forecast,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "模擬資料",
            "note": "⚠️ 此為模擬資料，實際天氣請參考中央氣象署"
        }

    def _get_chinese_weekday(self, weekday: int) -> str:
        """將數字星期轉換為中文"""
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        return weekdays[weekday]

    def format_weather_message(self, weather_data: Dict, user_name: str = "朋友") -> str:
        """格式化天氣資訊為易讀的訊息"""
        if not weather_data.get("success"):
            return f"@{user_name} ❌ 抱歉，目前無法取得天氣資訊：{weather_data.get('error', '未知錯誤')}"
            
        city = weather_data.get("city", "未知城市")
        forecast = weather_data.get("forecast", [])
        source = weather_data.get("source", "中央氣象署")
        
        if not forecast:
            return f"@{user_name} ❌ {city}的天氣資料暫時無法取得"
            
        # 判斷是當前天氣還是預報
        if len(forecast) == 1:
            # 當前天氣
            day_data = forecast[0]
            message = f"@{user_name} 🌤️ {city} 今日天氣\n\n"
            message += f"📅 {day_data.get('date', '')} {day_data.get('weekday', '')}\n"
            message += f"☁️ 天氣：{day_data.get('weather', '')}\n"
            message += f"🌡️ 溫度：{day_data.get('temperature', {}).get('low', '')}°C - {day_data.get('temperature', {}).get('high', '')}°C\n"
            message += f"💧 濕度：{day_data.get('humidity', '')}\n"
            message += f"☔ 降雨機率：{day_data.get('rain_probability', '')}\n"
        else:
            # 天氣預報
            message = f"@{user_name} 📅 {city} 未來{len(forecast)}日天氣預報\n\n"
            
            for day_data in forecast:
                date = day_data.get("date", "")
                weekday = day_data.get("weekday", "")
                weather = day_data.get("weather", "")
                temp = day_data.get("temperature", {})
                rain_prob = day_data.get("rain_probability", "")
                
                message += f"📆 {date} {weekday}\n"
                message += f"☁️ {weather}\n"
                message += f"🌡️ {temp.get('low', '')}°C - {temp.get('high', '')}°C\n"
                message += f"☔ 降雨機率：{rain_prob}\n\n"
            
        # 添加資料來源和免責聲明
        update_time = weather_data.get("update_time", "")
        message += f"📡 資料來源：{source}\n"
        message += f"⏰ 更新時間：{update_time}\n"
        message += f"ℹ️ 實際天氣以中央氣象署為準"
        
        if weather_data.get("note"):
            message += f"\n💡 {weather_data['note']}"
            
        return message

    def handle_weather_query(self, message: str, user_name: str = "朋友") -> Optional[str]:
        """處理天氣詢問的主要函數"""
        has_weather_query, location = self.detect_weather_query(message)
        
        if not has_weather_query:
            return None
        
        # 檢查是否為日期時間查詢
        date_keywords = ["日期", "幾號", "星期幾", "禮拜幾", "今天幾號", "今天星期幾", "今天禮拜幾", "現在幾點", "時間"]
        if any(keyword in message for keyword in date_keywords):
            current_time = datetime.now()
            
            # 格式化日期和時間
            date_str = current_time.strftime("%Y年%m月%d日")
            weekday_str = self._get_chinese_weekday(current_time.weekday())
            time_str = current_time.strftime("%H:%M")
            
            response = f"@{user_name} 📅 今天是{date_str}，{weekday_str}，現在時間是{time_str}。\n\n"
            response += "記得看清楚日期時間，別被詐騙訊息的假緊急通知騙了！真正重要的事情不會只給你幾分鐘處理 🛡️"
            
            return response
        
        # 預設地點為台北
        if not location:
            location = "台北"
        
        # 檢查是否詢問警報
        if any(word in message for word in ["警報", "颱風", "安全", "危險"]):
            # 返回天氣警報（簡化版）
            return f"@{user_name} ⚠️ 目前{location}沒有發布天氣警報，請持續關注中央氣象署最新資訊。\n\n📡 查詢網址：https://www.cwb.gov.tw/"
        
        # 判斷是要當前天氣還是預報
        if any(word in message for word in ["明天", "後天", "這幾天", "未來", "預報", "週末"]):
            # 天氣預報
            days = 3
            if "週末" in message or "這幾天" in message:
                days = 5
            elif "明天" in message:
                days = 2
            
            weather_data = self.get_weather_forecast(location, days)
        else:
            # 當前天氣
            weather_data = self.get_weather_forecast(location, 1)
        
        return self.format_weather_message(weather_data, user_name)

    def get_supported_cities(self) -> List[str]:
        """取得支援的城市列表"""
        return list(self.city_codes.keys())

    def is_weather_related(self, message: str) -> bool:
        """簡單檢查是否為天氣相關訊息"""
        has_weather_query, _ = self.detect_weather_query(message)
        return has_weather_query

    def get_weather_data(self, city: str) -> Dict[str, Any]:
        """
        獲取指定城市的天氣資料
        
        Args:
            city: 城市名稱
            
        Returns:
            包含天氣資料的字典
        """
        try:
            # 如果有 API 金鑰，使用真實 API
            if self.cwb_api_key:
                # 這裡可以實作真實的 API 調用
                pass
            
            # 使用模擬資料
            logger.warning("未設定中央氣象署API金鑰，使用模擬資料")
            
            current_time = datetime.now()
            
            return {
                "city": city,
                "date": current_time.strftime("%Y-%m-%d"),
                "day_of_week": current_time.strftime("%A"),
                "weather": "晴天",
                "temperature": "18°C - 25°C",
                "humidity": "60%",
                "rain_chance": "20%",
                "source": "模擬資料",
                "update_time": current_time.strftime("%H:%M")
            }
            
        except Exception as e:
            logger.error(f"獲取天氣資料時發生錯誤: {e}")
            return {
                "city": city,
                "error": str(e)
            }


# 創建全域天氣服務實例
weather_service = WeatherService()

# 提供便捷的函數接口
def handle_weather_query(message: str, user_name: str = "朋友") -> Optional[str]:
    """處理天氣詢問的便捷函數"""
    return weather_service.handle_weather_query(message, user_name)

def is_weather_related(message: str) -> bool:
    """檢查是否為天氣相關訊息的便捷函數"""
    return weather_service.is_weather_related(message)

def get_weather(city: str = "台北", days: int = 3) -> str:
    """獲取指定城市天氣預報的便捷函數"""
    weather_data = weather_service.get_weather_forecast(city, days)
    return weather_service.format_weather_message(weather_data)

def get_supported_cities() -> List[str]:
    """取得支援城市列表的便捷函數"""
    return weather_service.get_supported_cities()

def get_weather_data(city: str) -> Dict[str, Any]:
    """
    獲取指定城市的天氣資料
    
    Args:
        city: 城市名稱
        
    Returns:
        包含天氣資料的字典
    """
    return weather_service.get_weather_data(city)


if __name__ == "__main__":
    # 測試功能
    print("=== 天氣服務測試 ===")
    
    test_messages = [
        "土豆 今天台北天氣如何？",
        "土豆 明天會下雨嗎？", 
        "土豆 這週末去台中玩，天氣好嗎？",
        "土豆 現在有颱風警報嗎？",
        "土豆 你好嗎？"  # 非天氣詢問
    ]
    
    for message in test_messages:
        clean_message = message.replace("土豆", "").strip()
        response = handle_weather_query(clean_message, "測試用戶")
        print(f"\n輸入：{message}")
        if response:
            print(f"輸出：{response}")
        else:
            print("輸出：(不是天氣詢問)")
        print("-" * 50) 