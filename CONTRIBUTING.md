# 🤝 貢獻指南

感謝您對防詐騙LINE Bot項目的關注！我們歡迎所有形式的貢獻，無論是錯誤報告、功能建議、代碼改進還是文檔更新。

## 📋 貢獻方式

### 🐛 報告錯誤
如果您發現了錯誤，請：
1. 檢查 [Issues](https://github.com/your-username/anti-fraud-linebot/issues) 確認問題尚未被報告
2. 創建新的Issue，包含：
   - 清晰的錯誤描述
   - 重現步驟
   - 預期行為 vs 實際行為
   - 環境信息（Python版本、作業系統等）
   - 相關的錯誤日誌

### 💡 功能建議
我們歡迎新功能的建議：
1. 檢查現有Issues確認功能尚未被提議
2. 創建Feature Request，說明：
   - 功能的詳細描述
   - 使用場景和目標用戶
   - 可能的實現方案
   - 對現有功能的影響

### 🔧 代碼貢獻

#### 開發環境設置
1. **Fork 專案**
   ```bash
   git clone https://github.com/your-username/anti-fraud-linebot.git
   cd anti-fraud-linebot
   ```

2. **創建虛擬環境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   ```

3. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # 開發依賴
   ```

4. **設置環境變數**
   ```bash
   cp .env.example .env
   # 編輯 .env 文件，填入您的API金鑰
   ```

#### 開發流程
1. **創建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **進行開發**
   - 遵循現有的代碼風格
   - 添加適當的註釋和文檔
   - 編寫或更新測試

3. **運行測試**
   ```bash
   python test_complete_system.py
   ```

4. **代碼風格檢查**
   ```bash
   flake8 .
   black .
   ```

5. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   ```

6. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **創建Pull Request**

## 📝 代碼規範

### Python 代碼風格
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 規範
- 使用 [Black](https://black.readthedocs.io/) 進行代碼格式化
- 使用 [flake8](https://flake8.pycqa.org/) 進行代碼檢查
- 函數和類需要有適當的docstring

### 提交訊息規範
使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**類型 (type):**
- `feat`: 新功能
- `fix`: 錯誤修復
- `docs`: 文檔更新
- `style`: 代碼格式調整
- `refactor`: 代碼重構
- `test`: 測試相關
- `chore`: 其他雜項

**範例:**
```
feat(detection): 添加新的詐騙類型檢測
fix(game): 修復遊戲分數計算錯誤
docs(readme): 更新安裝說明
```

### 分支命名規範
- `feature/功能名稱`: 新功能開發
- `fix/錯誤描述`: 錯誤修復
- `docs/文檔更新`: 文檔相關
- `refactor/重構描述`: 代碼重構

## 🧪 測試指南

### 測試類型
1. **單元測試**: 測試個別函數和類
2. **整合測試**: 測試模組間的交互
3. **端到端測試**: 測試完整的用戶流程

### 編寫測試
- 每個新功能都應該有對應的測試
- 測試文件命名為 `test_*.py`
- 使用描述性的測試函數名稱
- 包含正常情況和邊界情況的測試

### 運行測試
```bash
# 運行所有測試
python test_complete_system.py

# 運行特定測試
python -m pytest test_specific_module.py

# 生成覆蓋率報告
python -m pytest --cov=. --cov-report=html
```

## 📚 文檔貢獻

### 文檔類型
- **README.md**: 項目概述和快速開始
- **API文檔**: 函數和類的詳細說明
- **用戶指南**: 使用說明和教程
- **開發者文檔**: 架構說明和開發指南

### 文檔規範
- 使用清晰、簡潔的語言
- 包含代碼範例
- 添加適當的截圖或圖表
- 保持文檔與代碼同步更新

## 🔍 代碼審查

### Pull Request 檢查清單
- [ ] 代碼遵循項目風格規範
- [ ] 包含適當的測試
- [ ] 測試全部通過
- [ ] 文檔已更新
- [ ] 提交訊息符合規範
- [ ] 沒有合併衝突

### 審查標準
- **功能性**: 代碼是否正確實現了預期功能
- **可讀性**: 代碼是否清晰易懂
- **效能**: 是否有效能問題
- **安全性**: 是否存在安全漏洞
- **可維護性**: 代碼是否易於維護和擴展

## 🏷️ 發布流程

### 版本號規範
使用 [Semantic Versioning](https://semver.org/)：
- `MAJOR.MINOR.PATCH`
- `MAJOR`: 不相容的API變更
- `MINOR`: 向後相容的功能新增
- `PATCH`: 向後相容的錯誤修復

### 發布步驟
1. 更新版本號
2. 更新 CHANGELOG.md
3. 創建發布標籤
4. 自動部署到生產環境

## 🌟 貢獻者認可

我們重視每一位貢獻者的努力：
- 所有貢獻者將被列在 README.md 中
- 重大貢獻者將獲得特別感謝
- 定期貢獻者可能被邀請成為維護者

## 📞 聯絡方式

如果您有任何問題或需要幫助：
- 創建 [GitHub Issue](https://github.com/your-username/anti-fraud-linebot/issues)
- 發送郵件到：[your-email@example.com]
- 加入我們的討論群組

## 📄 行為準則

我們致力於為所有人提供友善、安全的環境：
- 尊重不同的觀點和經驗
- 接受建設性的批評
- 專注於對社群最有利的事情
- 對其他社群成員表現同理心

違反行為準則的行為將不被容忍，可能導致暫時或永久禁止參與項目。

---

**感謝您為防詐騙事業做出的貢獻！讓我們一起守護長輩的數位安全！** 🛡️💙 