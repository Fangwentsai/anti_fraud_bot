# 防詐騙Line機器人

一個基於Line Messaging API和OpenAI的防詐騙機器人，幫助用戶識別詐騙訊息並學習防詐騙知識。

## 功能特色

- **詐騙分析**：分析URL或訊息中的詐騙風險
- **Flex Message**：以美觀的卡片式介面顯示分析結果
- **詐騙類型庫**：提供常見詐騙類型的資訊和防範方法
- **「選哪顆土豆」遊戲**：透過有趣的方式學習辨識詐騙訊息
- **統計功能**：查看各類詐騙的統計數據

## 目錄結構

```
./
├── anti-fraud-clean/          # 主程式目錄
│   ├── app.py                 # 主程式
│   ├── firebase_manager.py    # Firebase數據管理模組
│   ├── fix_json_display.py    # JSON格式處理工具
│   ├── fraud_tactics.json     # 詐騙話術資料庫
│   ├── potato_game_questions.json # 遊戲題庫
│   ├── requirements.txt       # 依賴套件清單
│   └── templates/             # 網頁模板目錄
└── linebot-anti-fraud/        # 配置檔案目錄
    └── .env                   # 環境變數設定檔
```

## 環境設定

1. 安裝依賴套件：
   ```
   cd anti-fraud-clean
   pip install -r requirements.txt
   ```

2. 配置環境變數：
   確保 `linebot-anti-fraud/.env` 檔案中包含以下設定：
   ```
   LINE_CHANNEL_SECRET=你的Line頻道密鑰
   LINE_CHANNEL_ACCESS_TOKEN=你的Line訪問令牌
   OPENAI_API_KEY=你的OpenAI API密鑰
   OPENAI_MODEL=gpt-3.5-turbo
   ```

## 運行方式

```bash
cd anti-fraud-clean
python app.py
```

## 部署

### Heroku 部署
```bash
git init
git add .
git commit -m "Initial commit"
heroku create your-app-name
git push heroku master
```

### Docker 部署
```bash
docker build -t line-antifraud-bot .
docker run -p 8080:8080 line-antifraud-bot
``` 