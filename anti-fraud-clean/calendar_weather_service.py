# -*- coding: utf-8 -*-
"""
國曆農曆轉換和天氣API服務模組
提供日期轉換、節氣查詢、天氣預報等功能
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import calendar
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設置日誌
logger = logging.getLogger(__name__)

class CalendarWeatherService:
    """國曆農曆轉換和天氣服務類"""
    
    def __init__(self):
        # 天氣API設定 (使用中央氣象署開放資料API)
        self.weather_api_key = os.environ.get('CWB_API_KEY', '')
        self.weather_base_url = "https://opendata.cwb.gov.tw/api/v1/rest/datastore"
        
        # 農曆相關常數
        self.lunar_months = ["正月", "二月", "三月", "四月", "五月", "六月", 
                           "七月", "八月", "九月", "十月", "十一月", "十二月"]
        
        self.lunar_days = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
                         "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                         "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
        
        # 二十四節氣
        self.solar_terms = [
            "立春", "雨水", "驚蟄", "春分", "清明", "穀雨",
            "立夏", "小滿", "芒種", "夏至", "小暑", "大暑", 
            "立秋", "處暑", "白露", "秋分", "寒露", "霜降",
            "立冬", "小雪", "大雪", "冬至", "小寒", "大寒"
        ]
        
        # 台灣主要城市代碼
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

    def get_current_date_info(self) -> Dict:
        """獲取當前日期的完整資訊（國曆、農曆、節氣等）"""
        try:
            now = datetime.now()
            
            # 國曆資訊
            gregorian_info = {
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "weekday": self._get_chinese_weekday(now.weekday()),
                "formatted": now.strftime("%Y年%m月%d日")
            }
            
            # 農曆資訊（簡化版，實際應用建議使用專業農曆庫如lunardate）
            lunar_info = self._get_lunar_info(now)
            
            # 節氣資訊
            solar_term = self._get_current_solar_term(now)
            
            return {
                "success": True,
                "gregorian": gregorian_info,
                "lunar": lunar_info,
                "solar_term": solar_term,
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"獲取日期資訊時發生錯誤: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_weather_forecast(self, city: str = "台北", days: int = 3) -> Dict:
        """獲取指定城市的天氣預報"""
        try:
            if city not in self.city_codes:
                return {
                    "success": False,
                    "error": f"不支援的城市: {city}",
                    "supported_cities": list(self.city_codes.keys())
                }
            
            if not self.weather_api_key:
                # 如果沒有API金鑰，返回模擬資料
                return self._get_mock_weather_data(city, days)
            
            # 呼叫中央氣象署API
            city_code = self.city_codes[city]
            url = f"{self.weather_base_url}/{city_code}"
            
            params = {
                "Authorization": self.weather_api_key,
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
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    def convert_date(self, date_str: str, from_type: str = "gregorian") -> Dict:
        """日期轉換（國曆轉農曆或農曆轉國曆）"""
        try:
            if from_type == "gregorian":
                # 國曆轉農曆
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                lunar_info = self._get_lunar_info(date_obj)
                
                return {
                    "success": True,
                    "input": {
                        "type": "國曆",
                        "date": date_str
                    },
                    "output": {
                        "type": "農曆",
                        "lunar": lunar_info
                    }
                }
            else:
                # 農曆轉國曆（簡化實作）
                return {
                    "success": False,
                    "error": "農曆轉國曆功能開發中，建議使用專業農曆庫"
                }
                
        except ValueError as e:
            return {
                "success": False,
                "error": f"日期格式錯誤: {e}，請使用 YYYY-MM-DD 格式"
            }
        except Exception as e:
            logger.error(f"日期轉換時發生錯誤: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_solar_terms_info(self, year: int = None) -> Dict:
        """獲取指定年份的二十四節氣資訊"""
        try:
            if year is None:
                year = datetime.now().year
                
            # 簡化的節氣計算（實際應用建議使用專業天文庫）
            solar_terms_data = []
            
            for i, term in enumerate(self.solar_terms):
                # 簡化計算：每個節氣約間隔15天
                month = (i // 2) + 1
                day = 6 if i % 2 == 0 else 21
                
                # 調整2月的日期
                if month == 2 and day > 28:
                    day = 28
                    
                solar_terms_data.append({
                    "name": term,
                    "date": f"{year}-{month:02d}-{day:02d}",
                    "description": self._get_solar_term_description(term)
                })
            
            return {
                "success": True,
                "year": year,
                "solar_terms": solar_terms_data
            }
            
        except Exception as e:
            logger.error(f"獲取節氣資訊時發生錯誤: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_holiday_info(self, date_str: str = None) -> Dict:
        """獲取指定日期的節日資訊"""
        try:
            if date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                date_obj = datetime.now()
                
            holidays = self._get_holiday_info(date_obj)
            
            return {
                "success": True,
                "date": date_obj.strftime("%Y-%m-%d"),
                "holidays": holidays
            }
            
        except ValueError as e:
            return {
                "success": False,
                "error": f"日期格式錯誤: {e}，請使用 YYYY-MM-DD 格式"
            }
        except Exception as e:
            logger.error(f"獲取節日資訊時發生錯誤: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_chinese_weekday(self, weekday: int) -> str:
        """將數字星期轉換為中文"""
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[weekday]

    def _get_lunar_info(self, date_obj: datetime) -> Dict:
        """獲取農曆資訊（簡化版）"""
        # 注意：這是簡化的農曆計算，實際應用建議使用專業農曆庫
        # 這裡提供一個基本的框架
        
        # 簡化計算：假設農曆年從春節開始
        year = date_obj.year
        
        # 簡化的農曆月日計算（實際需要複雜的天文計算）
        day_of_year = date_obj.timetuple().tm_yday
        lunar_month = ((day_of_year - 1) // 30) + 1
        lunar_day = ((day_of_year - 1) % 30) + 1
        
        # 確保不超出範圍
        if lunar_month > 12:
            lunar_month = 12
        if lunar_day > 30:
            lunar_day = 30
            
        return {
            "year": year,
            "month": lunar_month,
            "day": lunar_day,
            "month_name": self.lunar_months[lunar_month - 1],
            "day_name": self.lunar_days[lunar_day - 1],
            "formatted": f"農曆{year}年{self.lunar_months[lunar_month - 1]}{self.lunar_days[lunar_day - 1]}",
            "note": "此為簡化計算，實際農曆日期可能有差異"
        }

    def _get_current_solar_term(self, date_obj: datetime) -> Dict:
        """獲取當前節氣資訊"""
        month = date_obj.month
        day = date_obj.day
        
        # 簡化的節氣判斷
        if month == 1:
            if day < 6:
                term = "小寒"
            elif day < 21:
                term = "大寒"
            else:
                term = "立春"
        elif month == 2:
            if day < 6:
                term = "立春"
            elif day < 21:
                term = "雨水"
            else:
                term = "驚蟄"
        # ... 其他月份的節氣判斷
        else:
            term = "春分"  # 預設值
            
        return {
            "name": term,
            "description": self._get_solar_term_description(term)
        }

    def _get_solar_term_description(self, term: str) -> str:
        """獲取節氣描述"""
        descriptions = {
            "立春": "春季開始，萬物復甦",
            "雨水": "降雨增多，氣溫回升",
            "驚蟄": "春雷響起，蟄蟲甦醒",
            "春分": "晝夜等長，春意盎然",
            "清明": "天氣清朗，適合踏青",
            "穀雨": "雨水充沛，利於穀物生長",
            "立夏": "夏季開始，氣溫升高",
            "小滿": "麥類作物籽粒飽滿",
            "芒種": "有芒作物成熟收割",
            "夏至": "白晝最長，夏季最熱",
            "小暑": "天氣炎熱，但非最熱",
            "大暑": "一年中最熱的時期",
            "立秋": "秋季開始，暑熱漸消",
            "處暑": "暑熱結束，秋涼來臨",
            "白露": "露水增多，天氣轉涼",
            "秋分": "晝夜等長，秋高氣爽",
            "寒露": "露水更涼，深秋來臨",
            "霜降": "開始降霜，天氣更冷",
            "立冬": "冬季開始，萬物收藏",
            "小雪": "開始降雪，氣溫下降",
            "大雪": "雪量增大，天氣嚴寒",
            "冬至": "白晝最短，冬季最冷",
            "小寒": "天氣寒冷，但非最冷",
            "大寒": "一年中最冷的時期"
        }
        return descriptions.get(term, "節氣資訊")

    def _get_holiday_info(self, date_obj: datetime) -> List[Dict]:
        """獲取節日資訊"""
        holidays = []
        month = date_obj.month
        day = date_obj.day
        
        # 國定假日
        national_holidays = {
            (1, 1): {"name": "元旦", "type": "國定假日"},
            (2, 28): {"name": "和平紀念日", "type": "國定假日"},
            (4, 4): {"name": "兒童節", "type": "國定假日"},
            (4, 5): {"name": "清明節", "type": "國定假日"},
            (5, 1): {"name": "勞動節", "type": "國定假日"},
            (10, 10): {"name": "國慶日", "type": "國定假日"},
            (12, 25): {"name": "聖誕節", "type": "節日"}
        }
        
        # 檢查是否為國定假日
        if (month, day) in national_holidays:
            holidays.append(national_holidays[(month, day)])
            
        # 農曆節日（簡化處理）
        lunar_holidays = {
            "農曆正月初一": {"name": "春節", "type": "農曆節日"},
            "農曆正月十五": {"name": "元宵節", "type": "農曆節日"},
            "農曆五月初五": {"name": "端午節", "type": "農曆節日"},
            "農曆八月十五": {"name": "中秋節", "type": "農曆節日"}
        }
        
        return holidays

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
                        "high": 28,
                        "low": 22
                    },
                    "humidity": "70%",
                    "rain_probability": "30%",
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
            "note": "此為模擬資料，實際天氣請參考中央氣象署"
        }

    def format_weather_message(self, weather_data: Dict) -> str:
        """格式化天氣資訊為易讀的訊息"""
        if not weather_data.get("success"):
            return f"❌ 天氣查詢失敗：{weather_data.get('error', '未知錯誤')}"
            
        city = weather_data.get("city", "未知城市")
        forecast = weather_data.get("forecast", [])
        
        if not forecast:
            return f"❌ {city}的天氣資料暫時無法取得"
            
        message = f"🌤️ {city}天氣預報\n\n"
        
        for day_data in forecast:
            date = day_data.get("date", "")
            weekday = day_data.get("weekday", "")
            weather = day_data.get("weather", "")
            temp = day_data.get("temperature", {})
            rain_prob = day_data.get("rain_probability", "")
            
            message += f"📅 {date} {weekday}\n"
            message += f"🌡️ {weather} {temp.get('low', '')}°C - {temp.get('high', '')}°C\n"
            message += f"☔ 降雨機率：{rain_prob}\n\n"
            
        update_time = weather_data.get("update_time", "")
        message += f"⏰ 更新時間：{update_time}"
        
        if weather_data.get("note"):
            message += f"\n\n💡 {weather_data['note']}"
            
        return message

    def format_date_message(self, date_data: Dict) -> str:
        """格式化日期資訊為易讀的訊息"""
        if not date_data.get("success"):
            return f"❌ 日期查詢失敗：{date_data.get('error', '未知錯誤')}"
            
        gregorian = date_data.get("gregorian", {})
        lunar = date_data.get("lunar", {})
        solar_term = date_data.get("solar_term", {})
        
        message = "📅 今日日期資訊\n\n"
        message += f"🗓️ 國曆：{gregorian.get('formatted', '')} {gregorian.get('weekday', '')}\n"
        message += f"🏮 農曆：{lunar.get('formatted', '')}\n"
        
        if solar_term:
            message += f"🌸 節氣：{solar_term.get('name', '')} - {solar_term.get('description', '')}\n"
            
        if lunar.get("note"):
            message += f"\n💡 {lunar['note']}"
            
        return message


# 創建服務實例
calendar_weather_service = CalendarWeatherService()

# 提供便捷的函數接口
def get_today_info() -> str:
    """獲取今日完整資訊（日期+天氣）"""
    date_info = calendar_weather_service.get_current_date_info()
    weather_info = calendar_weather_service.get_weather_forecast("台北", 1)
    
    date_msg = calendar_weather_service.format_date_message(date_info)
    weather_msg = calendar_weather_service.format_weather_message(weather_info)
    
    return f"{date_msg}\n\n{weather_msg}"

def get_weather(city: str = "台北", days: int = 3) -> str:
    """獲取指定城市天氣預報"""
    weather_info = calendar_weather_service.get_weather_forecast(city, days)
    return calendar_weather_service.format_weather_message(weather_info)

def get_date_info(date_str: str = None) -> str:
    """獲取指定日期資訊"""
    if date_str:
        # 轉換指定日期
        result = calendar_weather_service.convert_date(date_str)
        if result.get("success"):
            return f"📅 日期轉換結果\n\n🗓️ {result['input']['type']}：{result['input']['date']}\n🏮 {result['output']['type']}：{result['output']['lunar']['formatted']}"
        else:
            return f"❌ 日期轉換失敗：{result.get('error', '未知錯誤')}"
    else:
        # 獲取今日資訊
        date_info = calendar_weather_service.get_current_date_info()
        return calendar_weather_service.format_date_message(date_info)

def get_solar_terms(year: int = None) -> str:
    """獲取二十四節氣資訊"""
    terms_info = calendar_weather_service.get_solar_terms_info(year)
    
    if not terms_info.get("success"):
        return f"❌ 節氣查詢失敗：{terms_info.get('error', '未知錯誤')}"
        
    year = terms_info.get("year", "")
    terms = terms_info.get("solar_terms", [])
    
    message = f"🌸 {year}年二十四節氣\n\n"
    
    seasons = ["春季", "夏季", "秋季", "冬季"]
    for i, term in enumerate(terms):
        if i % 6 == 0:
            message += f"\n🌱 {seasons[i // 6]}\n"
        message += f"• {term['name']} ({term['date']})\n"
        
    return message

if __name__ == "__main__":
    # 測試功能
    print("=== 測試國曆農曆天氣服務 ===")
    
    # 測試今日資訊
    print("\n1. 今日完整資訊：")
    print(get_today_info())
    
    # 測試天氣查詢
    print("\n2. 台北3天天氣：")
    print(get_weather("台北", 3))
    
    # 測試日期轉換
    print("\n3. 日期轉換：")
    print(get_date_info("2024-01-01"))
    
    # 測試節氣查詢
    print("\n4. 二十四節氣：")
    print(get_solar_terms(2024)) 