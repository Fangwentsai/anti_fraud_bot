import logging
import requests

logger = logging.getLogger(__name__)

def expand_short_url(short_url):
    """
    展開短網址，返回最終的目標 URL
    
    Args:
        short_url: 需要展開的短網址
        
    Returns:
        展開後的目標 URL，如果無法展開則返回原始 URL
    """
    try:
        logger.info(f"嘗試展開短網址: {short_url}")
        
        # 設置請求頭，模擬瀏覽器請求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        # 發送 HEAD 請求獲取重定向地址，不下載完整內容
        response = requests.head(short_url, allow_redirects=True, headers=headers, timeout=5)
        
        # 獲取最終 URL
        final_url = response.url
        
        # 如果最終 URL 與原始 URL 不同，表示展開成功
        if final_url != short_url:
            logger.info(f"短網址 {short_url} 展開為: {final_url}")
            return final_url
        else:
            # 如果HEAD請求失敗，嘗試GET請求
            response = requests.get(short_url, allow_redirects=True, headers=headers, timeout=5)
            final_url = response.url
            if final_url != short_url:
                logger.info(f"短網址 {short_url} 展開為: {final_url} (通過GET方法)")
                return final_url
            else:
                logger.warning(f"無法展開短網址 {short_url}，將使用原始URL")
                return short_url
    except Exception as e:
        logger.error(f"展開短網址時發生錯誤: {e}")
        return short_url

if __name__ == "__main__":
    # 設置日誌配置用於測試
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 測試短網址展開函數
    test_urls = [
        "https://bit.ly/3XQzXuY",       # 示例短網址
        "https://t.co/abcdefg",         # 另一個示例短網址
        "https://www.google.com",        # 正常網址，不應該變化
        "https://example.com"            # 正常網址，不應該變化
    ]
    
    for url in test_urls:
        expanded = expand_short_url(url)
        print(f"原始URL: {url}")
        print(f"展開後: {expanded}")
        print("-" * 40) 