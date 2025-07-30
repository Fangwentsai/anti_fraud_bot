# 防詐騙機器人專案結構指南

## 📁 建議的專案結構

```
anti_fraud_bot/
├── 📄 主要檔案
│   ├── anti_fraud_clean_app.py      # 主應用程式
│   ├── config.py                    # 配置檔案
│   ├── requirements.txt             # 依賴套件
│   ├── Procfile                    # 部署配置
│   └── render.yaml                 # Render部署配置
│
├── 🧩 核心模組
│   ├── fraud_knowledge.py          # 詐騙知識庫
│   ├── weather_service.py          # 天氣服務
│   ├── flex_message_service.py     # Flex訊息服務
│   ├── game_service.py             # 遊戲服務
│   ├── image_analysis_service.py   # 圖片分析服務
│   ├── domain_spoofing_detector.py # 域名欺詐檢測
│   ├── firebase_manager.py         # Firebase管理
│   └── keep_alive_service.py      # 保活服務
│
├── 📊 資料檔案
│   ├── safe_domains.json          # 安全域名列表
│   ├── fraud_tactics.json         # 詐騙手法資料
│   ├── fraud_detection_questions.json # 防詐問題庫
│   └── potato_game_questions.json # 遊戲問題庫
│
├── 🧪 測試檔案 (tests/)
│   ├── test_*.py                  # 各種測試檔案
│   └── comprehensive_test_report.py
│
├── 📦 備份檔案 (backups/)
│   ├── backup_files/              # 備份檔案
│   └── duplicate_flex_files/      # 重複的flex檔案
│
├── 🗂️ 臨時檔案 (temp_files/)
│   ├── temp_*.py                  # 臨時Python檔案
│   ├── temp_*.json               # 臨時JSON檔案
│   └── fixed_*.json              # 修復後的檔案
│
├── 📋 文檔檔案
│   ├── README.md                  # 專案說明
│   ├── DEPLOYMENT.md              # 部署指南
│   ├── CONTRIBUTING.md            # 貢獻指南
│   └── *.md                      # 其他說明文件
│
└── 🎨 前端模板 (templates/)
    ├── index.html                 # 首頁模板
    ├── statistics.html            # 統計頁面
    └── watch_ad.html             # 廣告頁面
```

## 🧹 清理建議

### 1. 立即清理項目
- **備份檔案**: 移動所有 `.bak`, `_backup.py` 檔案到 `backups/` 目錄
- **重複檔案**: 保留最大的 `flex_message_service.py`，刪除其他版本
- **測試檔案**: 移動所有 `test_*.py` 到 `tests/` 目錄
- **臨時檔案**: 移動所有 `temp_*.py`, `temp_*.json` 到 `temp_files/` 目錄

### 2. 模組化重構
- **主檔案過大**: 將 `anti_fraud_clean_app.py` (4037行) 進一步模組化
- **功能分離**: 將不同功能分離到獨立模組
- **配置集中**: 統一管理所有配置到 `config.py`

### 3. 檔案命名規範
- **主檔案**: 使用描述性名稱，避免版本號
- **模組檔案**: 使用小寫和下劃線
- **配置檔案**: 使用 `.json`, `.yaml` 格式
- **測試檔案**: 使用 `test_` 前綴

## 🔧 使用清理腳本

```bash
# 執行清理腳本
python3 project_cleanup.py

# 腳本會自動：
# 1. 創建必要的目錄結構
# 2. 識別並備份重複檔案
# 3. 移動測試和臨時檔案
# 4. 生成清理報告
```

## 📊 清理後的好處

### 1. 提高可維護性
- 清晰的檔案結構
- 容易找到相關檔案
- 減少重複程式碼

### 2. 提升開發效率
- 快速定位功能模組
- 簡化測試流程
- 減少混淆

### 3. 便於部署
- 清晰的依賴關係
- 簡化的部署流程
- 減少部署錯誤

## 🚀 後續建議

### 1. 定期維護
- 每週清理臨時檔案
- 每月檢查重複檔案
- 定期更新文檔

### 2. 版本控制
- 使用 Git 標籤管理版本
- 建立分支進行功能開發
- 定期合併和清理

### 3. 自動化
- 設置自動測試
- 自動部署流程
- 定期備份重要檔案

## 📝 注意事項

1. **備份重要**: 清理前務必備份重要檔案
2. **逐步進行**: 不要一次性刪除所有檔案
3. **測試驗證**: 清理後要測試功能是否正常
4. **文檔更新**: 更新相關文檔和說明

---

*最後更新: 2024年12月* 