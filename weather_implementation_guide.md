# 天氣功能實作指南

## 📋 概述

本指南說明如何將天氣功能整合到現有的防詐騙LINE Bot中，實現被動觸發的天氣查詢功能。用戶在閒聊過程中詢問天氣時，機器人會自動識別並提供相關資訊。

## 🎯 設計理念

- **被動觸發**：不主動顯示天氣按鈕，由用戶在對話中自然詢問
- **智能識別**：自動識別天氣相關關鍵詞和地點
- **個人化回應**：使用用戶名稱，提供友善的互動體驗
- **中央氣象署整合**：使用官方資料格式和免責聲明

## 🔧 實作步驟

### 步驟1：創建天氣功能類

在主程式中添加以下類別：

```python
class WeatherIntegration:
    """天氣功能整合類"""
    
    def __init__(self):
        # 天氣相關關鍵詞
        self.weather_keywords = [
            "天氣", "氣溫", "溫度", "下雨", "降雨", "雨天", "晴天", "陰天", "多雲",
            "颱風", "台風", "風速", "濕度", "氣壓", "預報", "天氣預報", "明天天氣",
            "今天天氣", "這幾天天氣", "週末天氣", "出門", "要帶傘", "會下雨",
            "熱不熱", "冷不冷", "穿什麼", "要穿外套", "幾度", "風大", "下雨"
        ]
        
        # 支援的城市
        self.location_keywords = [
            "台北", "新北", "桃園", "台中", "台南", "高雄", "基隆", "新竹",
            "苗栗", "彰化", "南投", "雲林", "嘉義", "屏東", "宜蘭", "花蓮",
            "台東", "澎湖", "金門", "馬祖"
        ]

    def detect_weather_query(self, message):
        """檢測是否為天氣相關詢問"""
        # 檢查天氣關鍵詞
        has_weather_keyword = any(keyword in message for keyword in self.weather_keywords)
        
        # 檢查地點
        mentioned_location = None
        for location in self.location_keywords:
            if location in message:
                mentioned_location = location
                break
        
        # 隱含天氣詢問檢測
        if mentioned_location and not has_weather_keyword:
            implicit_patterns = ["帶傘", "外套", "出門", "適合", "安全", "注意"]
            has_weather_keyword = any(pattern in message for pattern in implicit_patterns)
        
        return has_weather_keyword, mentioned_location

    def handle_weather_query(self, message, user_name="朋友"):
        """處理天氣詢問"""
        has_weather_query, location = self.detect_weather_query(message)
        
        if not has_weather_query:
            return None
        
        # 預設地點為台北
        if not location:
            location = "台北"
        
        # 這裡調用實際的天氣API
        # weather_data = call_weather_api(location, message)
        # return format_weather_response(weather_data, user_name)
        
        # 暫時返回模擬回應
        return f"@{user_name} 我來幫您查詢{location}的天氣資訊..."
```

### 步驟2：修改handle_message函數

在現有的`handle_message`函數中整合天氣功能：

```python
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 初始化天氣功能
    weather_integration = WeatherIntegration()
    
    # 獲取用戶資訊
    user_message = event.message.text
    user_id = event.source.user_id
    reply_token = event.reply_token
    
    # 獲取用戶顯示名稱
    display_name = get_user_profile(user_id)
    
    # 初始化回應變數
    reply_text = ""
    is_fraud_related = False
    
    # 檢查觸發關鍵詞
    bot_trigger_keyword = "土豆"
    if bot_trigger_keyword in user_message:
        clean_message = user_message.replace(bot_trigger_keyword, "").strip()
        
        # 1. 優先檢查天氣詢問
        weather_response = weather_integration.handle_weather_query(clean_message, display_name)
        if weather_response:
            reply_text = weather_response
        
        # 2. 檢查詐騙分析
        elif should_perform_fraud_analysis(clean_message):
            is_fraud_related = True
            # 現有的詐騙分析邏輯...
        
        # 3. 一般閒聊
        else:
            # 現有的閒聊邏輯...
    
    # 發送回應
    if reply_text:
        # 檢查長度限制
        if len(reply_text) > 4900:
            reply_text = reply_text[:4900] + "\n\n⚠️ 訊息過長已截斷"
        
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
```

### 步驟3：實作天氣API整合

根據您的需求選擇天氣API：

