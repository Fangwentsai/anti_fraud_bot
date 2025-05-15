# Firebase設置指南

本文件說明如何設置Firebase並將其與防詐騙Line機器人連接。

## 1. 創建Firebase項目

1. 前往 [Firebase控制台](https://console.firebase.google.com/)
2. 點擊"創建項目"
3. 輸入項目名稱，如"anti-fraud-linebot"
4. 按照提示完成項目創建

## 2. 設置Firestore數據庫

1. 在Firebase控制台中，選擇"構建" > "Firestore Database"
2. 點擊"創建數據庫"
3. 選擇"以生產模式啟動"
4. 選擇最近的數據庫位置（如亞洲-東北1）
5. 點擊"啟用"

## 3. 創建服務賬號並下載密鑰

1. 在Firebase控制台中，點擊齒輪圖標打開項目設置
2. 選擇"服務賬號"標籤
3. 選擇"Firebase Admin SDK"，然後選擇"Python"
4. 點擊"生成新的私鑰"
5. 下載JSON密鑰文件並重命名為`firebase-key.json`
6. 將此文件放在機器人項目的根目錄中

## 4. 配置Firestore安全規則

1. 在Firebase控制台中，選擇"構建" > "Firestore Database"
2. 點擊"規則"標籤
3. 設置適當的安全規則，如：

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false; // 僅通過服務器訪問
    }
  }
}
```

4. 點擊"發布"

## 5. 在機器人代碼中配置Firebase

有兩種方式配置Firebase：

### 方式1: 使用密鑰文件

1. 將下載的`firebase-key.json`放在機器人項目的根目錄中
2. 在`.env`文件中設置：
   ```
   FIREBASE_SERVICE_ACCOUNT_PATH=firebase-key.json
   ```

### 方式2: 使用環境變量

1. 在`.env`文件中設置：
   ```
   FIREBASE_CREDENTIALS={"type":"service_account","project_id":"你的項目ID","private_key_id":"私鑰ID","private_key":"私鑰內容","client_email":"客戶端郵箱","client_id":"客戶端ID",...}
   ```
   
   > 注意：將JSON密鑰文件的全部內容作為字符串放入FIREBASE_CREDENTIALS環境變量

## 6. 在Render部署時配置Firebase

在Render控制台中，為您的Web服務設置環境變量：

1. 點擊"Environment"
2. 添加環境變量：
   - `FIREBASE_CREDENTIALS`: 將`firebase-key.json`的全部內容轉換為單行字符串

## 7. 數據庫結構

防詐騙Line機器人使用以下集合：

1. `users`: 存儲用戶資料
   - 文檔ID: Line用戶ID
   - 字段:
     - `display_name`: 用戶顯示名稱
     - `last_interaction`: 最近互動時間
     - `interaction_count`: 互動次數

2. `interactions`: 存儲所有用戶互動
   - 字段:
     - `user_id`: Line用戶ID
     - `display_name`: 用戶顯示名稱
     - `message`: 用戶消息
     - `response`: 機器人響應
     - `timestamp`: 時間戳
     - `is_fraud_related`: 是否與詐騙相關
     - `fraud_type`: 詐騙類型（如果有）
     - `risk_level`: 風險等級（如果有）

3. `fraud_reports`: 存儲詐騙相關報告
   - 字段:
     - `user_id`: Line用戶ID
     - `display_name`: 用戶顯示名稱
     - `message`: 用戶消息
     - `fraud_type`: 詐騙類型
     - `risk_level`: 風險等級
     - `timestamp`: 時間戳

## 8. 測試Firebase連接

部署機器人後，通過以下方式測試Firebase連接：

1. 向機器人發送訊息
2. 檢查Firebase控制台中的Firestore數據庫，確認數據是否正確記錄
3. 要求機器人顯示"我的紀錄"，確認是否能檢索之前的互動記錄 