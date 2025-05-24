#!/usr/bin/env python3
"""
🔒 核心功能保護腳本
簡化版本 - 專注於最重要的防詐騙和天氣功能
"""

import os
import hashlib
import json
from datetime import datetime

# 核心功能版本
VERSION = "1.0.0-stable"
LOCK_DATE = "2025-05-24"

# 最重要的核心文件
PROTECTED_FILES = [
    "anti_fraud_clean_app.py",  # 主程式
    "weather_service.py"        # 天氣服務
]

def calculate_file_hash(filepath):
    """計算文件MD5校驗碼"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def create_protection_snapshot():
    """創建保護快照"""
    snapshot = {
        "version": VERSION,
        "lock_date": LOCK_DATE,
        "timestamp": datetime.now().isoformat(),
        "files": {}
    }
    
    for filepath in PROTECTED_FILES:
        file_hash = calculate_file_hash(filepath)
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        
        snapshot["files"][filepath] = {
            "hash": file_hash,
            "size": file_size,
            "exists": os.path.exists(filepath)
        }
    
    # 保存快照
    with open("protection_snapshot.json", "w") as f:
        json.dump(snapshot, f, indent=2)
    
    return snapshot

def verify_protection():
    """驗證核心功能保護狀態"""
    print(f"🔒 核心功能保護驗證 v{VERSION}")
    print("=" * 50)
    
    all_good = True
    
    for filepath in PROTECTED_FILES:
        print(f"\n📁 檢查: {filepath}")
        
        if not os.path.exists(filepath):
            print("❌ 文件不存在")
            all_good = False
            continue
        
        # 檢查文件大小
        size = os.path.getsize(filepath)
        print(f"📊 大小: {size:,} bytes")
        
        # 檢查關鍵內容
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if filepath == "anti_fraud_clean_app.py":
                # 檢查防詐騙核心功能
                checks = [
                    ("防詐騙檢測", "detect_fraud_with_chatgpt" in content),
                    ("訊息處理", "handle_message" in content),
                    ("風險分析", "parse_fraud_analysis" in content),
                    ("天氣整合", "首先檢查是否為天氣查詢" in content)
                ]
            elif filepath == "weather_service.py":
                # 檢查天氣服務核心功能
                checks = [
                    ("天氣查詢", "handle_weather_query" in content),
                    ("API整合", "opendata.cwa.gov.tw" in content),
                    ("台北時區", "TAIPEI_TZ" in content),
                    ("降級機制", "_get_mock_weather_data" in content)
                ]
            
            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"  {status} {check_name}")
                if not check_result:
                    all_good = False
                    
        except Exception as e:
            print(f"❌ 檢查失敗: {e}")
            all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 所有核心功能完整！")
        print("🛡️ 系統處於保護狀態")
    else:
        print("⚠️ 發現問題，請檢查核心功能")
    
    return all_good

def create_recovery_guide():
    """創建恢復指南"""
    guide = f"""# 🆘 核心功能恢復指南

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
curl -X POST https://your-bot-url/callback \\
  -H "Content-Type: application/json" \\
  -d '{{"events":[{{"message":{{"text":"https://event.liontraveler.com"}}}}]}}'
```

### 天氣查詢測試
```bash
# 測試天氣功能
python3 -c "from weather_service import handle_weather_query; print(handle_weather_query('台北天氣', '測試'))"
```

## 緊急聯絡

- **版本**: {VERSION}
- **鎖定日期**: {LOCK_DATE}
- **Git標籤**: v1.0.0-stable

記住：**穩定比功能更重要！** 🛡️
"""
    
    with open("RECOVERY_GUIDE.md", "w", encoding="utf-8") as f:
        f.write(guide)
    
    print("📝 已創建恢復指南: RECOVERY_GUIDE.md")

if __name__ == "__main__":
    print(f"🔒 啟動核心功能保護系統")
    print(f"📅 版本: {VERSION}")
    print(f"🗓️ 鎖定日期: {LOCK_DATE}")
    print()
    
    # 創建保護快照
    snapshot = create_protection_snapshot()
    print("📸 已創建保護快照: protection_snapshot.json")
    
    # 驗證保護狀態
    is_protected = verify_protection()
    
    # 創建恢復指南
    create_recovery_guide()
    
    print(f"\n🎯 保護狀態: {'🔒 已保護' if is_protected else '⚠️ 需要修復'}")
    print("💡 建議定期運行此腳本檢查核心功能完整性") 