#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天氣功能整合示例
展示如何將天氣功能整合到主程式的handle_message函數中
"""

import json
import random
from datetime import datetime, timedelta
from test_weather_comprehensive import WeatherSimulator, format_weather_response, format_alert_response

class WeatherIntegration:
    """天氣功能整合類"""
    
    def __init__(self):
        self.weather_sim = WeatherSimulator()
        
        # 天氣相關關鍵詞
        self.weather_keywords = [
            "天氣", "氣溫", "溫度", "下雨", "降雨", "雨天", "晴天", "陰天", "多雲",
            "颱風", "台風", "風速", "濕度", "氣壓", "預報", "天氣預報", "明天天氣",
            "今天天氣", "這幾天天氣", "週末天氣", "出門", "要帶傘", "會下雨",
            "熱不熱", "冷不冷", "穿什麼", "要穿外套", "幾度", "風大", "下雨"
        ]
        
        # 地點關鍵詞
        self.location_keywords = list(self.weather_sim.stations.keys())

    def detect_weather_query(self, message):
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

    def handle_weather_query(self, message, user_name="朋友"):
        """處理天氣詢問"""
        has_weather_query, location = self.detect_weather_query(message)
        
        if not has_weather_query:
            return None
        
        # 預設地點為台北
        if not location:
            location = "台北"
        
        # 檢查是否詢問警報
        if any(word in message for word in ["警報", "颱風", "安全", "危險"]):
            # 返回天氣警報
            alert_data = self.weather_sim.generate_weather_alert("大雨")
            alert_response = format_alert_response(alert_data)
            return f"@{user_name} ⚠️ 目前天氣警報資訊：\n\n{alert_response}"
        
        # 判斷是要當前天氣還是預報
        if any(word in message for word in ["明天", "後天", "這幾天", "未來", "預報", "週末"]):
            # 天氣預報
            days = 3
            if "週末" in message or "這幾天" in message:
                days = 5
            elif "明天" in message:
                days = 2
            
            weather_data = self.weather_sim.generate_forecast_weather(location, days)
            response = format_weather_response(weather_data)
            
            # 添加個人化開頭
            personal_intro = f"@{user_name} 我來幫您查詢{location}的天氣預報：\n\n"
            return personal_intro + response
        else:
            # 當前天氣
            weather_data = self.weather_sim.generate_current_weather(location)
            response = format_weather_response(weather_data)
            
            # 添加個人化開頭
            personal_intro = f"@{user_name} 我來幫您查詢{location}目前的天氣狀況：\n\n"
            return personal_intro + response

# 整合到主程式的示例代碼
def enhanced_handle_message_example(event):
    """
    增強版的handle_message函數示例
    展示如何整合天氣功能
    """
    
    # 初始化天氣功能
    weather_integration = WeatherIntegration()
    
    # 獲取用戶訊息和資訊
    user_message = event.message.text
    user_id = event.source.user_id
    reply_token = event.reply_token
    
    # 獲取用戶顯示名稱
    display_name = "朋友"  # 預設值
    try:
        profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
    except:
        pass
    
    # 初始化回應變數
    reply_text = ""
    is_fraud_related = False
    
    # 檢查是否包含觸發關鍵詞
    bot_trigger_keyword = "土豆"
    if bot_trigger_keyword in user_message:
        # 移除觸發關鍵詞
        clean_message = user_message.replace(bot_trigger_keyword, "").strip()
        
        # 1. 優先檢查天氣詢問
        weather_response = weather_integration.handle_weather_query(clean_message, display_name)
        if weather_response:
            reply_text = weather_response
        
        # 2. 檢查是否為詐騙相關詢問
        elif should_perform_fraud_analysis(clean_message):
            is_fraud_related = True
            # 進行詐騙分析...
            reply_text = "進行詐騙分析..."
        
        # 3. 一般閒聊模式
        else:
            # 使用AI進行閒聊回應
            reply_text = f"@{display_name} 您好！有什麼我可以幫助您的嗎？"
    
    # 發送回應
    if reply_text:
        # 檢查訊息長度限制
        if len(reply_text) > 4900:
            reply_text = reply_text[:4900] + "\n\n⚠️ 訊息過長已截斷，完整資訊請分次詢問"
        
        # 發送回應
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply_text)
        )

def test_integration_examples():
    """測試整合示例"""
    weather_integration = WeatherIntegration()
    
    print("🔧 天氣功能整合示例測試")
    print("=" * 60)
    
    # 模擬各種用戶詢問
    test_cases = [
        {
            "message": "土豆 今天台北天氣如何？",
            "user": "小明",
            "expected": "當前天氣查詢"
        },
        {
            "message": "土豆 明天會下雨嗎？",
            "user": "小華",
            "expected": "明天天氣預報"
        },
        {
            "message": "土豆 這週末去台中玩，天氣好嗎？",
            "user": "小美",
            "expected": "週末天氣預報"
        },
        {
            "message": "土豆 現在有颱風警報嗎？",
            "user": "阿強",
            "expected": "天氣警報查詢"
        },
        {
            "message": "土豆 你好嗎？",
            "user": "小玲",
            "expected": "一般閒聊"
        },
        {
            "message": "土豆 這個網址安全嗎？http://example.com",
            "user": "大雄",
            "expected": "詐騙檢測"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 測試案例 {i}：{test_case['expected']}")
        print(f"👤 用戶：{test_case['user']}")
        print(f"💬 訊息：{test_case['message']}")
        print("-" * 50)
        
        # 模擬處理邏輯
        clean_message = test_case['message'].replace("土豆", "").strip()
        
        # 檢查天氣詢問
        weather_response = weather_integration.handle_weather_query(clean_message, test_case['user'])
        
        if weather_response:
            print("🤖 處理結果：天氣功能觸發")
            response_preview = weather_response.split('\n')[0]
            print(f"📤 回應預覽：{response_preview}...")
        elif "網址" in clean_message or "http" in clean_message:
            print("🤖 處理結果：詐騙檢測功能觸發")
            print("📤 回應預覽：進行網址安全性分析...")
        else:
            print("🤖 處理結果：一般閒聊模式")
            print(f"📤 回應預覽：@{test_case['user']} 您好！有什麼我可以幫助您的嗎？")
        
        print("=" * 60)
    
    print("\n✅ 整合示例測試完成！")
    print("\n💡 整合要點：")
    print("1. 在handle_message函數開頭初始化WeatherIntegration")
    print("2. 移除觸發關鍵詞後，優先檢查天氣詢問")
    print("3. 天氣功能無匹配時，再檢查詐騙分析")
    print("4. 最後進入一般閒聊模式")
    print("5. 注意訊息長度限制（5000字元）")

if __name__ == "__main__":
    test_integration_examples() 