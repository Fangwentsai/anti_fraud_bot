# 防詐騙Line機器人

這是一個專為中老年人設計的防詐騙Line聊天機器人，提供各種詐騙類型的識別、案例分享和處理SOP，並整合ChatGPT進行即時訊息分析。

## 功能介紹

- 詐騙類型分類與說明
- 詐騙案例分享
- 詐騙處理SOP指南
- 簡易的管理界面
- ChatGPT輔助分析，識別可疑訊息中的詐騙風險
- Firebase整合，記錄用戶互動和詐騙報告
- 詐騙統計資料視覺化

## 系統需求

- Python 3.6+
- Flask
- Line Messaging API
- OpenAI API (ChatGPT)
- Firebase (Firestore)

## 安裝步驟

1. 克隆此儲存庫：
   ```
   git clone <repository-url>
   cd linebot-anti-fraud
   ```

2. 安裝所需套件：
   ```
   pip install -r requirements.txt
   ```

3. 設定環境變數：
   ```
   cp .env-example .env
   ```
   並編輯`.env`文件，填入您的Line Bot API憑證、OpenAI API密鑰和Firebase憑證

4. Firebase設置：
   詳細設置請參考`firebase_setup.md`文件

5. 運行應用：
   ```
   python app.py
   ```

6. 使用ngrok或其他服務將應用暴露在公網上：
   ```
   ngrok http 5000
   ```

7. 在Line Developer Console中設置Webhook URL為您的ngrok URL + `/callback`

8. 部署至Render.com (選擇性):
   - 在Render.com創建新的Web Service
   - 連接至GitHub儲存庫
   - 設置環境變數(LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, OPENAI_API_KEY, FIREBASE_CREDENTIALS)
   - 部署服務並設置Line Webhook URL為Render服務URL + `/callback`

## 詐騙類型

目前已包含的詐騙類型：

- 網路購物詐騙
- 假交友投資詐騙
- 假中獎通知詐騙
- 假借銀行貸款詐騙
- 假廣告詐騙
- 色情應召詐財詐騙
- 虛擬遊戲詐騙
- 假求職詐騙
- 假檢警詐騙
- 金融帳戶詐騙
- 釣魚簡訊詐騙

## 使用方式

用戶可以向Line機器人詢問：

- "詐騙類型" - 獲取所有詐騙類型列表
- "網路購物詐騙案例" - 獲取特定類型的詐騙案例
- "假冒身份詐騙處理方法" - 獲取特定類型詐騙的處理SOP
- "分析 [可疑訊息內容]" - 使用ChatGPT分析訊息是否含有詐騙跡象
- 或直接輸入詐騙類型名稱獲取相關資訊

## AI詐騙分析功能

本機器人整合了ChatGPT，能夠分析用戶提供的訊息內容，並提供：

1. 詐騙風險評估 (高/中/低)
2. 可能的詐騙類型
3. 識別出的可疑跡象
4. 防範建議和下一步行動

使用方式為輸入"分析"或"檢查"後接可疑訊息內容。

## 擴展與貢獻

您可以通過以下方式擴展機器人功能：

1. 在`fraud_tactics.json`中添加新的詐騙類型和話術
2. 在`app.py`中的`fraud_types`字典中添加更多詐騙類型、案例和SOP
3. 開發新的AI分析模型提高詐騙識別的準確率

## 資料統計

機器人會記錄用戶互動和詐騙分析數據，可通過以下方式查看：

- 訪問 `/fraud-statistics` 路徑查看詐騙統計數據視覺化頁面
- 數據包括詐騙類型分布、風險等級統計等

## 注意事項

本機器人提供的建議僅供參考，如遇可疑詐騙情況，請撥打165反詐騙專線尋求專業協助。 

定期更新詐騙資料庫以應對新型詐騙手法 