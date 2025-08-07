#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import urllib.parse
from bs4 import BeautifulSoup
import re
import html
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def expand_short_url_with_full_redirect(url, max_redirects=10):
    """展開短網址並追蹤所有重定向到最終目的地"""
    redirect_chain = [url]
    current_url = url
    page_title = None
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        for i in range(max_redirects):
            logger.info(f"第 {i+1} 次請求: {current_url}")
            
            try:
                # 先嘗試 HEAD 請求
                response = session.head(current_url, allow_redirects=False, timeout=10, verify=False)
                logger.info(f"HEAD 狀態碼: {response.status_code}")
                
                if response.status_code in [301, 302, 303, 307, 308]:
                    # 有重定向
                    redirect_url = response.headers.get('Location')
                    if redirect_url:
                        # 處理相對URL
                        if redirect_url.startswith('/'):
                            parsed = urllib.parse.urlparse(current_url)
                            redirect_url = f"{parsed.scheme}://{parsed.netloc}{redirect_url}"
                        elif not redirect_url.startswith('http'):
                            redirect_url = urllib.parse.urljoin(current_url, redirect_url)
                        
                        current_url = redirect_url
                        redirect_chain.append(current_url)
                        logger.info(f"HTTP重定向到: {current_url}")
                        continue
                
                # 如果沒有HTTP重定向，嘗試 GET 請求
                response = session.get(current_url, allow_redirects=False, timeout=10, verify=False)
                logger.info(f"GET 狀態碼: {response.status_code}")
                
                if response.status_code in [301, 302, 303, 307, 308]:
                    # 有重定向
                    redirect_url = response.headers.get('Location')
                    if redirect_url:
                        # 處理相對URL
                        if redirect_url.startswith('/'):
                            parsed = urllib.parse.urlparse(current_url)
                            redirect_url = f"{parsed.scheme}://{parsed.netloc}{redirect_url}"
                        elif not redirect_url.startswith('http'):
                            redirect_url = urllib.parse.urljoin(current_url, redirect_url)
                        
                        current_url = redirect_url
                        redirect_chain.append(current_url)
                        logger.info(f"HTTP重定向到: {current_url}")
                        continue
                
                # 如果沒有HTTP重定向，檢查頁面內容中的重定向
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 獲取頁面標題
                    title_tag = soup.find('title')
                    if title_tag:
                        page_title = title_tag.get_text().strip()
                        page_title = html.unescape(page_title)
                        logger.info(f"頁面標題: {page_title}")
                    
                    # 檢查 meta refresh
                    meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
                    if meta_refresh:
                        content = meta_refresh.get('content', '')
                        url_match = re.search(r'url=(.+)', content, re.IGNORECASE)
                        if url_match:
                            redirect_url = url_match.group(1).strip('\'"')
                            if not redirect_url.startswith('http'):
                                redirect_url = urllib.parse.urljoin(current_url, redirect_url)
                            
                            current_url = redirect_url
                            redirect_chain.append(current_url)
                            logger.info(f"通過 meta refresh 重定向到: {current_url}")
                            continue
                    
                    # 檢查隱藏的 input 元素
                    target_input = soup.find('input', {'id': 'target'}) or soup.find('input', {'name': 'target'})
                    if target_input and target_input.get('value'):
                        target_url = target_input.get('value')
                        target_url = html.unescape(target_url)
                        expanded_url = target_url
                        current_url = target_url
                        redirect_chain.append(current_url)
                        logger.info(f"通過隱藏元素重定向到: {current_url}")
                        continue
                    
                    # 檢查 JavaScript 重定向
                    scripts = soup.find_all('script')
                    for script in scripts:
                        if script.string:
                            script_content = script.string
                            url_patterns = [
                                r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                                r'window\.location\s*=\s*["\']([^"\']+)["\']',
                                r'location\.href\s*=\s*["\']([^"\']+)["\']',
                                r'location\s*=\s*["\']([^"\']+)["\']'
                            ]
                            
                            for pattern in url_patterns:
                                match = re.search(pattern, script_content)
                                if match:
                                    redirect_url = match.group(1)
                                    if not redirect_url.startswith('http'):
                                        redirect_url = urllib.parse.urljoin(current_url, redirect_url)
                                    
                                    current_url = redirect_url
                                    redirect_chain.append(current_url)
                                    logger.info(f"通過 JavaScript 重定向到: {current_url}")
                                    break
                            else:
                                continue
                            break
                
                # 如果沒有更多重定向，獲取最終頁面標題
                if response.status_code == 200:
                    content = response.text
                    
                    # 檢測並修復編碼問題
                    if any(char in content for char in ['â', 'ã', 'Ã', 'å']):
                        try:
                            content = response.content.decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                content = response.content.decode('big5')
                            except UnicodeDecodeError:
                                try:
                                    content = response.content.decode('gb2312')
                                except UnicodeDecodeError:
                                    content = response.content.decode('utf-8', errors='ignore')
                    
                    soup = BeautifulSoup(content[:1024], 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        page_title = title_tag.get_text().strip()
                        page_title = html.unescape(page_title)
                        logger.info(f"最終頁面標題: {page_title}")
                
                break  # 沒有更多重定向
                
            except Exception as e:
                logger.warning(f"請求失敗: {e}")
                break
        
        # 返回最終URL和重定向鏈
        final_url = redirect_chain[-1]
        is_short_url = len(redirect_chain) > 1
        was_expanded = final_url != url
        
        return url, final_url, is_short_url, was_expanded, page_title, redirect_chain
        
    except Exception as e:
        logger.error(f"展開短網址時發生錯誤: {e}")
        return url, url, False, False, None, [url]

def test_improved_expansion():
    """測試改進的短網址展開功能"""
    
    print("=" * 70)
    print("改進的短網址展開功能測試")
    print("=" * 70)
    
    test_url = "https://cht.tw/x/7h92p"
    print(f"測試網址: {test_url}")
    print()
    
    original_url, final_url, is_short_url, was_expanded, page_title, redirect_chain = expand_short_url_with_full_redirect(test_url)
    
    print("測試結果:")
    print(f"原始網址: {original_url}")
    print(f"最終網址: {final_url}")
    print(f"是否為短網址: {is_short_url}")
    print(f"是否成功展開: {was_expanded}")
    print(f"頁面標題: {page_title}")
    print()
    
    print("完整重定向鏈:")
    for i, redirect_url in enumerate(redirect_chain):
        print(f"  {i+1}. {redirect_url}")
    print()
    
    # 分析最終URL
    parsed_url = urllib.parse.urlparse(final_url)
    print(f"最終URL分析:")
    print(f"  協議: {parsed_url.scheme}")
    print(f"  域名: {parsed_url.netloc}")
    print(f"  路徑: {parsed_url.path}")
    print(f"  查詢參數: {parsed_url.query}")
    
    # 檢查是否為中華電信官方域名
    if 'cht' in parsed_url.netloc.lower():
        print("  ✅ 確認為中華電信官方域名")
    else:
        print("  ⚠️ 注意：不是中華電信官方域名")
    
    print()
    
    if was_expanded and 'cht' in final_url:
        print("✅ 改進的短網址展開功能正常")
        print("✅ 成功追蹤完整重定向鏈")
        print("✅ 最終目的地確認為官方網站")
    elif was_expanded:
        print("✅ 短網址展開功能正常")
        print("⚠️ 最終目的地需要進一步驗證")
    else:
        print("❌ 短網址展開功能異常")
    
    return was_expanded

if __name__ == "__main__":
    test_improved_expansion() 