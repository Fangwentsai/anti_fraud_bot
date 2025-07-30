# 🚀 GitHub 設置指南

## 1. 創建GitHub倉庫

1. 登入 GitHub (https://github.com)
2. 點擊右上角的 "+" → "New repository"
3. 倉庫名稱: `domain-spoofing-detector`
4. 描述: `🛡️ 高精度網域變形攻擊檢測系統 - 95%+檢測率，支援多種攻擊類型`
5. 設為 **Private** (保護代碼)
6. 不要初始化 README (我們已經有了)
7. 點擊 "Create repository"

## 2. 推送代碼到GitHub

在終端機執行以下命令：

```bash
# 添加遠程倉庫 (替換 YOUR_USERNAME 為您的GitHub用戶名)
git remote add origin https://github.com/YOUR_USERNAME/domain-spoofing-detector.git

# 推送代碼
git branch -M main
git push -u origin main
```

## 3. 保護倉庫設置

### 3.1 設置分支保護
1. 進入倉庫 → Settings → Branches
2. 點擊 "Add rule"
3. Branch name pattern: `main`
4. 勾選以下選項：
   - ✅ Require a pull request before merging
   - ✅ Require approvals (設為 1)
   - ✅ Dismiss stale PR approvals when new commits are pushed
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Restrict pushes that create files larger than 100MB

### 3.2 設置安全政策
1. 進入 Settings → Security & analysis
2. 啟用以下功能：
   - ✅ Dependency graph
   - ✅ Dependabot alerts
   - ✅ Dependabot security updates
   - ✅ Secret scanning

### 3.3 設置訪問權限
1. 進入 Settings → Manage access
2. 確保只有必要的人員有訪問權限
3. 考慮設置團隊權限而非個人權限

## 4. 添加安全標籤

在倉庫首頁添加以下標籤：
- `security`
- `anti-fraud`
- `domain-detection`
- `phishing-protection`
- `taiwan`
- `python`

## 5. 設置 GitHub Actions (可選)

創建 `.github/workflows/security-check.yml`:

```yaml
name: Security Check

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run security tests
      run: |
        python -m pytest test_fixed_detection.py -v
```

## 6. 完成後的檢查清單

- [ ] 倉庫已設為 Private
- [ ] 分支保護規則已設置
- [ ] 安全功能已啟用
- [ ] 訪問權限已限制
- [ ] README.md 顯示正常
- [ ] 代碼已成功推送
- [ ] 安全標籤已添加

## 🔒 安全提醒

1. **絕不要**將此倉庫設為公開
2. **定期檢查**訪問權限
3. **監控**安全警報
4. **備份**重要代碼
5. **更新**依賴套件

---

完成設置後，您的網域檢測系統就安全地保護在GitHub上了！ 