#!/usr/bin/env python3
"""
測試 Gunicorn 配置是否正確
"""

import os
import subprocess
import sys

def test_gunicorn_config():
    """測試 Gunicorn 配置文件"""
    print("🔍 測試 Gunicorn 配置...")
    
    # 檢查配置文件是否存在
    if not os.path.exists('gunicorn.conf.py'):
        print("❌ gunicorn.conf.py 不存在")
        return False
    
    # 檢查主程式是否存在
    if not os.path.exists('anti_fraud_clean_app.py'):
        print("❌ anti_fraud_clean_app.py 不存在")
        return False
    
    # 測試配置文件語法
    try:
        import gunicorn.conf
        print("✅ Gunicorn 配置文件語法正確")
    except Exception as e:
        print(f"❌ Gunicorn 配置文件語法錯誤: {e}")
        return False
    
    # 測試 Gunicorn 是否能正確載入應用程式
    try:
        cmd = ["gunicorn", "--check-config", "--config", "gunicorn.conf.py", "anti_fraud_clean_app:app"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Gunicorn 能正確載入應用程式")
            return True
        else:
            print(f"❌ Gunicorn 載入失敗: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️ Gunicorn 測試超時")
        return False
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        return False

def test_environment():
    """測試環境變數"""
    print("\n🔍 檢查環境變數...")
    
    required_vars = [
        'LINE_CHANNEL_ACCESS_TOKEN',
        'LINE_CHANNEL_SECRET', 
        'OPENAI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ 缺少環境變數: {', '.join(missing_vars)}")
    else:
        print("✅ 所有必要環境變數都已設定")
    
    # 檢查 FLASK_ENV
    flask_env = os.environ.get('FLASK_ENV', 'development')
    print(f"🔧 FLASK_ENV: {flask_env}")
    
    # 檢查 PORT
    port = os.environ.get('PORT', '8080')
    print(f"🔧 PORT: {port}")

if __name__ == "__main__":
    print("🚀 開始測試 Gunicorn 配置...")
    
    test_environment()
    
    if test_gunicorn_config():
        print("\n✅ 所有測試通過！Gunicorn 配置正確")
        sys.exit(0)
    else:
        print("\n❌ 測試失敗！請檢查配置")
        sys.exit(1) 