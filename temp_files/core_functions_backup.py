#!/usr/bin/env python3
"""
核心功能備份 - 穩定版本鎖定
防詐騙和天氣查詢功能的備份版本
版本：v1.0.0 - 2025-05-24
狀態：✅ 已測試穩定
"""

import hashlib
import json
from datetime import datetime

# 核心功能版本資訊
CORE_VERSION = "1.0.0"
LOCK_DATE = "2025-05-24"
FUNCTIONS_STATUS = {
    "anti_fraud": "✅ 穩定",
    "weather_service": "✅ 穩定", 
    "domain_spoofing": "✅ 穩定",
    "flex_message": "✅ 穩定"
}

# 核心文件清單和校驗碼
CORE_FILES = {
    "anti_fraud_clean_app.py": {
        "description": "主程式 - 防詐騙LINE Bot核心邏輯",
        "critical_functions": [
            "handle_message",
            "detect_fraud_with_chatgpt", 
            "parse_fraud_analysis",
            "should_perform_fraud_analysis"
        ],
        "last_stable": "2025-05-24 11:33:00"
    },
    "weather_service.py": {
        "description": "天氣服務 - 中央氣象署API整合",
        "critical_functions": [
            "handle_weather_query",
            "get_weather_forecast",
            "_parse_cwb_weather_data",
            "get_taipei_time"
        ],
        "last_stable": "2025-05-24 11:33:00"
    },
    "domain_spoofing_detector.py": {
        "description": "網域變形攻擊檢測",
        "critical_functions": [
            "detect_domain_spoofing",
            "_is_domain_suffix_spoofing"
        ],
        "last_stable": "2025-05-24 10:00:00"
    },
    "flex_message_service.py": {
        "description": "Flex訊息服務",
        "critical_functions": [
            "FlexMessageService",
            "create_domain_spoofing_flex_message"
        ],
        "last_stable": "2025-05-24 10:00:00"
    }
}

def calculate_file_hash(filepath):
    """計算文件的MD5校驗碼"""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            return hashlib.md5(content).hexdigest()
    except FileNotFoundError:
        return None

def create_backup_snapshot():
    """創建當前核心功能的快照"""
    snapshot = {
        "version": CORE_VERSION,
        "timestamp": datetime.now().isoformat(),
        "status": "LOCKED",
        "files": {}
    }
    
    for filename, info in CORE_FILES.items():
        file_hash = calculate_file_hash(filename)
        snapshot["files"][filename] = {
            "hash": file_hash,
            "description": info["description"],
            "critical_functions": info["critical_functions"],
            "last_stable": info["last_stable"],
            "exists": file_hash is not None
        }
    
    return snapshot

def verify_core_integrity():
    """驗證核心功能完整性"""
    print("🔒 核心功能完整性檢查")
    print("=" * 50)
    
    all_good = True
    
    for filename, info in CORE_FILES.items():
        print(f"\n📁 檢查文件: {filename}")
        print(f"📝 描述: {info['description']}")
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 檢查關鍵函數是否存在
            missing_functions = []
            for func in info["critical_functions"]:
                if f"def {func}" not in content:
                    missing_functions.append(func)
            
            if missing_functions:
                print(f"❌ 缺少關鍵函數: {', '.join(missing_functions)}")
                all_good = False
            else:
                print(f"✅ 所有關鍵函數完整")
                
            # 計算文件大小
            file_size = len(content.encode('utf-8'))
            print(f"📊 文件大小: {file_size} bytes")
            
        except FileNotFoundError:
            print(f"❌ 文件不存在")
            all_good = False
        except Exception as e:
            print(f"❌ 檢查失敗: {e}")
            all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 核心功能完整性檢查通過！")
    else:
        print("⚠️ 發現問題，請檢查上述錯誤")
    
    return all_good

def create_protection_readme():
    """創建保護說明文件"""
    readme_content = f"""# 🔒 核心功能保護說明

## 📋 概述
此目錄包含防詐騙LINE Bot的核心功能，已於 {LOCK_DATE} 鎖定為穩定版本 v{CORE_VERSION}。

## 🛡️ 受保護的功能

### 1. 防詐騙檢測 (anti_fraud_clean_app.py)
- ✅ 網域變形攻擊檢測
- ✅ 詐騙風險分析
- ✅ 安全網域白名單
- ✅ Flex訊息警告

### 2. 天氣查詢服務 (weather_service.py)
- ✅ 中央氣象署API整合
- ✅ 真實天氣資料獲取
- ✅ 台北時區轉換
- ✅ 降級機制

### 3. 網域偽裝檢測 (domain_spoofing_detector.py)
- ✅ 子網域合法性驗證
- ✅ 字元變形檢測
- ✅ 可疑模式識別

### 4. Flex訊息服務 (flex_message_service.py)
- ✅ 詐騙警告訊息
- ✅ 網域偽裝警告
- ✅ 美觀的UI設計

## ⚠️ 重要警告

### 🚫 請勿修改以下文件：
{chr(10).join([f"- {filename}" for filename in CORE_FILES.keys()])}

### 🔧 如需修改：
1. 先備份當前版本
2. 在測試環境進行修改
3. 完整測試所有功能
4. 更新版本號和文檔

## 🔍 完整性檢查

運行以下命令檢查核心功能：
```bash
python3 core_functions_backup.py
```

## 📊 功能狀態

{chr(10).join([f"- {func}: {status}" for func, status in FUNCTIONS_STATUS.items()])}

## 🆘 故障恢復

如果核心功能出現問題：

1. **檢查完整性**：
   ```bash
   python3 core_functions_backup.py
   ```

2. **從Git恢復**：
   ```bash
   git checkout HEAD -- anti_fraud_clean_app.py weather_service.py
   ```

3. **重新部署**：
   ```bash
   git add .
   git commit -m "🔧 恢復核心功能到穩定版本"
   git push origin main
   ```

## 📞 技術支援

- **版本**: v{CORE_VERSION}
- **鎖定日期**: {LOCK_DATE}
- **最後測試**: 2025-05-24 11:33:00
- **狀態**: 🔒 已鎖定保護

## 🎯 測試清單

在修改任何核心功能前，請確保以下測試通過：

### 防詐騙功能測試：
- [ ] 假冒網域檢測 (event.liontraveler.com)
- [ ] 合法子網域通過 (event.liontravel.com)
- [ ] Flex訊息正常顯示
- [ ] 風險等級正確判定

### 天氣查詢功能測試：
- [ ] 台北天氣查詢
- [ ] 日期時間查詢
- [ ] API金鑰正常運作
- [ ] 降級機制正常

記住：**穩定比功能更重要！** 🛡️
"""
    
    with open("CORE_PROTECTION_README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("📝 已創建保護說明文件: CORE_PROTECTION_README.md")

if __name__ == "__main__":
    print(f"🔒 核心功能保護系統 v{CORE_VERSION}")
    print(f"📅 鎖定日期: {LOCK_DATE}")
    print()
    
    # 創建快照
    snapshot = create_backup_snapshot()
    
    # 保存快照
    with open("core_functions_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    
    print("📸 已創建核心功能快照: core_functions_snapshot.json")
    
    # 驗證完整性
    verify_core_integrity()
    
    # 創建保護說明
    create_protection_readme()
    
    print("\n🎉 核心功能保護設定完成！")
    print("💡 建議將此版本標記為Git tag以便日後恢復") 