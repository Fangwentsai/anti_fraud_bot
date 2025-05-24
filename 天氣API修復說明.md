# 天氣API修復說明

## 🔍 問題診斷

天氣服務失效可能的原因：

1. **缺少CWB_API_KEY環境變數**
2. **API金鑰過期或無效**
3. **中央氣象署API服務異常**
4. **網路連線問題**

## 🛠️ 修復方案

### 方案1：設定API金鑰（推薦）

1. **取得API金鑰**
   - 前往 [中央氣象署氣象開放資料平臺](https://opendata.cwa.gov.tw/)
   - 註冊會員並申請API授權碼

2. **設定環境變數**
   ```bash
   # 在 .env 檔案中添加
   CWB_API_KEY=your_api_key_here
   ```

3. **Render平台設定**
   - 進入Render專案設定
   - 在Environment Variables中添加：
     - Key: `CWB_API_KEY`
     - Value: 您的API金鑰

### 方案2：使用模擬資料（當前狀態）

系統已自動回退到模擬資料模式：
- ✅ 天氣查詢功能正常
- ✅ 顯示模擬天氣資料
- ⚠️ 會標示「模擬資料」警告

### 方案3：檢查API連線

如果有API金鑰但仍失效，可能是：
- API請求超時（timeout=10秒）
- API回應格式變更
- API服務暫時中斷

## 📊 目前狀態

天氣服務會自動處理API失效問題：

```python
if not self.cwb_api_key:
    # 自動使用模擬資料
    logger.warning("未設定中央氣象署API金鑰，使用模擬資料")
    return self._get_mock_weather_data(city, days)
```

## 🧪 測試方法

測試天氣服務是否正常：
1. 私訊機器人「今天天氣」
2. 檢查回覆是否包含：
   - 天氣資訊
   - 「模擬資料」標示（如無API金鑰）
   - 資料來源說明

## 💡 模擬資料說明

當API不可用時，系統提供：
- 隨機天氣狀況（晴天、多雲、陰天、小雨、雷陣雨）
- 合理溫度範圍（18-28°C）
- 濕度和降雨機率
- 明確標示為「模擬資料」

## 🔧 部署時修復

1. **本地測試**
   ```bash
   export CWB_API_KEY="your_key"
   python weather_service.py
   ```

2. **Render部署**
   - 更新環境變數後重新部署
   - 檢查日誌確認API金鑰載入

3. **驗證修復**
   - 檢查回覆資料來源：「中央氣象署」vs「模擬資料」 