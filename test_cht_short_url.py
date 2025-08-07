#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
import html
from urllib.parse import urlparse
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_expand_short_url(url):
    """測試短網址展開功能"""
    print(f"測試短網址: {url}")
    
    parsed_url = urlparse(url)
    print(f"解析的域名: {parsed_url.netloc}")
    
    # 檢查是否為短網址
    short_url_domains = [
        'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly', 
        'is.gd', 'buff.ly', 'adf.ly', 'short.link', 'tiny.cc',
        'reurl.cc', 'pse.is', 'lihi.io', 'lin.ee', 'cht.tw', 'chts.tw'
    ]
    
    is_short_url = False
    for domain in short_url_domains:
        if domain in parsed_url.netloc:
            is_short_url = True
            print(f"確認為短網址，匹配域名: {domain}")
            break
    
    if not is_short_url:
        print("不是短網址")
        return
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        expanded_url = None
        page_title = None
        
        print("步驟1: 嘗試 HEAD 請求...")
        # 先嘗試 HEAD 請求
        try:
            response = session.head(url, allow_redirects=True, timeout=10, verify=False)
            expanded_url = response.url
            print(f"HEAD 請求結果: {expanded_url}")
        except Exception as e:
            print(f"HEAD 請求失敗: {e}")
        
        # 如果 HEAD 請求沒有重定向，嘗試 GET 請求並檢查內容
        if not expanded_url or expanded_url == url:
            print("步驟2: 嘗試 GET 請求...")
            try:
                response = session.get(url, allow_redirects=True, timeout=10, verify=False)
                expanded_url = response.url
                print(f"GET 請求結果: {expanded_url}")
                print(f"狀態碼: {response.status_code}")
                
                # 如果還是沒有重定向，檢查是否有 JavaScript 重定向或 meta refresh
                if expanded_url == url and response.status_code == 200:
                    print("步驟3: 分析頁面內容...")
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 獲取頁面標題
                    title_tag = soup.find('title')
                    if title_tag:
                        page_title = title_tag.get_text().strip()
                        # 解碼HTML實體
                        page_title = html.unescape(page_title)
                        print(f"頁面標題: {page_title}")
                    
                    # 檢查 meta refresh
                    meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
                    if meta_refresh:
                        content = meta_refresh.get('content', '')
                        print(f"找到 meta refresh: {content}")
                        url_match = re.search(r'url=(.+)', content, re.IGNORECASE)
                        if url_match:
                            expanded_url = url_match.group(1).strip('\'"')
                            print(f"通過 meta refresh 展開短網址: {url} -> {expanded_url}")
                            return url, expanded_url, True, True, page_title
                    
                    # 檢查隱藏的 input 元素
                    target_input = soup.find('input', {'id': 'target'}) or soup.find('input', {'name': 'target'})
                    if target_input and target_input.get('value'):
                        target_url = target_input.get('value')
                        # 解碼 HTML 實體
                        target_url = html.unescape(target_url)
                        expanded_url = target_url
                        print(f"通過隱藏元素展開短網址: {url} -> {expanded_url}")
                        return url, expanded_url, True, True, page_title
                    
                    # 檢查 JavaScript 重定向
                    scripts = soup.find_all('script')
                    print(f"找到 {len(scripts)} 個 script 標籤")
                    for i, script in enumerate(scripts):
                        if script.string:
                            script_content = script.string
                            print(f"分析 script {i+1}: {script_content[:200]}...")
                            url_patterns = [
                                r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                                r'window\.location\s*=\s*["\']([^"\']+)["\']',
                                r'location\.href\s*=\s*["\']([^"\']+)["\']',
                                r'location\s*=\s*["\']([^"\']+)["\']'
                            ]
                            
                            for pattern in url_patterns:
                                match = re.search(pattern, script_content)
                                if match:
                                    js_url = match.group(1)
                                    expanded_url = js_url
                                    print(f"通過 JavaScript 展開短網址: {url} -> {expanded_url}")
                                    return url, expanded_url, True, True, page_title
                    
                    # 檢查是否有其他重定向線索
                    print("檢查頁面內容中的重定向線索...")
                    print(f"頁面內容前500字符: {response.text[:500]}")
                    
            except requests.exceptions.SSLError as e:
                print(f"SSL 錯誤: {e}")
            except Exception as e:
                print(f"GET 請求失敗: {e}")
        
        # 如果成功展開，獲取目標頁面的標題
        if expanded_url and expanded_url != url:
            print(f"成功展開短網址: {url} -> {expanded_url}")
            try:
                title_response = session.get(expanded_url, timeout=5)
                if title_response.status_code == 200:
                    content = title_response.text
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
                    if title_match:
                        page_title = title_match.group(1).strip()
                        page_title = html.unescape(page_title)
                        print(f"目標頁面標題: {page_title}")
                title_response.close()
            except Exception as e:
                print(f"獲取目標頁面標題失敗: {e}")
            
            return url, expanded_url, True, True, page_title
        else:
            print(f"短網址無法展開或已失效: {url}")
            return url, url, True, False, page_title
            
    except requests.exceptions.Timeout:
        print(f"展開短網址超時: {url}")
        return url, url, True, False, None
    except requests.exceptions.ConnectionError:
        print(f"展開短網址連接失敗: {url}")
        return url, url, True, False, None
    except Exception as e:
        print(f"展開短網址時出錯: {e}")
        return url, url, True, False, None

if __name__ == "__main__":
    # 測試原始短網址
    test_url = "https://cht.tw/x/7h92p"
    print("=== 測試原始短網址 ===")
    result1 = test_expand_short_url(test_url)
    print(f"原始短網址結果: {result1}")
    
    # 測試展開後的網址
    if result1 and result1[1] != test_url:
        print("\n=== 測試展開後的網址 ===")
        expanded_url = result1[1]
        result2 = test_expand_short_url(expanded_url)
        print(f"展開後網址結果: {result2}") 