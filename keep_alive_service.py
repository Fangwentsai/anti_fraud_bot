#!/usr/bin/env python3
"""
Keep-Alive 服務
用於定期 ping 主服務，防止 Render 免費方案休眠
可以部署在 GitHub Actions、Vercel、或其他免費服務上
"""

import requests
import time
import logging
from datetime import datetime

# 配置
SERVICE_URL = "https://your-render-service-url.onrender.com"  # 替換為你的 Render 服務 URL
PING_INTERVAL = 14 * 60  # 14 分鐘（Render 15 分鐘後休眠）
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
            headers={'User-Agent': 'KeepAlive-Bot/1.0'}
        )
        
        if response.status_code == 200:
            logger.info(f"✅ 服務 ping 成功 - 狀態碼: {response.status_code}")
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
    logger.info(f"🚀 Keep-Alive 服務啟動")
    logger.info(f"📡 目標服務: {SERVICE_URL}")
    logger.info(f"⏰ Ping 間隔: {PING_INTERVAL} 秒")
    
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"🔄 [{current_time}] 開始 ping 服務...")
            
            success = ping_service()
            
            if success:
                logger.info(f"✅ [{current_time}] 服務保持活躍")
            else:
                logger.warning(f"⚠️ [{current_time}] 服務可能有問題")
            
            logger.info(f"😴 等待 {PING_INTERVAL} 秒後進行下次 ping...")
            time.sleep(PING_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🛑 收到中斷信號，停止 Keep-Alive 服務")
            break
        except Exception as e:
            logger.error(f"❌ Keep-Alive 循環中發生錯誤: {e}")
            logger.info("🔄 5 秒後重試...")
            time.sleep(5)

if __name__ == "__main__":
    run_keep_alive() 