#### 選項A：中央氣象署開放資料API
```python
def get_weather_from_cwb(location, query_type="current"):
    """從中央氣象署獲取天氣資料"""
    api_key = "YOUR_CWB_API_KEY"
    
    if query_type == "current":
        url = f"https://opendata.cwb.gov.tw/api/v1/rest/datastore/O-A0003-001"
    else:
        url = f"https://opendata.cwb.gov.tw/api/v1/rest/datastore/F-C0032-001"
    
    params = {
        "Authorization": api_key,
        "locationName": location
    }
    
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        logger.error(f"天氣API錯誤: {e}")
        return None
```

#### 選項B：第三方天氣API
```python
def get_weather_from_third_party(location):
    """從第三方服務獲取天氣資料"""
    # 使用OpenWeatherMap、AccuWeather等
    pass
```

### 步驟4：格式化天氣回應

```python
def format_weather_response(weather_data, user_name, location):
    """格式化天氣回應訊息"""
    if not weather_data or not weather_data.get("success"):
        return f"@{user_name} ❌ 抱歉，目前無法取得{location}的天氣資訊，請稍後再試。"
    
    # 解析天氣資料
    current_weather = weather_data["records"]["location"][0]
    elements = {elem["elementName"]: elem["elementValue"] 
               for elem in current_weather["weatherElement"]}
    
    response = f"@{user_name} 🌤️ {location} 當前天氣\n\n"
    response += f"☁️ 天氣：{elements.get('Weather', 'N/A')}\n"
    response += f"🌡️ 溫度：{elements.get('Temp', 'N/A')}°C\n"
    response += f"💧 濕度：{elements.get('Humidity', 'N/A')}%\n"
    response += f"💨 風向風速：{elements.get('WindDirection', 'N/A')} {elements.get('WindSpeed', 'N/A')}m/s\n"
    response += f"📊 氣壓：{elements.get('Pressure', 'N/A')}hPa\n"
    response += f"🌧️ 降雨量：{elements.get('Rainfall', 'N/A')}mm\n\n"
    response += f"📡 資料來源：中央氣象署\n"
    response += f"ℹ️ 實際天氣以中央氣象署為準"
    
    return response
```

## 🧪 測試方法

### 基本功能測試
```python
# 測試天氣關鍵詞檢測
test_messages = [
    "土豆 今天台北天氣如何？",
    "土豆 明天會下雨嗎？", 
    "土豆 這週末去台中玩，天氣好嗎？",
    "土豆 現在有颱風警報嗎？"
]

weather_integration = WeatherIntegration()
for message in test_messages:
    clean_message = message.replace("土豆", "").strip()
    response = weather_integration.handle_weather_query(clean_message, "測試用戶")
    print(f"輸入：{message}")
    print(f"輸出：{response}")
    print("-" * 50)
```

### 邊界情況測試
```python
# 測試非天氣詢問
non_weather_messages = [
    "土豆 你好嗎？",
    "土豆 這個網址安全嗎？",
    "土豆 台中有什麼好吃的？"
]

for message in non_weather_messages:
    clean_message = message.replace("土豆", "").strip()
    response = weather_integration.handle_weather_query(clean_message, "測試用戶")
    should_be_none = response is None
    print(f"輸入：{message}")
    print(f"應該不觸發天氣功能：{should_be_none}")
```

## 📊 支援的查詢類型

### 1. 當前天氣查詢
- "今天台北天氣如何？"
- "現在外面熱不熱？"
- "台中現在幾度？"

### 2. 天氣預報查詢
- "明天會下雨嗎？"
- "這週末天氣好嗎？"
- "未來幾天的天氣預報"

### 3. 生活化詢問
- "要帶雨傘嗎？"
- "需要穿外套嗎？"
- "適合出門嗎？"

### 4. 天氣警報查詢
- "現在有颱風嗎？"
- "有什麼天氣警報？"
- "台北安全嗎？"

## 🎨 回應格式設計

### 當前天氣格式
```
@用戶名 🌤️ 城市 當前天氣

☁️ 天氣：晴時多雲
🌡️ 溫度：25.3°C
💧 濕度：68%
💨 風向風速：西南風 3.2m/s
📊 氣壓：1013.5hPa
🌧️ 降雨量：0.0mm

📡 資料來源：中央氣象署
ℹ️ 實際天氣以中央氣象署為準
```

