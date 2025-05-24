#!/usr/bin/env python3
"""
診斷腳本 - 檢查部署所需的文件
"""
import os
import sys

def check_file_exists(filename):
    """檢查文件是否存在"""
    if os.path.exists(filename):
        size = os.path.getsize(filename)
        print(f"✅ {filename} 存在 (大小: {size} bytes)")
        return True
    else:
        print(f"❌ {filename} 不存在")
        return False

def main():
    print("🔍 檢查部署文件...")
    print(f"📁 當前目錄: {os.getcwd()}")
    print(f"📋 目錄內容:")
    
    # 列出當前目錄的所有文件
    for item in sorted(os.listdir('.')):
        if os.path.isfile(item):
            size = os.path.getsize(item)
            print(f"   📄 {item} ({size} bytes)")
        else:
            print(f"   📁 {item}/")
    
    print("\n🎯 檢查關鍵文件:")
    
    # 檢查關鍵文件
    required_files = [
        'requirements.txt',
        'anti_fraud_clean_app.py',
        'render.yaml',
        'safe_domains.json'
    ]
    
    all_exist = True
    for filename in required_files:
        if not check_file_exists(filename):
            all_exist = False
    
    if all_exist:
        print("\n✅ 所有關鍵文件都存在！")
        
        # 檢查requirements.txt內容
        print("\n📦 requirements.txt 內容:")
        try:
            with open('requirements.txt', 'r') as f:
                content = f.read()
                print(content)
        except Exception as e:
            print(f"❌ 讀取requirements.txt失敗: {e}")
            
    else:
        print("\n❌ 缺少關鍵文件！")
        sys.exit(1)

if __name__ == "__main__":
    main() 