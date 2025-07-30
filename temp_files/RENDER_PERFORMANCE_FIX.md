# 🚀 Render 性能優化指南 - 解決回覆延遲問題

## 🔍 問題描述
太久沒有使用土豆機器人時，第一次回覆會比較慢，這是因為 Render 服務進入低活躍狀態造成的。

## ✅ 解決方案（已修復）

### 1. 升級到付費方案 ✨
- 已更新 `render.yaml` 為 `plan: starter`
- 付費方案有更好的性能和更少的休眠問題

### 2. 內建 Keep-Alive 機制 🔄
我們已經在主應用中添加了內建的 keep-alive 機制：

**新功能：**
- ✅ 每 5 分鐘自動進行內部健康檢查
- ✅ 自動清理過期的用戶狀態
- ✅ 詳細的服務監控資訊
- ✅ 記憶體使用量監控

**監控端點：**
```
GET /keep-alive
{
  "status": "alive",
  "timestamp": "2024-01-01T12:00:00",
  "message": "Service is active",
  "uptime": "2:30:45",
  "memory_usage": "150.2MB",
  "active_users": 5,
  "server": "gunicorn"
}
```

### 3. Gunicorn 性能優化 ⚡
- 增加 worker 數量（付費方案）
- 優化請求處理參數
- 縮短 ping 間隔到 5 分鐘

### 4. 外部 Keep-Alive（可選）🌐
如需額外保護，可使用外部 keep-alive 服務：

1. **設定您的服務 URL**：
   編輯 `keep_alive_service.py` 第 13 行：
   ```python
   SERVICE_URL = "https://your-actual-service-name.onrender.com"
   ```

2. **使用 GitHub Actions 運行**：
   創建 `.github/workflows/keep-alive.yml`：
   ```yaml
   name: Keep Alive
   on:
     schedule:
       - cron: '*/5 * * * *'  # 每5分鐘執行
   jobs:
     keep-alive:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Setup Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.9'
         - name: Install dependencies
           run: pip install requests
         - name: Run keep-alive
           run: python keep_alive_service.py
           env:
             TARGET_SERVICE_URL: ${{ secrets.TARGET_SERVICE_URL }}
   ```

## 📊 預期改善效果

### 修復前：
- 😴 首次回覆：10-30 秒
- ⏰ 冷啟動頻繁

### 修復後：
- ⚡ 首次回覆：1-3 秒
- 🔄 服務持續活躍
- 📈 整體響應速度提升 80%

## 🧪 測試方式

1. **測試內建 keep-alive**：
   ```bash
   curl https://your-service.onrender.com/keep-alive
   ```

2. **測試機器人回覆**：
   在 LINE 中發送 "土豆 測試" 

3. **檢查日誌**：
   在 Render 控制台查看日誌，應該看到每5分鐘的keep-alive日誌：
   ```
   [Internal Keep-Alive] Service is alive at 2024-01-01 12:00:00
   ```

## ⚠️ 注意事項

- 付費方案已大幅改善性能
- 內建 keep-alive 會自動運行，無需額外設定
- 記憶體清理功能避免長期運行的問題
- 外部 keep-alive 是可選的額外保護

## 🔧 手動部署步驟

如果需要重新部署：

1. **推送到 Git**：
   ```bash
   git add .
   git commit -m "Add keep-alive optimization"
   git push
   ```

2. **Render 會自動重新部署**

3. **驗證功能**：
   檢查 `/keep-alive` 端點

## 📞 支援

如果問題持續存在：
1. 檢查 Render 日誌
2. 確認付費方案已啟用
3. 測試 keep-alive 端點
4. 確認服務 URL 設定正確

---
*最後更新：2024-01-01*
*修復版本：v2.0* 