### 天氣預報格式
```
@用戶名 📅 城市 未來3日天氣預報

📆 2025-05-24 (週六)
☁️ 多雲時晴
🌡️ 22°C ~ 28°C
🌧️ 降雨機率：20%

📆 2025-05-25 (週日)
☁️ 晴時多雲
🌡️ 24°C ~ 30°C
🌧️ 降雨機率：10%

📡 資料來源：中央氣象署
ℹ️ 實際天氣以中央氣象署為準
```

## ⚠️ 注意事項

### 1. API限制
- 注意API調用頻率限制
- 處理API錯誤和超時
- 實作快取機制減少API調用

### 2. 訊息長度
- LINE訊息限制5000字元
- 超過4900字元時自動截斷
- 提供分次查詢建議

### 3. 錯誤處理
```python
def safe_weather_query(location):
    """安全的天氣查詢，包含錯誤處理"""
    try:
        weather_data = get_weather_api(location)
        return format_weather_response(weather_data)
    except requests.RequestException:
        return "❌ 網路連線問題，請稍後再試"
    except KeyError:
        return "❌ 天氣資料格式錯誤"
    except Exception as e:
        logger.error(f"天氣查詢錯誤: {e}")
        return "❌ 系統暫時無法提供天氣資訊"
```

### 4. 效能優化
```python
# 實作快取機制
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=100)
def cached_weather_query(location, cache_time):
    """帶快取的天氣查詢"""
    return get_weather_api(location)

def get_cached_weather(location):
    """獲取快取的天氣資料（10分鐘有效）"""
    cache_time = datetime.now().replace(second=0, microsecond=0)
    cache_time = cache_time.replace(minute=cache_time.minute // 10 * 10)
    return cached_weather_query(location, cache_time)
```

## 🚀 進階功能

### 1. 智能建議
```python
def add_weather_suggestions(weather_data, message):
    """根據天氣狀況添加建議"""
    suggestions = []
    
    temp = float(weather_data.get("temperature", 0))
    rain_prob = float(weather_data.get("rain_probability", 0))
    
    if temp > 30:
        suggestions.append("🌡️ 天氣炎熱，建議多補充水分")
    elif temp < 15:
        suggestions.append("🧥 氣溫較低，建議穿著保暖衣物")
    
    if rain_prob > 70:
        suggestions.append("☔ 降雨機率高，建議攜帶雨具")
    
    if "出門" in message and suggestions:
        return "\n\n💡 貼心提醒：\n" + "\n".join(suggestions)
    
    return ""
```

### 2. 個人化設定
```python
def get_user_default_location(user_id):
    """獲取用戶預設城市"""
    # 從資料庫讀取用戶設定
    return user_settings.get(user_id, {}).get("default_city", "台北")

def set_user_default_location(user_id, location):
    """設定用戶預設城市"""
    # 儲存到資料庫
    user_settings[user_id] = {"default_city": location}
```

## 📈 監控和分析

### 1. 使用統計
```python
def log_weather_query(user_id, location, query_type):
    """記錄天氣查詢統計"""
    logger.info(f"天氣查詢 - 用戶:{user_id}, 地點:{location}, 類型:{query_type}")
    
    # 儲存到統計資料庫
    weather_stats.record_query(user_id, location, query_type, datetime.now())
```

### 2. 錯誤監控
```python
def monitor_weather_errors(error_type, details):
    """監控天氣功能錯誤"""
    error_count[error_type] = error_count.get(error_type, 0) + 1
    
    if error_count[error_type] > 10:  # 錯誤次數過多時告警
        send_alert(f"天氣功能錯誤頻繁: {error_type}")
```

## ✅ 部署檢查清單

- [ ] 天氣API金鑰設定完成
- [ ] 關鍵詞檢測邏輯測試通過
- [ ] 錯誤處理機制完善
- [ ] 訊息長度限制處理
- [ ] 快取機制實作
- [ ] 日誌記錄設定
- [ ] 效能測試通過
- [ ] 用戶體驗測試完成

## 🔗 相關資源

- [中央氣象署開放資料平台](https://opendata.cwb.gov.tw/)
- [LINE Bot API文件](https://developers.line.biz/en/docs/messaging-api/)
- [天氣功能測試程序](./test_weather_comprehensive.py)
- [整合示例代碼](./weather_integration_example.py)

---

**實作完成後，用戶就可以在對話中自然地詢問天氣，機器人會智能識別並提供準確的天氣資訊，大大提升用戶體驗！** 🌤️ 