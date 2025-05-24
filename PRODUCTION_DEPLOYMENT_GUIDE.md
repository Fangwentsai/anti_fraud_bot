# 🚀 生產環境部署指南

## 📋 問題診斷結果

### 本地環境狀態
- ✅ 觸發功能正常：「選哪顆土豆」可以正確觸發遊戲
- ✅ 按鈕標籤正確：所有標籤都是4字符（「選項 A」、「選項 B」等）
- ✅ Flex Message結構完整
- ✅ JSON序列化正常

### 生產環境問題
- ❌ LINE Bot API返回400錯誤
- ❌ 錯誤訊息：`"invalid property", "property": "/footer/contents/0/action/label"`
- 🔍 **根本原因**：生產環境使用的是舊版本代碼，未包含按鈕標籤修復

## 🔧 修復方案

### 方案1：重新部署（推薦）

如果您使用的是Render、Heroku等平台：

1. **推送最新代碼到Git**
   ```bash
   git add .
   git commit -m "🎮 修復土豆遊戲按鈕標籤問題"
   git push origin main
   ```

2. **觸發重新部署**
   - Render：會自動檢測到Git推送並重新部署
   - Heroku：`git push heroku main`
   - 其他平台：按照平台指引重新部署

3. **驗證部署**
   - 檢查部署日誌確認成功
   - 測試「選哪顆土豆」功能

### 方案2：手動更新文件

如果無法重新部署，可以手動更新關鍵文件：

1. **更新 `game_service.py`**
   - 確保第137行的按鈕標籤生成邏輯為：
   ```python
   button_label = f"選項 {chr(65 + i)}"  # A, B, C, D...
   ```

2. **更新觸發關鍵詞**
   - 確保第349行的遊戲觸發關鍵詞包含：
   ```python
   game_keywords = [
       "選哪顆土豆", "玩土豆", "選土豆", "土豆遊戲", 
       "玩遊戲", "選土豆遊戲", "開始遊戲"
   ]
   ```

3. **重啟應用程式**

## 📊 部署檢查清單

### 部署前檢查
- [ ] 本地測試通過
- [ ] Git提交包含所有修復
- [ ] 環境變數設定正確

### 部署後驗證
- [ ] 應用程式啟動成功
- [ ] 「選哪顆土豆」可以觸發遊戲
- [ ] 遊戲按鈕可以正常顯示
- [ ] 沒有LINE Bot API錯誤

## 🔍 測試步驟

### 1. 觸發測試
在LINE中發送：`選哪顆土豆`

**預期結果：**
- 機器人回應防詐騙小遊戲
- 顯示4個按鈕：「選項 A」、「選項 B」、「選項 C」、「選項 D」
- 沒有400錯誤

### 2. 按鈕測試
點擊任一選項按鈕

**預期結果：**
- 顯示遊戲結果
- 包含正確答案和解釋
- 提供「再玩一次」按鈕

### 3. 日誌檢查
檢查應用程式日誌

**預期結果：**
- 沒有LineBotApiError
- 沒有400狀態碼錯誤
- 遊戲觸發和回應正常記錄

## 🚨 常見問題排除

### 問題1：仍然出現400錯誤
**可能原因：**
- 代碼未正確更新
- 快取問題

**解決方案：**
1. 確認Git推送成功
2. 強制重新部署
3. 清除應用程式快取
4. 檢查部署日誌

### 問題2：觸發詞不工作
**可能原因：**
- `game_service.py`中的觸發關鍵詞未更新

**解決方案：**
1. 檢查第349行的`game_keywords`列表
2. 確保包含「選哪顆土豆」
3. 重啟應用程式

### 問題3：按鈕顯示異常
**可能原因：**
- Flex Message結構問題
- LINE SDK版本不兼容

**解決方案：**
1. 檢查`requirements.txt`中的LINE SDK版本
2. 確認Flex Message結構正確
3. 測試本地環境

## 📱 部署平台特定指引

### Render
1. 進入Render Dashboard
2. 選擇您的服務
3. 點擊「Manual Deploy」→「Deploy latest commit」
4. 等待部署完成

### Heroku
```bash
git push heroku main
heroku logs --tail
```

### Railway
```bash
railway up
railway logs
```

### 自建伺服器
```bash
git pull origin main
sudo systemctl restart your-app-service
sudo systemctl status your-app-service
```

## 📞 支援聯絡

如果部署後仍有問題，請提供：
1. 部署平台名稱
2. 錯誤日誌
3. 測試步驟和結果
4. 應用程式版本信息

---

**部署完成後，「選哪顆土豆」功能將完全恢復正常！** 🎮✨

**最後更新：** 2025-05-24  
**狀態：** 🚀 準備部署 