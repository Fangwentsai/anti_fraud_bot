# 🚀 部署指南

本文檔說明如何將防詐騙LINE Bot部署到各種平台。

## 📋 部署前準備

### 1. 環境變數設定
創建 `.env` 文件並設定以下變數：

```env
# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_CHANNEL_SECRET=your_line_channel_secret_here

# OpenAI API 設定
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Firebase 設定
FIREBASE_CREDENTIALS=path/to/your/firebase-credentials.json

# 應用程式設定
PORT=8080
FLASK_ENV=production
LOG_LEVEL=INFO
```

### 2. 依賴套件
確保 `requirements.txt` 包含所有必要套件：

```txt
Flask==2.3.3
line-bot-sdk==3.5.0
openai==1.3.0
firebase-admin==6.2.0
python-dotenv==1.0.0
requests==2.31.0
```

## 🌐 Heroku 部署

### 1. 安裝 Heroku CLI
```bash
# macOS
brew tap heroku/brew && brew install heroku

# Windows
# 下載並安裝 Heroku CLI
```

### 2. 登入 Heroku
```bash
heroku login
```

### 3. 創建應用程式
```bash
heroku create your-app-name
```

### 4. 設定環境變數
```bash
heroku config:set LINE_CHANNEL_ACCESS_TOKEN=your_token
heroku config:set LINE_CHANNEL_SECRET=your_secret
heroku config:set OPENAI_API_KEY=your_api_key
```

### 5. 部署
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### 6. 設定 Webhook URL
在 LINE Developers Console 設定：
```
https://your-app-name.herokuapp.com/callback
```

## ☁️ Google Cloud Platform 部署

### 1. 安裝 gcloud CLI
```bash
# 下載並安裝 Google Cloud SDK
```

### 2. 初始化專案
```bash
gcloud init
gcloud app create
```

### 3. 創建 app.yaml
```yaml
runtime: python39

env_variables:
  LINE_CHANNEL_ACCESS_TOKEN: "your_token"
  LINE_CHANNEL_SECRET: "your_secret"
  OPENAI_API_KEY: "your_api_key"

automatic_scaling:
  min_instances: 1
  max_instances: 10
```

### 4. 部署
```bash
gcloud app deploy
```

## 🐳 Docker 部署

### 1. 創建 Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "anti_fraud_clean_app.py"]
```

### 2. 建立映像
```bash
docker build -t anti-fraud-bot .
```

### 3. 運行容器
```bash
docker run -p 8080:8080 --env-file .env anti-fraud-bot
```

### 4. Docker Compose
創建 `docker-compose.yml`：
```yaml
version: '3.8'
services:
  anti-fraud-bot:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    restart: unless-stopped
```

運行：
```bash
docker-compose up -d
```

## 🔧 AWS EC2 部署

### 1. 啟動 EC2 實例
- 選擇 Ubuntu 20.04 LTS
- 配置安全群組開放 80, 443, 8080 端口

### 2. 連接到實例
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 3. 安裝依賴
```bash
sudo apt update
sudo apt install python3 python3-pip nginx git -y
```

### 4. 克隆專案
```bash
git clone https://github.com/your-username/anti-fraud-linebot.git
cd anti-fraud-linebot
```

### 5. 安裝 Python 套件
```bash
pip3 install -r requirements.txt
```

### 6. 設定環境變數
```bash
nano .env
# 填入您的環境變數
```

### 7. 設定 Nginx
```bash
sudo nano /etc/nginx/sites-available/anti-fraud-bot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 8. 啟用網站
```bash
sudo ln -s /etc/nginx/sites-available/anti-fraud-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 9. 設定系統服務
```bash
sudo nano /etc/systemd/system/anti-fraud-bot.service
```

```ini
[Unit]
Description=Anti-Fraud LINE Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/anti-fraud-linebot
ExecStart=/usr/bin/python3 anti_fraud_clean_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 10. 啟動服務
```bash
sudo systemctl daemon-reload
sudo systemctl enable anti-fraud-bot
sudo systemctl start anti-fraud-bot
```

## 🔒 SSL 憑證設定

### 使用 Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

## 📊 監控和日誌

### 1. 查看應用程式日誌
```bash
# Heroku
heroku logs --tail

# Docker
docker logs -f container_name

# EC2
sudo journalctl -u anti-fraud-bot -f
```

### 2. 健康檢查
設定健康檢查端點：
```python
@app.route("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

## 🔧 故障排除

### 常見問題

1. **Webhook 驗證失敗**
   - 檢查 LINE_CHANNEL_SECRET 是否正確
   - 確認 HTTPS 設定正確

2. **OpenAI API 錯誤**
   - 檢查 API 金鑰是否有效
   - 確認帳戶餘額充足

3. **Firebase 連接失敗**
   - 檢查憑證文件路徑
   - 確認 Firebase 專案設定

4. **記憶體不足**
   - 增加實例記憶體
   - 優化程式碼效能

### 日誌分析
```bash
# 查看錯誤日誌
grep "ERROR" app.log

# 監控 API 使用量
grep "OpenAI" app.log | wc -l
```

## 📈 效能優化

### 1. 快取設定
```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.memoize(timeout=300)
def get_fraud_analysis(message):
    # 快取分析結果
    pass
```

### 2. 資料庫連接池
```python
# 設定 Firebase 連接池
firebase_admin.initialize_app(credential, {
    'databaseURL': 'your-database-url',
    'httpTimeout': 30
})
```

### 3. 非同步處理
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

def async_analysis(message):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # 非同步處理邏輯
```

## 🔄 持續部署

### GitHub Actions
創建 `.github/workflows/deploy.yml`：
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{secrets.HEROKU_API_KEY}}
        heroku_app_name: "your-app-name"
        heroku_email: "your-email@example.com"
```

---

**部署成功後，記得在 LINE Developers Console 設定正確的 Webhook URL！** 🎉 