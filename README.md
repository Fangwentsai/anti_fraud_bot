# 🛡️ 防詐騙LINE Bot - 土豆小幫手

一個專為50-60歲中老年人設計的智能防詐騙LINE機器人，提供即時詐騙風險分析、教育遊戲和防範建議。

## ✨ 主要功能

### 🔍 智能詐騙檢測
- **URL安全分析**：自動檢測可疑網址和釣魚網站
- **網域變形攻擊檢測**：識別模仿知名網站的變形網域
- **短網址展開**：自動展開並分析短網址的真實目的地
- **關鍵詞分析**：基於AI的詐騙話術識別

### 🌐 白名單系統
- **317個安全網域**：涵蓋政府機關、銀行金融、電商購物等
- **分類管理**：按行業分類的可信任網站清單
- **動態載入**：支援JSON格式的白名單更新

### 🎮 互動式學習
- **「選哪顆土豆」遊戲**：通過問答遊戲提升防詐騙意識
- **實際案例學習**：基於真實詐騙案例的教育內容
- **即時回饋**：遊戲中提供詳細的解釋和建議

### 💬 智能對話
- **閒聊模式**：支援自然語言對話，提供溫暖的互動體驗
- **記憶功能**：記住用戶的對話歷史，提供個性化回應
- **群組支援**：支援LINE群組使用，使用「土豆」關鍵詞觸發

### 📊 視覺化回覆
- **Flex Message**：美觀的卡片式回覆介面
- **風險等級顯示**：清晰的顏色編碼和emoji標示
- **操作按鈕**：便捷的快速回覆和功能按鈕

## 🏗️ 系統架構

### 模組化設計
```
anti-fraud-clean/
├── anti_fraud_clean_app.py      # 主程式
├── config.py                    # 配置管理
├── fraud_knowledge.py           # 詐騙知識庫
├── domain_spoofing_detector.py  # 網域變形檢測
├── flex_message_service.py      # Flex Message服務
├── game_service.py              # 遊戲服務
├── weather_service.py           # 天氣服務
├── firebase_manager.py          # 資料庫管理
├── safe_domains.json            # 安全網域清單
├── fraud_tactics.json           # 詐騙手法資料
└── potato_game_questions.json   # 遊戲題目
```

### 核心技術
- **Flask**：Web框架
- **LINE Bot SDK**：LINE機器人開發
- **OpenAI GPT**：AI對話和分析
- **Firebase**：雲端資料庫
- **Python 3.8+**：主要開發語言

## 🚀 快速開始

### 環境需求
- Python 3.8+
- LINE Developer Account
- OpenAI API Key
- Firebase Project

### 安裝步驟

1. **克隆專案**
```bash
git clone https://github.com/your-username/anti-fraud-linebot.git
cd anti-fraud-linebot
```

2. **安裝依賴**
```bash
pip install -r requirements.txt
```

3. **環境變數設定**
創建 `.env` 文件：
```env
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
OPENAI_API_KEY=your_openai_api_key
FIREBASE_CREDENTIALS=path_to_firebase_credentials.json
```

4. **啟動服務**
```bash
python anti_fraud_clean_app.py
```

### LINE Bot 設定
1. 在 [LINE Developers Console](https://developers.line.biz/) 創建新的Channel
2. 設定Webhook URL：`https://your-domain.com/callback`
3. 啟用Messaging API功能

## 📋 使用說明

### 基本指令
- **土豆**：在群組中觸發機器人（私聊不需要）
- **請幫我分析這則訊息**：請求詐騙風險分析
- **選哪顆土豆**：啟動防詐騙能力測試遊戲
- **詐騙類型列表**：查看各種詐騙類型說明

### 分析功能
1. 直接貼上可疑網址或訊息
2. 機器人會自動分析風險等級
3. 提供詳細的解釋和防範建議
4. 支援短網址自動展開

### 遊戲功能
1. 輸入「選哪顆土豆」啟動遊戲
2. 根據題目選擇正確答案
3. 獲得詳細的解釋和防詐騙知識
4. 累積分數和學習進度

## 🔧 配置說明

### 白名單管理
編輯 `safe_domains.json` 文件來管理安全網域：
```json
{
  "safe_domains": {
    "政府機關": {
      "gov.tw": "台灣政府機關通用網域",
      "president.gov.tw": "總統府官方網站"
    }
  },
  "donation_domains": {
    "buymeacoffee.com/todao_antifraud": "贊助頁面"
  }
}
```

### 詐騙知識庫
編輯 `fraud_tactics.json` 來更新詐騙類型和防範措施：
```json
{
  "假投資詐騙": {
    "description": "詐騙描述",
    "keywords": ["關鍵詞1", "關鍵詞2"],
    "risk_level": "極高",
    "sop": ["防範措施1", "防範措施2"]
  }
}
```

## 📊 測試報告

系統通過完整的測試驗證，達到 **100% 測試通過率**：

- ✅ 配置模組測試
- ✅ 安全網域載入測試  
- ✅ 詐騙知識模組測試
- ✅ 網域變形檢測測試
- ✅ 遊戲服務測試
- ✅ Flex Message服務測試
- ✅ 主程式核心函數測試
- ✅ 整合測試

運行測試：
```bash
python test_complete_system.py
```

## 🛠️ 開發指南

### 添加新的詐騙類型
1. 在 `fraud_tactics.json` 中添加新類型
2. 更新 `fraud_knowledge.py` 中的關鍵詞檢測
3. 運行測試確保功能正常

### 擴展白名單
1. 編輯 `safe_domains.json`
2. 按分類添加新的安全網域
3. 包含網站描述信息

### 自定義Flex Message
1. 編輯 `flex_message_service.py`
2. 創建新的Flex Message模板
3. 在主程式中調用新模板

## 🤝 貢獻指南

歡迎提交Issue和Pull Request！

1. Fork 這個專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟Pull Request

## 📄 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 文件

## 🙏 致謝

- 感謝所有提供詐騙案例和建議的用戶
- 感謝開源社群提供的優秀工具和框架
- 特別感謝中老年用戶的耐心測試和回饋

## 📞 聯絡方式

- 專案維護者：土豆團隊
- 贊助支持：[Buy Me a Coffee](https://buymeacoffee.com/todao_antifraud)
- 問題回報：請使用GitHub Issues

---

**讓我們一起守護長輩的數位安全！** 🛡️💙 