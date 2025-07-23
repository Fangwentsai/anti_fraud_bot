#!/usr/bin/env python3
"""
Keep-Alive 服務
用於定期 ping 主服務，防止 Render 服務休眠
可以部署在 GitHub Actions、Vercel、或其他免費服務上
"""

import requests
import time
import logging
from datetime import datetime
import os

# 配置 - 從環境變數或手動設定
SERVICE_URL = os.environ.get('TARGET_SERVICE_URL', "https://anti-fraud-bot.onrender.com")  # 請替換為你的實際 Render 服務 URL
PING_INTERVAL = 5 * 60  # 5 分鐘（付費方案保險設定）
TIMEOUT = 30

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ping_service():
    """Ping 主服務以保持其活躍狀態"""
    try:
        response = requests.get(
            f"{SERVICE_URL}/keep-alive",
            timeout=TIMEOUT,
            headers={'User-Agent': 'KeepAlive-Bot/2.0'}
        )
        
        if response.status_code == 200:
            data = response.json()
            uptime = data.get('uptime', 'unknown')
            memory = data.get('memory_usage', 'unknown')
            active_users = data.get('active_users', 0)
            logger.info(f"✅ 服務 ping 成功 - 運行時間: {uptime}, 記憶體: {memory}, 活躍用戶: {active_users}")
            return True
        else:
            logger.warning(f"⚠️ 服務 ping 返回異常狀態碼: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ 服務 ping 超時")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ 無法連接到服務")
        return False
    except Exception as e:
        logger.error(f"❌ Ping 服務時發生錯誤: {e}")
        return False

def run_keep_alive():
    """運行 keep-alive 循環"""
    logger.info(f"🚀 Keep-Alive 服務啟動 v2.0")
    logger.info(f"📡 目標服務: {SERVICE_URL}")
    logger.info(f"⏰ Ping 間隔: {PING_INTERVAL} 秒 ({PING_INTERVAL//60} 分鐘) - 保險設定")
    
    # 檢查服務 URL 是否已設定
    if "your-app-name" in SERVICE_URL:
        logger.warning("⚠️ 請設定正確的 SERVICE_URL！")
        logger.warning("🔧 請將 SERVICE_URL 更改為您的實際 Render 服務網址")
        return
    
    consecutive_failures = 0
    max_failures = 3
    
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"🔄 [{current_time}] 開始 ping 服務...")
            
            success = ping_service()
            
            if success:
                logger.info(f"✅ [{current_time}] 服務保持活躍")
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logger.warning(f"⚠️ [{current_time}] 服務可能有問題 (連續失敗: {consecutive_failures}/{max_failures})")
                
                if consecutive_failures >= max_failures:
                    logger.error(f"🚨 服務連續失敗 {max_failures} 次，可能需要人工介入")
                    # 可以在這裡添加通知機制
            
            logger.info(f"😴 等待 {PING_INTERVAL} 秒後進行下次 ping...")
            time.sleep(PING_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🛑 收到中斷信號，停止 Keep-Alive 服務")
            break
        except Exception as e:
            logger.error(f"❌ Keep-Alive 循環中發生錯誤: {e}")
            logger.info("🔄 30 秒後重試...")
            time.sleep(30)

if __name__ == "__main__":
    run_keep_alive() 