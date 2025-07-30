# 🆘 核心功能恢復指南

## 快速恢復步驟

### 1. 從Git恢復到穩定版本
```bash
git checkout v1.0.0-stable
```

### 2. 恢復特定文件
```bash
git checkout v1.0.0-stable -- anti_fraud_clean_app.py weather_service.py
```

### 3. 重新部署
```bash
git add .
git commit -m "🔧 恢復核心功能到穩定版本"
git push origin main
```

## 測試核心功能

### 防詐騙測試
```bash
# 測試假冒網域檢測
curl -X POST https://your-bot-url/callback \
  -H "Content-Type: application/json" \
  -d '{"events":[{"message":{"text":"https://event.liontraveler.com"}}]}'
```

### 天氣查詢測試
```bash
# 測試天氣功能
python3 -c "from weather_service import handle_weather_query; print(handle_weather_query('台北天氣', '測試'))"
```

## 緊急聯絡

- **版本**: 1.0.0-stable
- **鎖定日期**: 2025-05-24
- **Git標籤**: v1.0.0-stable

記住：**穩定比功能更重要！** 🛡️
