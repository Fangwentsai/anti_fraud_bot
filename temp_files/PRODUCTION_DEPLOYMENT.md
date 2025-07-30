# 🚀 生產環境部署指南

## ⚠️ 重要：關於開發伺服器警告

如果您看到以下警告：
```
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
```

這表示您正在使用 Flask 的內建開發伺服器，**必須**在生產環境中使用 Gunicorn。

## 🔧 最新修復（2025-05-24）

我們已經修復了導致生產環境仍然顯示開發伺服器警告的問題：

### 修復內容
1. **主程式邏輯修正**：在生產環境中不再啟動 Flask 開發伺服器
2. **部署腳本修正**：移除了 `deploy.sh` 中直接執行 Python 檔案的命令
3. **Render.com 配置簡化**：直接使用 Gunicorn 啟動命令
4. **Gunicorn 配置改進**：添加更詳細的日誌和端口配置

### 修復後的行為
- **生產環境**：只能通過 Gunicorn 啟動，直接執行 Python 檔案會退出並提示錯誤
- **開發環境**：仍然可以直接執行 Python 檔案使用 Flask 開發伺服器

## 🛠️ 正確的部署方式

### 1. Render.com 部署（推薦）
我們的 `render.yaml` 已經配置為使用 Gunicorn：
```yaml
startCommand: gunicorn --config gunicorn.conf.py anti_fraud_clean_app:app
```

### 2. Heroku 部署
`Procfile` 已經配置為使用 Gunicorn：
```
web: gunicorn --bind 0.0.0.0:$PORT anti_fraud_clean_app:app
```

### 3. 手動部署
```bash
# 安裝依賴
pip install -r requirements.txt

# 使用 Gunicorn 啟動（生產環境）
gunicorn --config gunicorn.conf.py anti_fraud_clean_app:app

# 或者簡單啟動
gunicorn --bind 0.0.0.0:8080 anti_fraud_clean_app:app
```

### 4. 開發環境
```bash
# 設定開發環境
export FLASK_ENV=development

# 直接執行（僅限開發）
python anti_fraud_clean_app.py
```

## 🔧 Gunicorn 配置說明

我們的 `gunicorn.conf.py` 包含以下優化：

### 性能設定
- **Workers**: 根據 CPU 核心數自動調整（最多4個）
- **連接數**: 每個 worker 最多 1000 個連接
- **請求限制**: 每個 worker 處理 1000 個請求後重啟

### 超時設定
- **請求超時**: 30 秒
- **Keep-alive**: 2 秒
- **優雅關閉**: 30 秒

### 日誌設定
- **存取日誌**: 輸出到 stdout
- **錯誤日誌**: 輸出到 stderr
- **日誌等級**: info
- **詳細回調**: 包含啟動、關閉等狀態日誌

## 📊 性能比較

| 伺服器類型 | 併發處理 | 穩定性 | 生產適用 |
|-----------|---------|--------|----------|
| Flask 開發伺服器 | ❌ 低 | ❌ 差 | ❌ 不適用 |
| Gunicorn | ✅ 高 | ✅ 優秀 | ✅ 適用 |

## 🧪 測試配置

使用我們提供的測試腳本：
```bash
python test_gunicorn.py
```

這個腳本會檢查：
- Gunicorn 配置文件語法
- 主程式文件存在性
- 環境變數設定
- Gunicorn 載入應用程式的能力

## 🚨 常見問題

### Q: 為什麼還是看到開發伺服器警告？
A: 檢查以下項目：
1. 確認 `FLASK_ENV=production` 環境變數已設定
2. 確認使用 Gunicorn 啟動而不是直接執行 Python 檔案
3. 檢查部署平台的啟動命令
4. **新增**：確認您使用的是最新版本的代碼（2025-05-24 之後）

### Q: Gunicorn 啟動失敗怎麼辦？
A: 檢查以下項目：
1. 確認 `requirements.txt` 包含 `gunicorn==21.2.0`
2. 檢查 `gunicorn.conf.py` 語法是否正確
3. 查看錯誤日誌獲取詳細信息
4. 運行 `python test_gunicorn.py` 進行診斷

### Q: 如何監控 Gunicorn 性能？
A: 可以使用以下方法：
1. 查看 Gunicorn 日誌
2. 監控記憶體和 CPU 使用率
3. 使用 APM 工具（如 New Relic、DataDog）

## 🔍 健康檢查

添加健康檢查端點：
```python
@app.route("/health")
def health_check():
    return {
        "status": "healthy",
        "server": "gunicorn",
        "timestamp": datetime.now().isoformat()
    }
```

## 📈 監控建議

1. **記憶體使用**: 監控 worker 記憶體使用情況
2. **回應時間**: 監控 API 回應時間
3. **錯誤率**: 監控 5xx 錯誤率
4. **併發數**: 監控同時連接數

## 🔒 安全建議

1. **環境變數**: 敏感資訊使用環境變數
2. **HTTPS**: 生產環境必須使用 HTTPS
3. **防火牆**: 限制不必要的端口存取
4. **日誌**: 定期檢查錯誤日誌

---

**記住**: 在生產環境中**絕對不要**使用 Flask 開發伺服器！

**最新更新**: 2025-05-24 - 修復了所有導致開發伺服器警告的問題 