# 🛡️ 防詐騙機器人 Anti-Fraud Bot

[![測試狀態](https://img.shields.io/badge/測試狀態-100%25通過-brightgreen)](./test_report_20250524_153027.txt)
[![功能完整性](https://img.shields.io/badge/功能完整性-4%2F4-brightgreen)](#功能特色)
[![Python版本](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![LINE Bot](https://img.shields.io/badge/LINE-Bot-00C300)](https://developers.line.biz/)

專為50-60歲長輩設計的LINE防詐騙聊天機器人，提供網站風險評估、詐騙案例分享、防詐遊戲和天氣查詢服務。

## 🎯 功能特色

### ✅ 1. 網站風險評估 (86.7%準確率)
- **智能URL分析**：自動檢測可疑網址和釣魚網站
- **網域變形檢測**：識別模仿知名網站的假冒網址
- **短網址展開**：安全展開並分析短網址真實目的地
- **白名單保護**：內建台灣常用安全網站清單

### ✅ 2. 詐騙案例分享 (100%功能完整)
- **真實案例**：提供3大類詐騙的詳細案例分析
  - 假交友投資詐騙
  - 網路購物詐騙
  - 假檢警詐騙
- **防詐小知識**：10+條實用防詐騙提醒
- **話術資料庫**：涵蓋9種常見詐騙類型

### ✅ 3. 防詐遊戲 (31道題目)
- **互動測試**：趣味問答測試防詐騙知識
- **涵蓋範圍**：20種詐騙類型，包括：
  - LINE假冒子女詐騙
  - 假中獎通知詐騙
  - 退休金詐騙
  - 老年投資詐騙等
- **智能觸發**：支援多種遊戲觸發關鍵詞
- **詳細解釋**：每題都有詳細的防詐騙說明

### ✅ 4. 天氣查詢 (5個城市全支援)
- **多城市支援**：台北、宜蘭、嘉義、高雄、屏東
- **即時資料**：使用中央氣象署官方API
- **完整資訊**：溫度、天氣狀況、降雨機率
- **智能識別**：自動識別天氣相關關鍵詞

## 🧪 測試結果

根據綜合測試報告([詳細報告](./test_report_20250524_153027.txt))：

| 功能 | 測試狀態 | 成功率 | 測試內容 |
|------|---------|--------|----------|
| 🔍 網站風險評估 | ✅ 通過 | 86.7% | 15個測試案例，包含可疑網域、變異網域、合法網域 |
| 📖 詐騙案例分享 | ✅ 通過 | 100% | 3個詐騙案例 + 10條防詐小知識 |
| 🎮 防詐遊戲 | ✅ 通過 | 4/4 | 31道題目，涵蓋20種詐騙類型 |
| ☁️ 天氣查詢 | ✅ 通過 | 100% | 5個指定城市天氣預報 |

**🎯 整體通過率：4/4 (100%)**

## 🚀 快速開始

### 前置需求
- Python 3.8+
- LINE Messaging API 帳號
- OpenAI API 金鑰
- 中央氣象署API金鑰 (選用)

### 安裝步驟

1. **克隆專案**
```bash
git clone https://github.com/your-username/anti-fraud-bot.git
cd anti-fraud-bot
```

2. **安裝依賴**
```bash
pip install -r requirements.txt
```

3. **環境變數設置**
創建`.env`文件：
```env
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
OPENAI_API_KEY=your_openai_api_key
CWB_API_KEY=your_weather_api_key  # 選用，用於天氣查詢
```

4. **啟動服務**
```bash
python anti_fraud_clean_app.py
```

### 測試功能

運行完整測試套件：
```bash
python comprehensive_test_report.py
```

個別功能測試：
```bash
python test_website_risk_assessment.py  # 網站風險評估
python test_fraud_cases.py             # 詐騙案例分享
python test_fraud_game.py              # 防詐遊戲
python test_weather_query.py           # 天氣查詢
```

## 💬 使用方法

### 私聊模式
直接與機器人對話：
- 「請幫我分析這個網站」+ 網址
- 「防詐騙測試」
- 「詐騙類型列表」
- 「今天台北天氣」

### 群組模式
使用觸發關鍵詞「土豆」：
- 「土豆 請幫我分析這個網站」
- 「土豆 防詐騙測試」
- 「土豆 今天天氣如何」

## 🏗️ 系統架構

```
防詐騙機器人
├── anti_fraud_clean_app.py      # 主程式
├── config.py                    # 配置管理
├── weather_service.py           # 天氣服務
├── game_service.py              # 遊戲服務
├── fraud_knowledge.py           # 詐騙知識庫
├── domain_spoofing_detector.py  # 網域檢測
├── flex_message_service.py      # 訊息格式化
├── firebase_manager.py          # 資料庫管理
└── 測試檔案/
    ├── test_website_risk_assessment.py
    ├── test_fraud_cases.py
    ├── test_fraud_game.py
    ├── test_weather_query.py
    └── comprehensive_test_report.py
```

## 📊 功能統計

- **詐騙類型覆蓋**：20種常見詐騙手法
- **安全網域資料庫**：50+個台灣常用網站
- **防詐遊戲題庫**：31道精選題目
- **支援城市**：5個台灣主要城市
- **測試覆蓋率**：100%功能測試通過

## 🛠️ 技術特色

- **智能對話**：使用OpenAI GPT-4進行自然語言處理
- **彈性訊息**：LINE Flex Message提供豐富互動體驗
- **即時資料**：整合中央氣象署官方API
- **模組化設計**：清晰的程式碼架構便於維護
- **完整測試**：涵蓋所有核心功能的自動化測試

## 🔒 安全性

- **API金鑰保護**：所有敏感資訊透過環境變數管理
- **輸入驗證**：對所有用戶輸入進行安全檢查
- **錯誤處理**：完善的異常處理機制
- **資料隱私**：用戶互動資料加密儲存

## 📈 持續改進

未來計劃功能：
- [ ] 增加更多詐騙類型的偵測
- [ ] 支援語音訊息分析
- [ ] 用戶行為統計分析
- [ ] 多語言支援
- [ ] 即時詐騙警報系統

## 📄 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 文件

## 🤝 貢獻指南

歡迎提交Issue和Pull Request！

1. Fork 本專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 開啟Pull Request

## 📞 聯絡資訊

如有問題或建議，歡迎透過以下方式聯繫：
- 提交 [GitHub Issue](../../issues)
- 電子郵件：your-email@example.com

## 🙏 致謝

感謝以下服務和資源：
- [LINE Messaging API](https://developers.line.biz/)
- [OpenAI API](https://openai.com/api/)
- [中央氣象署開放資料平台](https://opendata.cwa.gov.tw/)
- [Firebase](https://firebase.google.com/)

---

**⚠️ 免責聲明**：本機器人提供的資訊僅供參考，實際詐騙手法日新月異，請使用者保持警覺並多方查證。如遇可疑情況，請立即撥打165反詐騙專線。 