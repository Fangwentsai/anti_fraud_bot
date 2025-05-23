#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天氣功能綜合測試程序
模擬各種天氣狀況，測試回傳資訊
資料來源：中央氣象署
"""

import json
import random
from datetime import datetime, timedelta
import requests

class WeatherSimulator:
    """天氣模擬器 - 模擬中央氣象署資料格式"""
    
    def __init__(self):
        # 中央氣象署測站代碼
        self.stations = {
            "台北": "466920",
            "新北": "466880", 
            "桃園": "467050",
            "台中": "467490",
            "台南": "467410",
            "高雄": "467440",
            "基隆": "466940",
            "新竹": "467060",
            "苗栗": "467080",
            "彰化": "467240",
            "南投": "467270",
            "雲林": "467300",
            "嘉義": "467480",
            "屏東": "467590",
            "宜蘭": "466990",
            "花蓮": "467620",
            "台東": "467660",
            "澎湖": "467350",
            "金門": "467110",
            "馬祖": "467990"
        }
        
        # 天氣現象代碼 (中央氣象署標準)
        self.weather_codes = {
            "01": "晴天",
            "02": "晴時多雲", 
            "03": "多雲時晴",
            "04": "多雲",
            "05": "多雲時陰",
            "06": "陰天",
            "07": "陰時多雲",
            "08": "陰短暫雨",
            "09": "陰時有雨",
            "10": "陰天有雨",
            "11": "多雲短暫雨",
            "12": "多雲時有雨", 
            "13": "晴時有雨",
            "14": "晴短暫雨",
            "15": "晴時多雲短暫雨",
            "16": "多雲短暫陣雨",
            "17": "晴短暫陣雨",
            "18": "多雲時晴短暫陣雨",
            "19": "晴時多雲短暫陣雨",
            "20": "陰短暫陣雨",
            "21": "陰時有陣雨",
            "22": "陰天有陣雨",
            "23": "多雲有陣雨",
            "24": "晴時有陣雨",
            "25": "晴有陣雨",
            "26": "多雲時晴有陣雨",
            "27": "晴時多雲有陣雨",
            "28": "陰有雷雨",
            "29": "多雲有雷雨",
            "30": "晴有雷雨"
        }
        
        # 風向代碼
        self.wind_directions = {
            "N": "北風",
            "NNE": "北北東風", 
            "NE": "東北風",
            "ENE": "東北東風",
            "E": "東風",
            "ESE": "東南東風",
            "SE": "東南風", 
            "SSE": "南南東風",
            "S": "南風",
            "SSW": "南南西風",
            "SW": "西南風",
            "WSW": "西南西風", 
            "W": "西風",
            "WNW": "西北西風",
            "NW": "西北風",
            "NNW": "北北西風",
            "C": "無風"
        }

    def generate_current_weather(self, city="台北"):
        """生成當前天氣資料"""
        now = datetime.now()
        
        # 隨機選擇天氣狀況
        weather_code = random.choice(list(self.weather_codes.keys()))
        weather_desc = self.weather_codes[weather_code]
        
        # 根據天氣狀況調整溫度範圍
        if weather_code in ["01", "02", "03"]:  # 晴天
            temp_range = (25, 35)
            humidity_range = (40, 65)
        elif weather_code in ["04", "05", "06", "07"]:  # 多雲陰天
            temp_range = (20, 30)
            humidity_range = (55, 75)
        else:  # 雨天
            temp_range = (18, 28)
            humidity_range = (70, 95)
            
        temperature = round(random.uniform(*temp_range), 1)
        humidity = random.randint(*humidity_range)
        
        # 風向風速
        wind_dir = random.choice(list(self.wind_directions.keys()))
        wind_speed = round(random.uniform(0.5, 8.0), 1)
        
        # 氣壓
        pressure = round(random.uniform(1005, 1025), 1)
        
        # 降雨量 (根據天氣狀況)
        if weather_code in ["08", "09", "10", "11", "12", "13", "14", "15"]:
            rainfall = round(random.uniform(0.1, 5.0), 1)
        elif weather_code in ["16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27"]:
            rainfall = round(random.uniform(1.0, 15.0), 1)
        elif weather_code in ["28", "29", "30"]:
            rainfall = round(random.uniform(5.0, 30.0), 1)
        else:
            rainfall = 0.0
            
        return {
            "success": True,
            "records": {
                "location": [
                    {
                        "locationName": city,
                        "stationId": self.stations.get(city, "466920"),
                        "time": {
                            "obsTime": now.strftime("%Y-%m-%d %H:%M:%S")
                        },
                        "weatherElement": [
                            {
                                "elementName": "Weather",
                                "elementValue": weather_desc
                            },
                            {
                                "elementName": "Temp", 
                                "elementValue": str(temperature)
                            },
                            {
                                "elementName": "Humidity",
                                "elementValue": str(humidity)
                            },
                            {
                                "elementName": "WindDirection",
                                "elementValue": self.wind_directions[wind_dir]
                            },
                            {
                                "elementName": "WindSpeed",
                                "elementValue": str(wind_speed)
                            },
                            {
                                "elementName": "Pressure",
                                "elementValue": str(pressure)
                            },
                            {
                                "elementName": "Rainfall",
                                "elementValue": str(rainfall)
                            }
                        ]
                    }
                ]
            },
            "dataSource": "中央氣象署",
            "disclaimer": "實際天氣以中央氣象署為準"
        }

    def generate_forecast_weather(self, city="台北", days=3):
        """生成天氣預報資料"""
        forecasts = []
        
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            
            # 隨機天氣
            weather_code = random.choice(list(self.weather_codes.keys()))
            weather_desc = self.weather_codes[weather_code]
            
            # 溫度範圍
            if weather_code in ["01", "02", "03"]:
                min_temp = random.randint(22, 28)
                max_temp = min_temp + random.randint(6, 12)
            elif weather_code in ["04", "05", "06", "07"]:
                min_temp = random.randint(18, 25)
                max_temp = min_temp + random.randint(5, 10)
            else:
                min_temp = random.randint(16, 23)
                max_temp = min_temp + random.randint(4, 8)
            
            # 降雨機率
            if weather_code in ["01", "02", "03"]:
                rain_prob = random.randint(0, 20)
            elif weather_code in ["04", "05", "06", "07"]:
                rain_prob = random.randint(10, 40)
            else:
                rain_prob = random.randint(60, 90)
            
            forecasts.append({
                "date": date.strftime("%Y-%m-%d"),
                "dayOfWeek": ["一", "二", "三", "四", "五", "六", "日"][date.weekday()],
                "weather": weather_desc,
                "weatherCode": weather_code,
                "minTemp": str(min_temp),
                "maxTemp": str(max_temp),
                "rainProbability": str(rain_prob)
            })
        
        return {
            "success": True,
            "records": {
                "location": [
                    {
                        "locationName": city,
                        "weatherElement": [
                            {
                                "elementName": "WeatherForecast",
                                "time": forecasts
                            }
                        ]
                    }
                ]
            },
            "dataSource": "中央氣象署",
            "disclaimer": "實際天氣以中央氣象署為準"
        }

    def generate_weather_alert(self, alert_type="大雨"):
        """生成天氣警報資料"""
        now = datetime.now()
        
        alert_types = {
            "大雨": {
                "title": "大雨特報",
                "level": "注意",
                "color": "yellow",
                "description": "24小時累積雨量達80毫米以上，或時雨量達40毫米以上"
            },
            "豪雨": {
                "title": "豪雨特報", 
                "level": "警告",
                "color": "orange",
                "description": "24小時累積雨量達200毫米以上，或3小時累積雨量達100毫米以上"
            },
            "大豪雨": {
                "title": "大豪雨特報",
                "level": "嚴重警告", 
                "color": "red",
                "description": "24小時累積雨量達350毫米以上"
            },
            "強風": {
                "title": "強風特報",
                "level": "注意",
                "color": "yellow", 
                "description": "平均風力達6級以上或陣風達8級以上"
            },
            "高溫": {
                "title": "高溫資訊",
                "level": "注意",
                "color": "orange",
                "description": "氣溫達攝氏36度以上"
            }
        }
        
        alert_info = alert_types.get(alert_type, alert_types["大雨"])
        
        return {
            "success": True,
            "records": {
                "hazard": [
                    {
                        "hazardId": f"W{now.strftime('%Y%m%d%H%M')}",
                        "hazardName": alert_info["title"],
                        "status": "發布",
                        "level": alert_info["level"],
                        "effectiveTime": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "expireTime": (now + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
                        "description": alert_info["description"],
                        "affectedAreas": ["台北市", "新北市", "桃園市", "基隆市"],
                        "instruction": "請注意防範，避免前往山區及河川等危險區域"
                    }
                ]
            },
            "dataSource": "中央氣象署",
            "disclaimer": "實際天氣以中央氣象署為準"
        }

def format_weather_response(weather_data):
    """格式化天氣回應訊息"""
    if not weather_data.get("success"):
        return "❌ 無法取得天氣資訊，請稍後再試"
    
    location = weather_data["records"]["location"][0]
    city = location["locationName"]
    
    # 檢查是否有time欄位（當前天氣）
    if "time" in location:
        # 當前天氣
        elements = {elem["elementName"]: elem["elementValue"] 
                   for elem in location["weatherElement"]}
        
        obs_time = location.get("time", {}).get("obsTime", "")
        
        response = f"🌤️ {city} 當前天氣\n"
        response += f"📅 觀測時間：{obs_time}\n\n"
        response += f"☁️ 天氣：{elements.get('Weather', 'N/A')}\n"
        response += f"🌡️ 溫度：{elements.get('Temp', 'N/A')}°C\n"
        response += f"💧 濕度：{elements.get('Humidity', 'N/A')}%\n"
        response += f"💨 風向風速：{elements.get('WindDirection', 'N/A')} {elements.get('WindSpeed', 'N/A')}m/s\n"
        response += f"📊 氣壓：{elements.get('Pressure', 'N/A')}hPa\n"
        response += f"🌧️ 降雨量：{elements.get('Rainfall', 'N/A')}mm\n\n"
        response += f"📡 資料來源：{weather_data.get('dataSource', '中央氣象署')}\n"
        response += f"ℹ️ {weather_data.get('disclaimer', '實際天氣以中央氣象署為準')}"
        
    else:
        # 天氣預報
        forecasts = location["weatherElement"][0]["time"]
        response = f"📅 {city} 未來{len(forecasts)}日天氣預報\n\n"
        
        for forecast in forecasts:
            response += f"📆 {forecast['date']} (週{forecast['dayOfWeek']})\n"
            response += f"☁️ {forecast['weather']}\n"
            response += f"🌡️ {forecast['minTemp']}°C ~ {forecast['maxTemp']}°C\n"
            response += f"🌧️ 降雨機率：{forecast['rainProbability']}%\n\n"
        
        response += f"📡 資料來源：{weather_data.get('dataSource', '中央氣象署')}\n"
        response += f"ℹ️ {weather_data.get('disclaimer', '實際天氣以中央氣象署為準')}"
    
    return response

def format_alert_response(alert_data):
    """格式化天氣警報回應訊息"""
    if not alert_data.get("success"):
        return "❌ 無法取得天氣警報資訊"
    
    hazards = alert_data["records"]["hazard"]
    if not hazards:
        return "✅ 目前無天氣警報發布"
    
    response = "⚠️ 天氣警報資訊\n\n"
    
    for hazard in hazards:
        level_emoji = {
            "注意": "🟡",
            "警告": "🟠", 
            "嚴重警告": "🔴"
        }.get(hazard["level"], "⚠️")
        
        response += f"{level_emoji} {hazard['hazardName']}\n"
        response += f"📊 等級：{hazard['level']}\n"
        response += f"⏰ 發布時間：{hazard['effectiveTime']}\n"
        response += f"⏳ 有效至：{hazard['expireTime']}\n"
        response += f"📝 說明：{hazard['description']}\n"
        response += f"🗺️ 影響區域：{', '.join(hazard['affectedAreas'])}\n"
        response += f"💡 建議：{hazard['instruction']}\n\n"
    
    response += f"📡 資料來源：{alert_data.get('dataSource', '中央氣象署')}\n"
    response += f"ℹ️ {alert_data.get('disclaimer', '實際天氣以中央氣象署為準')}"
    
    return response

def test_weather_scenarios():
    """測試各種天氣情境"""
    simulator = WeatherSimulator()
    
    print("=" * 60)
    print("🌤️ 天氣功能綜合測試")
    print("=" * 60)
    
    # 測試不同城市的當前天氣
    cities = ["台北", "台中", "高雄", "花蓮", "澎湖"]
    
    print("\n📍 測試不同城市當前天氣：")
    print("-" * 40)
    
    for city in cities:
        print(f"\n🏙️ 測試城市：{city}")
        weather_data = simulator.generate_current_weather(city)
        response = format_weather_response(weather_data)
        print(response)
        print("-" * 40)
    
    # 測試天氣預報
    print("\n📅 測試天氣預報：")
    print("-" * 40)
    
    forecast_data = simulator.generate_forecast_weather("台北", 5)
    forecast_response = format_weather_response(forecast_data)
    print(forecast_response)
    print("-" * 40)
    
    # 測試各種天氣警報
    print("\n⚠️ 測試天氣警報：")
    print("-" * 40)
    
    alert_types = ["大雨", "豪雨", "大豪雨", "強風", "高溫"]
    
    for alert_type in alert_types:
        print(f"\n🚨 測試警報類型：{alert_type}")
        alert_data = simulator.generate_weather_alert(alert_type)
        alert_response = format_alert_response(alert_data)
        print(alert_response)
        print("-" * 40)
    
    # 測試極端天氣情境
    print("\n🌪️ 測試極端天氣情境：")
    print("-" * 40)
    
    # 模擬颱風天
    print("\n🌀 颱風天氣模擬：")
    typhoon_weather = {
        "success": True,
        "records": {
            "location": [
                {
                    "locationName": "台北",
                    "stationId": "466920",
                    "time": {
                        "obsTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    "weatherElement": [
                        {"elementName": "Weather", "elementValue": "陰天有雷雨"},
                        {"elementName": "Temp", "elementValue": "24.5"},
                        {"elementName": "Humidity", "elementValue": "92"},
                        {"elementName": "WindDirection", "elementValue": "東北風"},
                        {"elementName": "WindSpeed", "elementValue": "12.8"},
                        {"elementName": "Pressure", "elementValue": "995.2"},
                        {"elementName": "Rainfall", "elementValue": "45.6"}
                    ]
                }
            ]
        },
        "dataSource": "中央氣象署",
        "disclaimer": "實際天氣以中央氣象署為準"
    }
    
    typhoon_response = format_weather_response(typhoon_weather)
    print(typhoon_response)
    
    # 模擬高溫炎熱天氣
    print("\n🔥 高溫天氣模擬：")
    hot_weather = {
        "success": True,
        "records": {
            "location": [
                {
                    "locationName": "台中",
                    "stationId": "467490", 
                    "time": {
                        "obsTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    "weatherElement": [
                        {"elementName": "Weather", "elementValue": "晴天"},
                        {"elementName": "Temp", "elementValue": "38.2"},
                        {"elementName": "Humidity", "elementValue": "45"},
                        {"elementName": "WindDirection", "elementValue": "西南風"},
                        {"elementName": "WindSpeed", "elementValue": "2.1"},
                        {"elementName": "Pressure", "elementValue": "1015.8"},
                        {"elementName": "Rainfall", "elementValue": "0.0"}
                    ]
                }
            ]
        },
        "dataSource": "中央氣象署",
        "disclaimer": "實際天氣以中央氣象署為準"
    }
    
    hot_response = format_weather_response(hot_weather)
    print(hot_response)
    
    print("\n✅ 天氣功能測試完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_weather_scenarios() 