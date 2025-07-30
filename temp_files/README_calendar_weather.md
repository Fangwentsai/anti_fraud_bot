# 國曆農曆天氣服務模組

這是一個專門處理國曆農曆轉換和天氣查詢的Python模組，可以整合到您的防詐騙LINE Bot中，提供更豐富的功能。

## 🌟 主要功能

### 📅 日期功能
- **國曆農曆轉換**：支援國曆轉農曆（農曆轉國曆開發中）
- **今日日期資訊**：顯示國曆、農曆、星期、節氣等完整資訊
- **二十四節氣查詢**：提供全年節氣時間和說明
- **節日查詢**：支援國定假日和傳統節日查詢

### 🌤️ 天氣功能
- **多城市天氣預報**：支援台灣20個主要城市
- **多日預報**：可查詢1-7天的天氣預報
- **詳細資訊**：包含溫度、濕度、降雨機率等
- **中央氣象署API**：使用官方資料來源（需申請API金鑰）

## 📦 安裝依賴

```bash
# 安裝基本依賴
pip install -r requirements_calendar_weather.txt

# 或手動安裝主要套件
pip install requests python-dotenv python-dateutil
```

## 🔧 環境設定

1. 複製配置範例文件：
```bash
cp calendar_weather_config.example .env
```

2. 編輯 `.env` 文件，設定您的API金鑰：
```bash
# 中央氣象署開放資料API金鑰（可選）
CWB_API_KEY=your_api_key_here
```

> **注意**：如果沒有設定API金鑰，系統會使用模擬資料

## 🚀 快速開始

### 基本使用

```python
from calendar_weather_service import (
    get_today_info,
    get_weather,
    get_date_info,
    get_solar_terms
)

# 獲取今日完整資訊（日期+天氣）
print(get_today_info())

# 查詢台北3天天氣
print(get_weather("台北", 3))

# 獲取今日日期資訊
print(get_date_info())

# 國曆轉農曆
print(get_date_info("2024-01-01"))

# 查詢2024年二十四節氣
print(get_solar_terms(2024))
```

### 進階使用

```python
from calendar_weather_service import CalendarWeatherService

# 創建服務實例
service = CalendarWeatherService()

# 獲取詳細的日期資訊
date_info = service.get_current_date_info()
print(f"今天是{date_info['gregorian']['formatted']}")
print(f"農曆{date_info['lunar']['formatted']}")

# 獲取天氣預報資料
weather_data = service.get_weather_forecast("高雄", 5)
if weather_data['success']:
    for day in weather_data['forecast']:
        print(f"{day['date']} {day['weather']} {day['temperature']['low']}-{day['temperature']['high']}°C")

# 查詢節日資訊
holiday_info = service.get_holiday_info("2024-10-10")
if holiday_info['holidays']:
    for holiday in holiday_info['holidays']:
        print(f"今天是{holiday['name']}（{holiday['type']}）")
```

## 🏙️ 支援城市

目前支援台灣以下20個城市的天氣查詢：

| 城市 | 城市 | 城市 | 城市 |
|------|------|------|------|
| 台北 | 新北 | 桃園 | 台中 |
| 台南 | 高雄 | 基隆 | 新竹 |
| 苗栗 | 彰化 | 南投 | 雲林 |
| 嘉義 | 屏東 | 宜蘭 | 花蓮 |
| 台東 | 澎湖 | 金門 | 連江 |

## 🤖 整合到LINE Bot

在您的防詐騙LINE Bot中加入日期天氣功能：

```python
# 在 anti_fraud_clean_app.py 中加入
from calendar_weather_service import get_today_info, get_weather, get_date_info

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text_message = event.message.text
    
    # 新增天氣查詢功能
    if "天氣" in text_message:
        # 解析城市名稱
        city = "台北"  # 預設城市
        for supported_city in ["台北", "台中", "高雄", "台南"]:
            if supported_city in text_message:
                city = supported_city
                break
        
        weather_info = get_weather(city, 3)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=weather_info)
        )
        return
    
    # 新增日期查詢功能
    if "今天" in text_message and ("日期" in text_message or "農曆" in text_message):
        date_info = get_date_info()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=date_info)
        )
        return
    
    # 新增節氣查詢功能
    if "節氣" in text_message:
        solar_terms = get_solar_terms()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=solar_terms)
        )
        return
    
    # 原有的詐騙分析功能...
```

## 🧪 測試

### 運行單元測試
```bash
python test_calendar_weather.py
```

### 運行手動測試
```bash
python test_calendar_weather.py manual
```

### 測試特定功能
```bash
# 直接運行服務模組
python calendar_weather_service.py
```

## 📋 API參考

### CalendarWeatherService 類

#### 主要方法

- `get_current_date_info()` - 獲取當前日期完整資訊
- `get_weather_forecast(city, days)` - 獲取天氣預報
- `convert_date(date_str, from_type)` - 日期轉換
- `get_solar_terms_info(year)` - 獲取二十四節氣
- `get_holiday_info(date_str)` - 獲取節日資訊

#### 格式化方法

- `format_weather_message(weather_data)` - 格式化天氣訊息
- `format_date_message(date_data)` - 格式化日期訊息

### 便捷函數

- `get_today_info()` - 今日完整資訊
- `get_weather(city, days)` - 天氣預報
- `get_date_info(date_str)` - 日期資訊/轉換
- `get_solar_terms(year)` - 二十四節氣

## ⚠️ 注意事項

1. **農曆計算**：目前使用簡化算法，實際應用建議使用專業農曆庫如 `lunardate`
2. **節氣計算**：使用簡化算法，精確計算需要天文庫如 `ephem`
3. **API限制**：中央氣象署API有使用限制，建議加入快取機制
4. **錯誤處理**：網路請求可能失敗，系統會自動降級到模擬資料

## 🔮 未來功能

- [ ] 精確的農曆轉國曆功能
- [ ] 更精確的節氣計算
- [ ] 天氣資料快取機制
- [ ] 更多天氣API支援
- [ ] 農曆節日自動計算
- [ ] 黃曆宜忌查詢
- [ ] 潮汐資訊查詢

## 🤝 貢獻

歡迎提交Issue和Pull Request來改進這個模組！

## 📄 授權

此模組遵循MIT授權條款。

---

**提示**：這個模組設計為獨立運作，可以輕鬆整合到任何Python專案中，不僅限於LINE Bot使用。 