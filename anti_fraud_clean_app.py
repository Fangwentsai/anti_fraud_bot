# -*- coding: utf-8 -*-
import os
import json
import logging
import random
import re
import requests
from urllib.parse import urlparse
from datetime import datetime, timedelta
import openai
from openai import OpenAI
from flask import Flask, request, abort, render_template, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage,
    PostbackEvent, QuickReply, QuickReplyButton, MessageAction,
    BubbleContainer, BoxComponent, TextComponent, SeparatorComponent,
    ButtonComponent, URIAction, PostbackAction, ImageMessage
)
from linebot.v3 import WebhookHandler as V3WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.webhooks import MessageEvent as V3MessageEvent
from linebot.v3.messaging import TextMessage as V3TextMessage
from firebase_manager import FirebaseManager
from domain_spoofing_detector import detect_domain_spoofing
from dotenv import load_dotenv
import time
import threading

# 導入新的模組化組件
from config import *
from fraud_knowledge import load_fraud_tactics, get_anti_fraud_tips, get_fraud_features, analyze_fraud_keywords
from weather_service import handle_weather_query, is_weather_related, handle_weather_query_data
from flex_message_service import (
    create_analysis_flex_message, create_domain_spoofing_flex_message,
    create_donation_flex_message, create_weather_flex_message,
    create_fraud_types_flex_message, create_fraud_detail_flex_message,
    FlexMessageService
)
from game_service import (
    start_potato_game, handle_potato_game_answer, is_game_trigger, get_user_game_state
)

# 添加圖片分析功能
import image_handler
from image_analysis_service import ANALYSIS_TYPES

# 首先在頂部添加導入城市選擇器
from city_selector import get_city_selector

# 指定 .env 文件的路徑
current_dir_env = os.path.join(os.path.dirname(__file__), '.env')
parent_dir_env = os.path.join(os.path.dirname(__file__), '..', 'linebot-anti-fraud', '.env')

# 嘗試載入.env文件
if os.path.exists(current_dir_env):
    load_dotenv(dotenv_path=current_dir_env)
    print(f"載入環境變數從: {current_dir_env}")
elif os.path.exists(parent_dir_env):
    load_dotenv(dotenv_path=parent_dir_env)
    print(f"載入環境變數從: {parent_dir_env}")
else:
    load_dotenv()
    print("嘗試載入預設的.env文件")

# 從JSON文件載入安全網域列表
def load_safe_domains():
    """從safe_domains.json文件載入安全網域列表"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        safe_domains_path = os.path.join(script_dir, 'safe_domains.json')
        
        with open(safe_domains_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            flattened_safe_domains = {}
            for category, domains in data['safe_domains'].items():
                if isinstance(domains, dict):
                    flattened_safe_domains.update(domains)
                else:
                    logger.warning(f"類別 '{category}' 的格式不正確: {type(domains)}")
            
            return flattened_safe_domains, data['donation_domains']
    except FileNotFoundError:
        print("找不到safe_domains.json文件，使用預設的安全網域列表")
        default_safe_domains = {
            "google.com": "Google 搜尋引擎",
            "facebook.com": "Facebook 社群網站",
            "youtube.com": "YouTube 影音平台",
            "gov.tw": "中華民國政府網站",
            "165.npa.gov.tw": "165反詐騙諮詢專線"
        }
        default_donation_domains = []
        return default_safe_domains, default_donation_domains
    except Exception as e:
        print(f"載入safe_domains.json時發生錯誤: {e}")
        default_safe_domains = {
            "google.com": "Google 搜尋引擎",
            "facebook.com": "Facebook 社群網站",
            "youtube.com": "YouTube 影音平台",
            "gov.tw": "中華民國政府網站",
            "165.npa.gov.tw": "165反詐騙諮詢專線"
        }
        default_donation_domains = []
        return default_safe_domains, default_donation_domains

# 用戶狀態管理
def get_user_state(user_id):
    """獲取用戶狀態"""
    if user_id not in user_conversation_state:
        user_conversation_state[user_id] = {"last_time": datetime.now()}
    return user_conversation_state[user_id]

def update_user_state(user_id, state):
    """更新用戶狀態"""
    user_conversation_state[user_id] = state

# 設置日誌
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# 檢查重要的環境變數
logger.info(f"CWB_API_KEY 狀態: {'已設定' if os.environ.get('CWB_API_KEY') else '未設定'}")
logger.info(f"LINE_CHANNEL_ACCESS_TOKEN 狀態: {'已設定' if os.environ.get('LINE_CHANNEL_ACCESS_TOKEN') else '未設定'}")
logger.info(f"OPENAI_API_KEY 狀態: {'已設定' if os.environ.get('OPENAI_API_KEY') else '未設定'}")

# 載入安全網域和贊助網域
SAFE_DOMAINS, DONATION_DOMAINS = load_safe_domains()
logger.info(f"成功載入 {len(SAFE_DOMAINS)} 個安全網域和 {len(DONATION_DOMAINS)} 個贊助網域")

app = Flask(__name__)

# Line API 設定
if LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    
    v3_configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    v3_api_client = ApiClient(v3_configuration)
    v3_messaging_api = MessagingApi(v3_api_client)
    
    image_handler.init_image_handler(line_bot_api)
    logger.info("LINE Bot API 初始化成功")
else:
    line_bot_api = None
    handler = None
    v3_messaging_api = None
    logger.info("LINE Bot API 初始化失敗：缺少必要的環境變數")

# OpenAI設定
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=30.0,
            max_retries=3
        )
        logger.info("OpenAI API 初始化成功")
    except Exception as e:
        logger.error(f"OpenAI API 初始化失敗: {e}")
        openai_client = None
else:
    openai_client = None
    logger.warning("OpenAI API 初始化失敗：缺少 API 金鑰")

# 初始化Firebase管理器
firebase_manager = FirebaseManager.get_instance()

# 用戶狀態變數
user_game_state = {}
user_last_chat_time = {}
user_pending_analysis = {}
first_time_chatters = set()
user_conversation_state = {}

# 服務監控變數
import psutil
app_start_time = datetime.now()
process = psutil.Process()

# 內建 Keep-Alive 機制
def internal_keep_alive():
    """內建的 keep-alive 機制，定期自我 ping"""
    while True:
        try:
            time.sleep(5 * 60)  # 每5分鐘 ping 一次
            
            # 簡單的內部健康檢查，不需要發送 HTTP 請求
            current_time = datetime.now()
            logger.info(f"[Internal Keep-Alive] Service is alive at {current_time}")
            
            # 清理過期的用戶狀態（可選的內存清理）
            cleanup_expired_states()
            
        except Exception as e:
            logger.error(f"Internal keep-alive error: {e}")

def cleanup_expired_states():
    """清理過期的用戶狀態"""
    try:
        current_time = datetime.now()
        expired_users = []
        
        for user_id, state in user_conversation_state.items():
            last_time = state.get("last_time")
            if last_time and (current_time - last_time).total_seconds() > 3600:  # 1小時後清理
                expired_users.append(user_id)
        
        for user_id in expired_users:
            user_conversation_state.pop(user_id, None)
            user_game_state.pop(user_id, None)
            user_last_chat_time.pop(user_id, None)
            user_pending_analysis.pop(user_id, None)
            
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired user states")
            
    except Exception as e:
        logger.error(f"Error cleaning up expired states: {e}")

# 啟動內建 Keep-Alive 服務
def start_internal_keep_alive():
    """啟動內建的 keep-alive 服務"""
    keep_alive_thread = threading.Thread(target=internal_keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("🔄 內建 Keep-Alive 服務已啟動")

# 在應用啟動時啟動 keep-alive
start_internal_keep_alive()

# 載入醫美服務和健康知識的白名單
def load_beauty_health_whitelist():
    """從beauty_health_whitelist.json文件載入醫美和健康相關的白名單關鍵詞"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        whitelist_path = os.path.join(script_dir, 'beauty_health_whitelist.json')
        
        with open(whitelist_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 將所有類別的關鍵詞合併為一個扁平列表
            flattened_whitelist = []
            for category, keywords in data['categories'].items():
                flattened_whitelist.extend(keywords)
            
            logger.info(f"成功載入 {len(flattened_whitelist)} 個醫美和健康相關關鍵詞")
            return flattened_whitelist
    except FileNotFoundError:
        logger.warning("找不到beauty_health_whitelist.json文件，使用預設的白名單列表")
        default_whitelist = [
            "皮秒雷射", "微針", "膠原蛋白", "玻尿酸", "肉毒桿菌", "減肥", "美白",
            "保濕", "瘦身", "膠原蛋白飲", "中醫美容", "雷射", "電波拉皮"
        ]
        return default_whitelist
    except Exception as e:
        logger.error(f"載入beauty_health_whitelist.json時發生錯誤: {e}")
        return []

# 載入醫美和健康相關白名單
BEAUTY_HEALTH_WHITELIST = load_beauty_health_whitelist()

# 為了向下兼容，保留舊的變數名稱
function_inquiry_keywords = FUNCTION_INQUIRY_KEYWORDS
follow_up_patterns = FOLLOW_UP_PATTERNS
fraud_prevention_game_trigger_keywords = FRAUD_PREVENTION_GAME_TRIGGER_KEYWORDS
bot_trigger_keyword = BOT_TRIGGER_KEYWORD
analysis_prompts = ANALYSIS_PROMPTS

def expand_short_url(url):
    """嘗試展開短網址，返回原始URL、展開後的URL和網頁標題"""
    parsed_url = urlparse(url)
    is_short_url = False
    for domain in SHORT_URL_DOMAINS:
        if domain in parsed_url.netloc:
            is_short_url = True
            break
    
    if not is_short_url:
        return url, url, False, False, None
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        expanded_url = None
        page_title = None
        
        # 先嘗試 HEAD 請求
        try:
            response = session.head(url, allow_redirects=True, timeout=10, verify=False)
            expanded_url = response.url
        except Exception:
            pass
        
        # 如果 HEAD 請求沒有重定向，嘗試 GET 請求並檢查內容
        if not expanded_url or expanded_url == url:
            try:
                response = session.get(url, allow_redirects=True, timeout=10, verify=False)
                expanded_url = response.url
                
                # 如果還是沒有重定向，檢查是否有 JavaScript 重定向或 meta refresh
                if expanded_url == url and response.status_code == 200:
                    from bs4 import BeautifulSoup
                    import re
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 獲取頁面標題
                    title_tag = soup.find('title')
                    if title_tag:
                        page_title = title_tag.get_text().strip()
                        # 解碼HTML實體
                        import html
                        page_title = html.unescape(page_title)
                    
                    # 檢查 meta refresh
                    meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
                    if meta_refresh:
                        content = meta_refresh.get('content', '')
                        url_match = re.search(r'url=(.+)', content, re.IGNORECASE)
                        if url_match:
                            expanded_url = url_match.group(1).strip('\'"')
                            logger.info(f"通過 meta refresh 展開短網址: {url} -> {expanded_url}")
                            return url, expanded_url, True, True, page_title
                    
                    # 檢查隱藏的 input 元素（如 reurl.cc 的做法）
                    target_input = soup.find('input', {'id': 'target'}) or soup.find('input', {'name': 'target'})
                    if target_input and target_input.get('value'):
                        target_url = target_input.get('value')
                        # 解碼 HTML 實體
                        import html
                        target_url = html.unescape(target_url)
                        expanded_url = target_url
                        logger.info(f"通過隱藏元素展開短網址: {url} -> {expanded_url}")
                        return url, expanded_url, True, True, page_title
                    
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
                                    js_url = match.group(1)
                                    expanded_url = js_url
                                    logger.info(f"通過 JavaScript 展開短網址: {url} -> {expanded_url}")
                                    return url, expanded_url, True, True, page_title
                
            except requests.exceptions.SSLError as e:
                logger.warning(f"SSL 錯誤，嘗試不驗證證書: {e}")
                # 對於 SSL 錯誤，嘗試不驗證證書
                try:
                    response = session.get(url, allow_redirects=True, timeout=10, verify=False)
                    expanded_url = response.url
                    
                    # 如果還是沒有重定向，檢查是否有 JavaScript 重定向或 meta refresh
                    if expanded_url == url and response.status_code == 200:
                        from bs4 import BeautifulSoup
                        import re
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 獲取頁面標題
                        title_tag = soup.find('title')
                        if title_tag:
                            page_title = title_tag.get_text().strip()
                            # 解碼HTML實體
                            import html
                            page_title = html.unescape(page_title)
                        
                        # 檢查隱藏的 input 元素（如 reurl.cc 的做法）
                        target_input = soup.find('input', {'id': 'target'}) or soup.find('input', {'name': 'target'})
                        if target_input and target_input.get('value'):
                            target_url = target_input.get('value')
                            # 解碼 HTML 實體
                            import html
                            target_url = html.unescape(target_url)
                            expanded_url = target_url
                            logger.info(f"通過隱藏元素展開短網址: {url} -> {expanded_url}")
                            return url, expanded_url, True, True, page_title
                except Exception as e2:
                    logger.warning(f"重試後仍然失敗: {e2}")
            except Exception as e:
                logger.warning(f"GET 請求失敗: {e}")
        
        # 如果成功展開，獲取目標頁面的標題
        if expanded_url and expanded_url != url:
            try:
                title_response = session.get(expanded_url, timeout=5)
                if title_response.status_code == 200:
                    # 使用與 get_website_title 相同的編碼處理邏輯
                    content = title_response.text
                    
                    # 檢測並修復編碼問題
                    if any(char in content for char in ['â', 'ã', 'Ã', 'å']):
                        try:
                            content = title_response.content.decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                content = title_response.content.decode('big5')
                            except UnicodeDecodeError:
                                try:
                                    content = title_response.content.decode('gb2312')
                                except UnicodeDecodeError:
                                    content = title_response.content.decode('utf-8', errors='ignore')
                    
                    # 只讀取前 1KB 來獲取標題
                    content = content[:1024]
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
                    if title_match:
                        page_title = title_match.group(1).strip()
                        # 解碼HTML實體
                        import html
                        page_title = html.unescape(page_title)
                title_response.close()
            except Exception:
                pass  # 獲取標題失敗不影響主要功能
            
            logger.info(f"成功展開短網址: {url} -> {expanded_url}")
            return url, expanded_url, True, True, page_title
        else:
            logger.warning(f"短網址無法展開或已失效: {url}")
            return url, url, True, False, page_title
            
    except requests.exceptions.Timeout:
        logger.warning(f"展開短網址超時: {url}")
        return url, url, True, False, None
    except requests.exceptions.ConnectionError:
        logger.warning(f"展開短網址連接失敗: {url}")
        return url, url, True, False, None
    except Exception as e:
        logger.error(f"展開短網址時出錯: {e}")
        return url, url, True, False, None

# 載入詐騙話術資料
anti_fraud_tips = []
fraud_types = load_fraud_tactics()
fraud_tactics = load_fraud_tactics()
logger.info(f"成功載入詐騙類型：{', '.join(fraud_tactics.keys())}")

def create_suspicious_ad_warning_message(display_name, ad_description="兼職計劃旅程"):
    """創建可疑廣告警告訊息"""
    warning_message = f"@{display_name} 聽起來這個廣告有點讓人疑惑，尤其是牽涉到「{ad_description}」這類說法時，我們要特別小心。這類廣告常見於詐騙手法裡，可能會利用「兼職」或「免費旅遊」的誘因，誘使你留下個人資料，甚至進一步要求匯款或購買昂貴課程。\n\n建議你可以先做以下幾件事：\n\n"
    
    warning_message += "🚫 不要急著留下信箱或任何個人資料，先觀察和詢問更多細節。\n"
    warning_message += "🔍 查詢這個廣告的來源，例如公司名稱或負責人資料，看看是否有正當的背景。\n"
    warning_message += "🌐 搜尋網路評價或負評，看看其他人有沒有遭遇過類似的詐騙。\n"
    warning_message += "🛡️ 如果覺得不安全，直接忽略或封鎖廣告，避免被騙。\n\n"
    
    warning_message += "如果方便的話，可以把廣告內容或截圖分享給我，我可以幫你分析得更詳細喔！你的安全最重要，我會一直陪著你。😊"
    
    return warning_message

# 獲取用戶個人資料
def get_user_profile(user_id):
    try:
        profile = line_bot_api.get_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"獲取用戶 {user_id} 個人資料失敗: {e}")
        return None

# 解析OpenAI返回的詐騙分析結果
def parse_fraud_analysis(analysis_result):
    """解析OpenAI返回的詐騙分析結果"""
    try:
        # 先檢查是否包含 "[]" 並清理
        analysis_result = str(analysis_result).replace("[]", "").strip()
        
        lines = analysis_result.strip().split('\n')
        result = {
            "risk_level": "中風險",
            "fraud_type": "需要進一步分析",
            "explanation": "無法解析分析結果。",
            "suggestions": "建議謹慎處理。",
            "is_emerging": False
        }
        
        # 先嘗試解析結構化格式
        for line in lines:
            line = line.strip()
            if line.startswith("風險等級：") or line.startswith("風險等級:"):
                risk_level = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                # 清理可能的陣列格式
                risk_level = risk_level.replace("[]", "").replace("[", "").replace("]", "").strip()
                if risk_level:
                    result["risk_level"] = risk_level
            elif line.startswith("詐騙類型：") or line.startswith("詐騙類型:"):
                fraud_type = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                # 清理可能的陣列格式
                fraud_type = fraud_type.replace("[]", "").replace("[", "").replace("]", "").strip()
                # 避免使用"未知"作為詐騙類型
                if fraud_type and fraud_type not in ["未知", "不明", "無法確定"]:
                    result["fraud_type"] = fraud_type
            elif line.startswith("分析說明：") or line.startswith("分析說明:"):
                explanation = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                # 清理可能的陣列格式
                explanation = explanation.replace("[]", "").replace("[", "").replace("]", "").strip()
                if explanation:
                    result["explanation"] = explanation
            elif line.startswith("土豆建議：") or line.startswith("土豆建議:"):
                suggestions = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                # 清理可能的陣列格式和引號
                suggestions = suggestions.replace("[]", "").replace("[", "").replace("]", "").strip()
                suggestions = suggestions.replace('"', '').replace("'", "").strip()
                if suggestions:
                    result["suggestions"] = suggestions
            elif line.startswith("新興手法：") or line.startswith("新興手法:"):
                emerging_text = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                result["is_emerging"] = emerging_text in ["是", "Yes", "true", "True"]
        
        # 如果沒有解析到說明，嘗試從整個回應中提取
        if not result["explanation"] or result["explanation"] == "無法解析分析結果。":
            # 移除格式標籤，取得純文字內容
            clean_text = analysis_result
            for prefix in ["風險等級：", "風險等級:", "詐騙類型：", "詐騙類型:", "說明：", "說明:", "建議：", "建議:", "新興手法：", "新興手法:"]:
                clean_text = clean_text.replace(prefix, "")
            
            # 清理可能的陣列格式
            clean_text = clean_text.replace("[]", "").replace("[", "").replace("]", "").strip()
            
            # 分割成行並過濾空行
            clean_lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
            
            # 如果有內容，使用第一行作為說明
            if clean_lines:
                result["explanation"] = clean_lines[0]
            
            # 如果還是沒有有效說明，使用整個回應
            if not result["explanation"] or len(result["explanation"]) < 10:
                result["explanation"] = analysis_result.strip()
        
        # 最終檢查：確保所有文字欄位都不包含 "[]" 並限制字數
        for key in ["risk_level", "fraud_type", "explanation", "suggestions"]:
            if result[key]:
                result[key] = str(result[key]).replace("[]", "").replace("[", "").replace("]", "").strip()
                # 如果清理後變成空字串，提供預設值
                if not result[key]:
                    if key == "risk_level":
                        result[key] = "中風險"
                    elif key == "fraud_type":
                        result[key] = "需要進一步分析"
                    elif key == "explanation":
                        result[key] = "無法獲取詳細分析。"
                    elif key == "suggestions":
                        result[key] = "建議謹慎處理。"
                
                # 特殊處理：限制分析說明字數並優化土豆建議
                if key == "explanation" and len(result[key]) > 40:
                    # 截斷到40字以內
                    result[key] = result[key][:40].rstrip("，。、")
                    if not result[key].endswith("。"):
                        result[key] += "。"
                
                elif key == "suggestions":
                    # 根據風險等級優化土豆建議
                    risk_level = result.get("risk_level", "中風險")
                    if risk_level in ["高風險", "極高風險"]:
                        if len(result[key]) < 10 or "謹慎" in result[key]:
                            result[key] = "立即停止操作，直接聯繫官方客服確認！📞🔒"
                    elif risk_level in ["低風險", "極低風險"]:
                        if len(result[key]) < 10:
                            result[key] = "放心啦，這只是正常的通知而已😊"
                    else:  # 中風險
                        if len(result[key]) < 10:
                            result[key] = "建議先暫停操作，確認來源後再決定！⚠️"
        
        # 智能推斷詐騙類型（如果仍然是預設值）
        if result["fraud_type"] == "需要進一步分析":
            content_lower = analysis_result.lower()
            
            # 根據關鍵詞推斷詐騙類型
            if any(keyword in content_lower for keyword in ["投資", "理財", "股票", "基金", "獲利", "報酬", "收益"]):
                result["fraud_type"] = "投資詐騙"
            elif any(keyword in content_lower for keyword in ["購物", "商品", "產品", "減肥", "美容", "療效"]):
                result["fraud_type"] = "購物詐騙/虛假廣告"
            elif any(keyword in content_lower for keyword in ["交友", "約會", "感情", "戀愛", "單身"]):
                result["fraud_type"] = "假交友詐騙"
            elif any(keyword in content_lower for keyword in ["中獎", "獎金", "抽獎", "幸運"]):
                result["fraud_type"] = "中獎詐騙"
            elif any(keyword in content_lower for keyword in ["工作", "兼職", "招聘", "求職", "面試"]):
                result["fraud_type"] = "求職詐騙"
            elif any(keyword in content_lower for keyword in ["網址", "連結", "點擊", "登入", "密碼"]):
                result["fraud_type"] = "釣魚網站"
            elif any(keyword in content_lower for keyword in ["冒充", "假冒", "身分", "政府", "銀行"]):
                result["fraud_type"] = "假冒身分詐騙"
            elif "風險" in content_lower and any(level in content_lower for level in ["低", "無"]):
                result["fraud_type"] = "非詐騙相關"
            else:
                result["fraud_type"] = "可疑訊息"
        
        # 確保風險等級有效
        valid_risk_levels = ["極低風險", "低風險", "中風險", "高風險", "極高風險", "無風險"]
        if result["risk_level"] not in valid_risk_levels:
            # 嘗試從文字中推斷風險等級
            content_lower = analysis_result.lower()
            if any(keyword in content_lower for keyword in ["極高", "非常高", "很高"]):
                result["risk_level"] = "極高風險"
            elif any(keyword in content_lower for keyword in ["高風險", "高"]):
                result["risk_level"] = "高風險"
            elif any(keyword in content_lower for keyword in ["低風險", "低", "安全"]):
                result["risk_level"] = "低風險"
            elif any(keyword in content_lower for keyword in ["極低", "非常低", "無風險"]):
                result["risk_level"] = "極低風險"
            else:
                result["risk_level"] = "中風險"
        
        return result
        
    except Exception as e:
        logger.error(f"解析詐騙分析結果時發生錯誤: {e}")
        return {
            "risk_level": "中風險",
            "fraud_type": "解析錯誤",
            "explanation": "分析結果解析失敗，建議人工檢查。",
            "suggestions": "🔍 請仔細檢查內容\n🛡️ 如有疑慮請諮詢專家",
            "is_emerging": False
        }

def _is_legitimate_subdomain(subdomain_part):
    """檢查子網域部分是否合法"""
    if not subdomain_part or len(subdomain_part) > 20:
        return False
    
    legitimate_prefixes = [
        'www', 'mail', 'email', 'webmail', 'smtp', 'pop', 'imap',
        'ftp', 'sftp', 'api', 'app', 'mobile', 'm', 'wap',
        'admin', 'secure', 'ssl', 'login', 'auth', 'account',
        'shop', 'store', 'buy', 'order', 'cart', 'checkout',
        'news', 'blog', 'forum', 'support', 'help', 'service',
        'event', 'events', 'promo', 'promotion', 'campaign',
        'member', 'members', 'user', 'users', 'profile',
        'search', 'find', 'discover', 'explore',
        'download', 'upload', 'file', 'files', 'doc', 'docs',
        'img', 'image', 'images', 'pic', 'pics', 'photo', 'photos',
        'video', 'videos', 'media', 'cdn', 'static', 'assets',
        'dev', 'test', 'staging', 'beta', 'alpha', 'demo',
        'tw', 'taiwan', 'hk', 'hongkong', 'cn', 'china',
        'en', 'english', 'zh', 'chinese',
        'playing', 'play', 'game', 'games', 'entertainment', 'fun',
        'amp', 'article', 'articles', 'read', 'view', 'content'
    ]
    
    if subdomain_part.lower() in legitimate_prefixes:
        return True
    
    suspicious_patterns = [
        '-tw-', '-official-', '-secure-', '-login-', '-bank-',
        'phishing', 'fake', 'scam', 'fraud', 'malware'
    ]
    
    for pattern in suspicious_patterns:
        if pattern in subdomain_part.lower():
            return False
    
    import re
    if not re.match(r'^[a-zA-Z0-9-]+$', subdomain_part):
        return False
    
    if subdomain_part.startswith('-') or subdomain_part.endswith('-'):
        return False
    
    return True

def detect_fraud_with_chatgpt(user_message, display_name="朋友", user_id=None):
    """使用OpenAI的API檢測詐騙信息"""
    import re
    from urllib.parse import urlparse
    
    try:
        # 優先檢查是否為信用卡3D驗證簡訊
        if is_credit_card_3d_verification(user_message):
            logger.info(f"檢測到信用卡3D驗證簡訊，進行專門分析")
            return analyze_credit_card_3d_verification(user_message, display_name)
        
        # 檢查是否為郵件內容 - 更寬鬆的檢測條件
        email_pattern = r'(?:寄件者|發信者|From|from)[:：]\s*([^\n\r]+@[^\n\r\s]+)'
        email_match = re.search(email_pattern, user_message)
        
        # 檢查強郵件特徵關鍵詞（更嚴格的判斷）
        strong_email_indicators = ['寄件者', '發信者', '主旨', '收件者', 'From:', 'To:', 'Subject:', '郵件', 'email', '發送時間', '收信時間', '回覆', '轉寄', '附件', '信箱']
        has_strong_email_indicators = any(indicator in user_message for indicator in strong_email_indicators)
        
        # 檢查是否為 LINE 聊天內容（排除條件）
        line_chat_indicators = [
            '< ', '> ', 'https://www.youtube.com', 'https://youtu.be', 'https://line.me', 'https://lin.ee',
            '哈囉', '你好', '我要查價', '感謝您的訊息', '感謝您加入好友', '敬請期待', 
            '此官方帳號將定期發放最新資訊給您', '很抱歉，本帳號無法個別回覆用戶的訊息',
            '整新機查詢', 'Apple整新機', '感謝您加入好友', '已讀', '正在自動回覆訊息'
        ]
        has_line_chat_indicators = any(indicator in user_message for indicator in line_chat_indicators)
        
        # 檢查是否包含郵件地址格式
        email_address_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        has_email_address = re.search(email_address_pattern, user_message)
        
        # 檢查是否包含典型的郵件服務格式（如您的案例）
        service_patterns = [
            r'[A-Z]+\.[A-Z]+-服務[A-Z]+\.[A-Z]+',  # RTK.UI-服務FETC.Service
            r'[A-Z]+-[^<]+<[^>]+@[^>]+>',  # YTA-未於期限理 <casinto@telenet.be>
        ]
        has_service_pattern = any(re.search(pattern, user_message) for pattern in service_patterns)
        
        # 檢查是否為正常的服務查詢或客服對話（排除條件）
        service_query_indicators = [
            '查詢', '詢問', '服務', '客服', '整新機', '二手', '官方帳號', '自動回覆',
            '定期發放', '最新資訊', '敬請期待', '無法個別回覆', '感謝加入'
        ]
        is_service_query = any(indicator in user_message for indicator in service_query_indicators)
        
        # 如果符合郵件特徵且不是 LINE 聊天內容且不是服務查詢，進行郵件分析
        if (email_match or has_strong_email_indicators or has_email_address or has_service_pattern) and not has_line_chat_indicators and not is_service_query:
            logger.info(f"檢測到郵件內容，進行專門分析")
            sender_email = None
            
            # 嘗試提取發信者郵件地址
            if email_match:
                sender_email = email_match.group(1)
            elif has_email_address:
                # 提取第一個找到的郵件地址
                email_addresses = re.findall(email_address_pattern, user_message)
                if email_addresses:
                    sender_email = email_addresses[0]
            
            return analyze_email_fraud(user_message, sender_email, display_name)
        
        original_url = None
        expanded_url = None
        is_short_url = False
        url_expanded_successfully = False
        page_title = None  # 初始化 page_title 變數
        
        url_pattern = re.compile(r'(https?://[^\s\u4e00-\u9fff，。！？；：]+|www\.[^\s\u4e00-\u9fff，。！？；：]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s\u4e00-\u9fff，。！？；：]*)?)')
        url_match = url_pattern.search(user_message)
        
        if url_match:
            original_url = url_match.group(0)
            original_url = re.sub(r'[，。！？；：]+$', '', original_url)
            
            if not original_url.startswith(('http://', 'https://')):
                original_url = 'https://' + original_url
            
            # 檢查是否為圖片URL
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
            image_domains = ['imgur.com', 'i.imgur.com', 'postimg.cc', 'imgbb.com', 'ibb.co', 'tinypic.com', 'photobucket.com', 'flickr.com', 'instagram.com', 'facebook.com']
            
            is_image_url = False
            parsed_url = urlparse(original_url)
            
            # 檢查副檔名
            if any(original_url.lower().endswith(ext) for ext in image_extensions):
                is_image_url = True
                logger.info(f"檢測到圖片副檔名: {original_url}")
            
            # 檢查圖片網站域名
            elif any(domain in parsed_url.netloc.lower() for domain in image_domains):
                is_image_url = True
                logger.info(f"檢測到圖片網站域名: {parsed_url.netloc}")
            
            # 如果是圖片URL，使用圖片分析功能
            if is_image_url:
                logger.info(f"開始分析圖片URL: {original_url}")
                try:
                    from image_handler import handle_image_url
                    
                    # 使用圖片分析功能
                    flex_message, raw_result = handle_image_url(
                        original_url, user_id or "unknown", display_name, 
                        context_message=f"用戶提供的圖片網址分析請求：{user_message}", 
                        analysis_type="GENERAL"
                    )
                    
                    if flex_message and raw_result:
                        # 解析圖片分析結果
                        try:
                            # 從raw_result中提取分析結果
                            import json
                            if isinstance(raw_result, str):
                                # 如果是字符串，嘗試解析為JSON
                                try:
                                    result_data = json.loads(raw_result)
                                except:
                                    # 如果不是JSON，創建基本結構
                                    result_data = {
                                        "risk_level": "中風險",
                                        "fraud_type": "圖片內容分析",
                                        "explanation": raw_result,
                                        "suggestions": "建議謹慎處理此圖片內容"
                                    }
                            else:
                                result_data = raw_result
                            
                            # 添加圖片URL相關信息
                            result_data["display_name"] = display_name
                            result_data["original_url"] = original_url
                            result_data["is_image_url"] = True
                            result_data["analysis_type"] = "圖片URL分析"
                            
                            return {
                                "success": True,
                                "message": "圖片分析完成",
                                "result": result_data,
                                "raw_result": raw_result,
                                "flex_message": flex_message
                            }
                        except Exception as parse_error:
                            logger.error(f"解析圖片分析結果時發生錯誤: {parse_error}")
                            return {
                                "success": True,
                                "message": "圖片分析完成",
                                "result": {
                                    "risk_level": "中風險",
                                    "fraud_type": "圖片URL分析",
                                    "explanation": f"✅ 已成功分析圖片內容。\n\n🔍 圖片網址：{original_url}\n\n📊 分析結果已通過圖片分析功能處理，請查看詳細的分析報告。",
                                    "suggestions": "🔍 請仔細查看圖片分析結果\n⚠️ 如果圖片內容涉及金錢交易，請特別謹慎\n🛡️ 不要輕易提供個人資料或進行轉帳\n💡 有疑問時可以諮詢親友或專業人士",
                                    "is_emerging": False,
                                    "display_name": display_name,
                                    "original_url": original_url,
                                    "is_image_url": True,
                                    "analysis_type": "圖片URL分析"
                                },
                                "raw_result": str(raw_result),
                                "flex_message": flex_message
                            }
                    else:
                        # 圖片分析失敗
                        return {
                            "success": False,
                            "message": "圖片分析失敗",
                            "result": {
                                "risk_level": "無法判定",
                                "fraud_type": "圖片分析失敗",
                                "explanation": f"⚠️ 無法分析此圖片URL。\n\n🔍 圖片網址：{original_url}\n\n可能原因：\n• 圖片無法下載或訪問\n• 圖片格式不支援\n• 網路連接問題\n• 圖片分析服務暫時不可用",
                                "suggestions": "🔄 請稍後再試\n📷 建議直接上傳圖片進行分析\n🔍 確認圖片URL是否正確\n💡 如果持續無法分析，請手動檢查圖片內容",
                                "is_emerging": False,
                                "display_name": display_name,
                                "original_url": original_url,
                                "is_image_url": True
                            }
                        }
                        
                except Exception as e:
                    logger.error(f"分析圖片URL時發生錯誤: {e}")
                    return {
                        "success": False,
                        "message": f"分析圖片URL時發生錯誤: {str(e)}",
                        "result": {
                            "risk_level": "無法判定",
                            "fraud_type": "圖片分析錯誤",
                            "explanation": f"❌ 分析圖片時發生技術錯誤。\n\n🔍 圖片網址：{original_url}\n\n錯誤信息：{str(e)}",
                            "suggestions": "🔄 請稍後再試\n📷 建議直接上傳圖片進行分析\n🛠️ 如果問題持續，請聯繫技術支援",
                            "is_emerging": False,
                            "display_name": display_name,
                            "original_url": original_url,
                            "is_image_url": True
                        }
                    }
                
            # 先檢查是否為短網址
            original_url, expanded_url, is_short_url, url_expanded_successfully, page_title = expand_short_url(original_url)
            
            # 如果是短網址，提供特殊處理
            if is_short_url:
                if url_expanded_successfully:
                    # 短網址成功展開，分析展開後的網址
                    analysis_message = user_message.replace(url_match.group(0), f"{original_url} (展開後: {expanded_url})")
                    logger.info(f"已展開短網址進行分析: {original_url} -> {expanded_url}")
                    
                    # 首先檢查展開後的網址是否為白名單網站
                    try:
                        parsed = urlparse(expanded_url)
                        domain = parsed.netloc.lower()
                        
                        # 創建標準化的安全網域列表
                        normalized_safe_domains = {}
                        for safe_domain, description in SAFE_DOMAINS.items():
                            safe_domain_lower = safe_domain.lower()
                            normalized_safe_domains[safe_domain_lower] = (safe_domain, description)
                            
                            if safe_domain_lower.startswith('www.'):
                                normalized_safe_domains[safe_domain_lower[4:]] = (safe_domain, description)
                            else:
                                normalized_safe_domains['www.' + safe_domain_lower] = (safe_domain, description)
                        
                        # 首先檢查完全匹配
                        if domain in normalized_safe_domains:
                            original_domain, site_description = normalized_safe_domains[domain]
                            logger.info(f"短網址展開後檢測到白名單網域: {domain} -> {original_domain}")
                            
                            # 特殊處理：酷澎招募表單 - 需要填寫個人資料，設為中風險
                            if domain == 'coupang.surveycake.biz':
                                return {
                                    "success": True,
                                    "message": "分析完成",
                                    "result": {
                                        "risk_level": "中風險",
                                        "fraud_type": "假冒招募詐騙",
                                        "explanation": f"⚠️ 這是酷澎短網址，連到招募調查表單。",
                                        "suggestions": "🔍 建議先到酷澎官方網站 tw.coupang.com 確認是否有相關招募資訊\n📞 可以致電酷澎客服確認招募活動的真實性\n⚠️ 填寫個人資料前要特別小心，避免提供過多敏感資訊\n🛡️ 如果要求提供銀行帳號、身分證號等重要資料，務必再次確認\n💡 正當的招募通常會透過官方管道或知名求職網站進行",
                                        "is_emerging": False,
                                        "display_name": display_name,
                                        "original_url": original_url,
                                        "expanded_url": expanded_url,
                                        "is_short_url": is_short_url,
                                        "url_expanded_successfully": url_expanded_successfully,
                                        "page_title": page_title
                                    },
                                    "raw_result": f"酷澎招募表單（中風險）：{site_description}"
                                }
                            
                            # 特殊處理：酷澎短網址 - 展開後連到安全網站
                            elif original_url and 'coupa.ng' in original_url.lower():
                                return {
                                    "success": True,
                                    "message": "分析完成",
                                    "result": {
                                        "risk_level": "低風險",
                                        "fraud_type": "酷澎官方短網址",
                                        "explanation": f"✅ 這是酷澎官方短網址，連到安全的購物網站。",
                                        "suggestions": "✅ 這個酷澎短網址是安全的，可以放心使用\n🔍 建議確認傳送者身份，確保不是陌生人\n⚠️ 如果內容涉及投資、賺錢，要特別小心\n🛡️ 遇到要求轉帳或提供個人資料時，務必多方查證\n💡 養成良好習慣：即使是官方平台也要保持警覺",
                                        "is_emerging": False,
                                        "display_name": display_name,
                                        "original_url": original_url,
                                        "expanded_url": expanded_url,
                                        "is_short_url": is_short_url,
                                        "url_expanded_successfully": url_expanded_successfully
                                    },
                                    "raw_result": f"酷澎官方短網址連到安全網站：{site_description}"
                                }
                            
                            # 特殊處理：lin.ee 短網址 - 展開後連到安全網站
                            elif original_url and 'lin.ee' in original_url.lower():
                                return {
                                    "success": True,
                                    "message": "分析完成",
                                    "result": {
                                        "risk_level": "低風險",
                                        "fraud_type": "LINE 官方短網址連到安全網站",
                                                                                    "explanation": f"✅ 這是 LINE 官方短網址，連到安全的網站。",
                                        "suggestions": "✅ 這個 LINE 短網址是安全的，可以放心使用\n🔍 建議確認傳送者身份，確保不是陌生人\n⚠️ 如果內容涉及投資、賺錢、購物，要特別小心\n🛡️ 遇到要求轉帳或提供個人資料時，務必多方查證\n💡 養成良好習慣：即使是官方平台也要保持警覺",
                                        "is_emerging": False,
                                        "display_name": display_name,
                                        "original_url": original_url,
                                        "expanded_url": expanded_url,
                                        "is_short_url": is_short_url,
                                        "url_expanded_successfully": url_expanded_successfully
                                    },
                                    "raw_result": f"LINE 官方短網址連到安全網站：{site_description}"
                                }
                            
                            # 其他安全網域的一般處理
                            else:
                                return {
                                    "success": True,
                                    "message": "分析完成",
                                    "result": {
                                        "risk_level": "低風險",
                                        "fraud_type": "短網址連結到安全網站",
                                        "explanation": f"✅ 這是短網址，連到安全的網站。",
                                        "suggestions": "✅ 這個短網址是安全的，可以放心使用\n🔍 建議直接從官方管道進入該網站會更安全\n💡 以後遇到短網址時，可以先詢問傳送者內容\n🛡️ 養成良好的網路安全習慣，不隨意點擊不明連結",
                                        "is_emerging": False,
                                        "display_name": display_name,
                                        "original_url": original_url,
                                        "expanded_url": expanded_url,
                                        "is_short_url": is_short_url,
                                        "url_expanded_successfully": url_expanded_successfully,
                                        "page_title": page_title
                                    },
                                    "raw_result": f"短網址展開後連到安全網站：{site_description}"
                                }
                        
                        # 檢查子網域是否屬於白名單網域
                        for safe_domain_lower, (safe_domain, description) in normalized_safe_domains.items():
                            if domain.endswith('.' + safe_domain_lower):
                                logger.info(f"短網址展開後檢測到白名單子網域: {domain} -> {safe_domain}")
                                
                                # 特殊處理：lin.ee 短網址 - 展開後連到安全網站的子網域
                                if original_url and 'lin.ee' in original_url.lower():
                                    return {
                                        "success": True,
                                        "message": "分析完成",
                                        "result": {
                                            "risk_level": "低風險",
                                            "fraud_type": "LINE 官方短網址連到安全網站",
                                            "explanation": f"✅ 這是 LINE 官方短網址，連到安全的網站。",
                                            "suggestions": "✅ 這個 LINE 短網址是安全的，可以放心使用\n🔍 建議確認傳送者身份，確保不是陌生人\n⚠️ 如果內容涉及投資、賺錢、購物，要特別小心\n🛡️ 遇到要求轉帳或提供個人資料時，務必多方查證\n💡 養成良好習慣：即使是官方平台也要保持警覺",
                                            "is_emerging": False,
                                            "display_name": display_name,
                                            "original_url": original_url,
                                            "expanded_url": expanded_url,
                                            "is_short_url": is_short_url,
                                            "url_expanded_successfully": url_expanded_successfully
                                        },
                                        "raw_result": f"LINE 官方短網址連到安全網站：{description}"
                                    }
                                
                                # 其他安全網域的一般處理
                                return {
                                    "success": True,
                                    "message": "分析完成",
                                    "result": {
                                        "risk_level": "低風險",
                                        "fraud_type": "短網址連結到安全網站",
                                        "explanation": f"✅ 這是短網址，連到安全的網站。",
                                        "suggestions": "✅ 這個短網址是安全的，可以放心使用\n🔍 建議直接從官方管道進入該網站會更安全\n💡 以後遇到短網址時，可以先詢問傳送者內容\n🛡️ 養成良好的網路安全習慣，不隨意點擊不明連結",
                                        "is_emerging": False,
                                        "display_name": display_name,
                                        "original_url": original_url,
                                        "expanded_url": expanded_url,
                                        "is_short_url": is_short_url,
                                        "url_expanded_successfully": url_expanded_successfully
                                    },
                                    "raw_result": f"短網址展開後連到安全網站：{description}"
                                }
                    except Exception as e:
                        logger.error(f"解析展開後的網址時發生錯誤: {e}")
                    
                    # 如果不是白名單網站，再進行網域變形檢測
                    spoofing_result = detect_domain_spoofing(expanded_url, SAFE_DOMAINS)
                    if spoofing_result['is_spoofed']:
                        logger.warning(f"短網址展開後檢測到網域變形攻擊: {spoofing_result['spoofed_domain']} 模仿 {spoofing_result['original_domain']}")
                        return {
                            "success": True,
                            "message": "分析完成",
                            "result": {
                                "risk_level": "極高風險",
                                "fraud_type": "短網址隱藏的網域變形攻擊",
                                "explanation": f"⚠️ 這是短網址，連到假冒網站！",
                                "suggestions": f"🚫 立即停止點擊這個短網址\n⚠️ 不要輸入任何個人資料或密碼\n🔍 如需使用正牌網站，請直接搜尋 {spoofing_result['original_domain']} 或從書籤進入\n📞 將此可疑網址回報給165反詐騙專線\n💡 以後遇到短網址要特別小心，建議先詢問傳送者內容",
                                "is_emerging": False,
                                "display_name": display_name,
                                "original_url": original_url,
                                "expanded_url": expanded_url,
                                "is_short_url": is_short_url,
                                "url_expanded_successfully": url_expanded_successfully,
                                "page_title": page_title,
                                "is_domain_spoofing": True,
                                "spoofing_result": spoofing_result
                            },
                            "raw_result": f"短網址隱藏的網域變形攻擊：{spoofing_result['spoofing_type']} - {spoofing_result['risk_explanation']}"
                        }
                    
                    # 如果展開後的網址不是變形攻擊也不是白名單，使用 OpenAI 分析
                    logger.info(f"短網址展開後需要進一步分析: {original_url} -> {expanded_url}")
                    
                    # 特殊處理：lin.ee 短網址展開後不是安全網站，需要更詳細的分析
                    if original_url and 'lin.ee' in original_url.lower():
                        # 修改分析訊息，包含短網址和展開後的資訊
                        analysis_message = f"這是一個 LINE 官方短網址 {original_url}，展開後連到 {expanded_url}。請分析展開後的網站內容是否為詐騙，特別注意：1. 是否為投資詐騙 2. 是否為購物詐騙 3. 是否為假交友詐騙 4. 是否要求提供個人資料或金錢 5. 網站內容是否可疑。由於詐騙集團會申請正規 LINE 帳號來傳送詐騙連結，請特別仔細分析。"
                    else:
                        # 一般短網址的分析
                        analysis_message = f"這是一個短網址 {original_url}，展開後連到 {expanded_url}。請分析展開後的網站內容是否為詐騙。"
                    
                    # 繼續使用 OpenAI 分析展開後的內容
                else:
                    # 短網址無法展開，直接返回高風險
                    logger.warning(f"短網址無法展開: {original_url}")
                    
                    # 特殊處理：lin.ee 無法展開的情況
                    if original_url and 'lin.ee' in original_url.lower():
                        # 檢查訊息內容是否包含明顯的詐騙關鍵詞
                        fraud_keywords = [
                            "投資", "獲利", "賺錢", "收益", "報酬", "保證", "穩賺", "高報酬", "低風險",
                            "限時", "優惠", "機會", "名額", "今天", "立即", "馬上", "快速",
                            "轉帳", "匯款", "付款", "先付", "保證金", "手續費", "會費",
                            "私聊", "加LINE", "加我", "聯繫我", "詳談", "私下", "一對一"
                        ]
                        
                        suspicious_content = any(keyword in user_message for keyword in fraud_keywords)
                        
                        if suspicious_content:
                            # 如果訊息內容可疑，進行完整分析而不是直接返回
                            logger.warning(f"lin.ee 無法展開且訊息內容可疑，進行完整分析")
                            analysis_message = f"這個訊息包含一個無法展開的 LINE 官方短網址 {original_url}，同時訊息內容可能涉及詐騙。請仔細分析整個訊息內容是否為詐騙，特別注意投資詐騙、購物詐騙等常見手法。訊息內容：{user_message}"
                            # 繼續進行 OpenAI 分析，不直接返回
                        else:
                            # 如果訊息內容看起來正常，返回中風險警告
                            return {
                                "success": True,
                                "message": "分析完成",
                                "result": {
                                    "risk_level": "中風險",
                                    "fraud_type": "LINE 官方短網址無法展開",
                                    "explanation": f"⚠️ 這是一個 LINE 官方短網址，但我們無法展開查看真正的目的地。\n\n🔍 短網址：{original_url}\n\n可能原因：\n• 連結已失效或過期\n• LINE 官方帳號被停用\n• 網站暫時無法訪問\n• 可能是惡意連結被封鎖\n\n💡 雖然是 LINE 官方服務，但詐騙集團也會申請正規 LINE 帳號。無法展開的連結需要特別小心。",
                                    "suggestions": "🔍 詢問傳送者這個連結的具體內容和目的\n⚠️ 確認傳送者身份是否可信\n🛡️ 如果不確定來源或內容，建議不要點擊\n📞 如有疑慮可撥打165反詐騙專線諮詢\n💡 記住：即使是官方平台，也可能被不肖人士利用",
                                    "is_emerging": False,
                                    "display_name": display_name,
                                    "original_url": original_url,
                                    "expanded_url": expanded_url,
                                    "is_short_url": is_short_url,
                                    "url_expanded_successfully": url_expanded_successfully
                                },
                                "raw_result": f"LINE 官方短網址無法展開，需要謹慎確認：{original_url}"
                            }
                    else:
                        # 一般短網址無法展開，設定分析訊息但不直接返回
                        analysis_message = user_message
                    
                    # 如果不是 lin.ee 或 lin.ee 內容不可疑，對於一般短網址無法展開直接返回高風險
                    if not (original_url and 'lin.ee' in original_url.lower()):
                        return {
                            "success": True,
                            "message": "分析完成",
                            "result": {
                                "risk_level": "高風險",
                                "fraud_type": "失效或可疑短網址",
                                "explanation": f"⚠️ 這是一個短網址，但我們無法展開查看真正的目的地。\n\n🔍 短網址：{original_url}\n\n可能原因：\n• 網址已失效或過期\n• 網站暫時無法訪問\n• 可能是惡意網址被封鎖\n• 詐騙網站被下架\n\n💡 無法驗證的短網址特別危險，因為不知道會連到哪個網站。",
                                "suggestions": "🚫 立即停止點擊這個短網址\n🔍 詢問傳送者這個連結的具體內容\n⚠️ 如果不確定來源，直接刪除或忽略\n🛡️ 遇到失效短網址要特別小心，可能是詐騙陷阱\n📞 如有疑慮可撥打165反詐騙專線諮詢",
                                "is_emerging": False,
                                "display_name": display_name,
                                "original_url": original_url,
                                "expanded_url": expanded_url,
                                "is_short_url": is_short_url,
                                "url_expanded_successfully": url_expanded_successfully
                            },
                            "raw_result": f"短網址無法展開，存在安全風險：{original_url}"
                        }
            else:
                analysis_message = user_message
        else:
            analysis_message = user_message

        # 只有在非短網址的情況下才進行網域變形檢測
        if not is_short_url:
            spoofing_result = detect_domain_spoofing(analysis_message, SAFE_DOMAINS)
            if spoofing_result['is_spoofed']:
                logger.warning(f"檢測到網域變形攻擊: {spoofing_result['spoofed_domain']} 模仿 {spoofing_result['original_domain']}")
                return {
                    "success": True,
                    "message": "分析完成",
                    "result": {
                        "risk_level": "極高風險",
                        "fraud_type": "網域名稱變形攻擊",
                        "explanation": spoofing_result['risk_explanation'],
                        "suggestions": f"🚫 立即停止使用這個網站\n⚠️ 不要輸入任何個人資料或密碼\n🔍 如需使用正牌網站，請直接搜尋 {spoofing_result['original_domain']} 或從書籤進入\n📞 將此可疑網址回報給165反詐騙專線",
                        "is_emerging": False,
                        "display_name": display_name,
                        "original_url": original_url,
                        "expanded_url": expanded_url,
                        "is_short_url": is_short_url,
                        "url_expanded_successfully": url_expanded_successfully,
                        "is_domain_spoofing": True,
                        "spoofing_result": spoofing_result
                    },
                    "raw_result": f"網域變形攻擊檢測：{spoofing_result['spoofing_type']} - {spoofing_result['risk_explanation']}"
                }

        # 檢查招聘訊息是否為低風險
        recruitment_keywords = ["招聘", "招募", "徵才", "應徵", "面試", "職缺", "工作機會", "求才", "求職", "人才", "履歷", "人力銀行", "104人力銀行"]
        is_recruitment_message = any(keyword in user_message for keyword in recruitment_keywords)
        
        if is_recruitment_message:
            # 檢查是否包含正規人力銀行平台
            has_job_bank = any(platform in user_message for platform in ["104人力銀行", "104", "1111人力銀行", "1111", "518人力銀行", "518", "yes123", "人力銀行"])
            
            # 檢查是否有完整公司名稱
            company_pattern = re.compile(r'[^\s]{2,}(?:股份有限公司|有限公司|公司|企業社|工作室|事務所)')
            has_company_name = bool(company_pattern.search(user_message))
            
            # 檢查是否有合法聯絡方式
            phone_pattern = re.compile(r'(?:(?:連絡|聯絡|聯繫|電話|手機|聯絡電話|連絡電話)(?:電話)?[:：]?\s*)?(?:\(?\s*(?:0800|0[2-9]|0[2-9]-\d{7}|\d{2}-\d{6,8}|\d{2}\d{8}|09\d{2}[ -]?\d{6}|09\d{8})\)?(?:\s*(?:分機|#|ext|轉)\s*\d{2,5})?)', re.IGNORECASE)
            has_phone = bool(phone_pattern.search(user_message))
            
            # 檢查是否有聯絡人
            contact_pattern = re.compile(r'(?:(?:連絡|聯絡|聯繫)(?:人|窗口|人員)[:：]?\s*)([\u4e00-\u9fff]{1,3}(?:先生|小姐|專員|經理|主任|組長|店長)?)|(?:([\u4e00-\u9fff]{1,3})(?:先生|小姐|專員|經理|主任))', re.IGNORECASE)
            has_contact_person = bool(contact_pattern.search(user_message))
            
            # 檢查是否有工作內容描述
            job_description_pattern = re.compile(r'(?:工作內容|職務內容|工作職責|工作描述|工作項目|職務項目)')
            has_job_description = bool(job_description_pattern.search(user_message))
            
            # 檢查是否有薪資資訊
            salary_pattern = re.compile(r'(?:薪資|待遇|月薪|時薪)(?:：|:|\s)*(?:\d{2,6}[~-至]?(?:\d{2,6})?\s*(?:元|萬元|月|年薪)?)')
            has_salary_info = bool(salary_pattern.search(user_message))
            
            # 檢查是否有面試地點或工作地點
            location_pattern = re.compile(r'(?:面試地(?:點|址)|工作地(?:點|址)|地(?:點|址)|公司地(?:點|址))[:：]?\s*(?:[\u4e00-\u9fff]+(?:市|縣|區)[\u4e00-\u9fff0-9]+(?:路|街|道)[\u4e00-\u9fff0-9號]+)')
            has_location = bool(location_pattern.search(user_message))
            
            # 檢查是否有明確的工作/面試時間
            time_pattern = re.compile(r'(?:工作時間|上班時間|出勤時間|面試時間)[:：]?\s*(?:[上下]午|\d{1,2}[.:：]\d{2}[~-至]\d{1,2}[.:：]\d{2}|(?:週|星期)[一二三四五六日])')
            has_time_info = bool(time_pattern.search(user_message))
            
            # 檢查是否有可疑要求
            suspicious_requests = ["預付", "先付", "支付費用", "繳納保證金", "繳交", "繳費", "保證金", "訂金", "先轉帳", "先匯款", "面試費", "報名費", "資料處理費", "審核費"]
            has_suspicious_requests = any(request in user_message for request in suspicious_requests)
            
            # 檢查是否包含高薪誘餌
            bait_pattern = re.compile(r'(?:高薪|高額獎金|獎金無上限|輕鬆賺|輕鬆(?:\d{1,2})萬|(?:\d{1,2})萬起)')
            has_salary_bait = bool(bait_pattern.search(user_message))
            
            # 檢查是否為可疑的兼職類型
            suspicious_part_time_jobs = [
                "網路兼職", "打字兼職", "刷單", "購物助理", "網購助理", "日結", "日領", "小時工", 
                "網賺", "網絡賺錢", "在家工作", "零投入", "零門檻", "兼職賺錢", "輕鬆兼職", 
                "賺外快", "代練", "代購", "代刷", "網店代運營", "點贊", "點擊", "評論", "包養"
            ]
            has_suspicious_part_time = any(job_type in user_message for job_type in suspicious_part_time_jobs)
            
            # 檢查是否要求添加個人社交媒體帳號
            social_media_pattern = re.compile(r'(?:加|添加|聯繫|聯絡|私聊)(?:我的?|群主的?|老師的?)?(?:LINE|微信|WeChat|telegram|TG|IG|私人|私聊)', re.IGNORECASE)
            requires_social_media = bool(social_media_pattern.search(user_message))
            
            # 檢查是否包含典型詐騙招聘關鍵詞組合
            scam_combinations = [
                (has_salary_bait and has_suspicious_part_time),  # 高薪+可疑兼職類型
                (has_salary_bait and requires_social_media and not has_job_bank),  # 高薪+要求加LINE等+非正規平台
                (has_suspicious_part_time and requires_social_media),  # 可疑兼職+要求加LINE等
                (has_salary_bait and "無需經驗" in user_message),  # 高薪+無需經驗
                (has_salary_bait and "無經驗" in user_message),  # 高薪+無經驗
                (has_salary_bait and "兼職" in user_message and "在家" in user_message)  # 高薪+兼職+在家工作
            ]
            
            is_likely_scam_job = any(scam_combinations)
            
            # 明確的詐騙指標
            if is_likely_scam_job or has_suspicious_requests:
                logger.warning(f"檢測到可疑招聘訊息，疑似詐騙")
                
                explanation = "這則招聘訊息存在多個可疑特徵，可能是詐騙："
                if has_salary_bait:
                    explanation += "\n• 過高或不合理的薪資承諾"
                if has_suspicious_part_time:
                    explanation += "\n• 可疑的兼職類型（如網路兼職、刷單、代購等）"
                if requires_social_media:
                    explanation += "\n• 要求加入個人社交媒體帳號而非透過正規管道應徵"
                if has_suspicious_requests:
                    explanation += "\n• 要求預先支付費用或保證金"
                if not has_job_bank and not has_company_name:
                    explanation += "\n• 沒有明確的公司資訊或非透過正規人力銀行平台"
                
                suggestions = "🚨 求職安全警告：\n"
                suggestions += "• 合法企業不會要求應徵者預付任何費用\n"
                suggestions += "• 對過高薪資承諾要特別警惕，尤其是無經驗要求的工作\n"
                suggestions += "• 建議透過104、1111等正規人力銀行平台求職\n"
                suggestions += "• 可向165反詐騙專線諮詢\n"
                suggestions += "• 避免加入不明人士的社交媒體或通訊軟體"
                
                return {
                    "success": True,
                    "message": "分析完成",
                    "result": {
                        "risk_level": "高風險",
                        "fraud_type": "可疑招聘詐騙",
                        "explanation": explanation,
                        "suggestions": suggestions,
                        "is_emerging": True,
                        "display_name": display_name,
                        "original_url": original_url,
                        "expanded_url": expanded_url,
                        "is_short_url": is_short_url,
                        "url_expanded_successfully": url_expanded_successfully
                    },
                    "raw_result": "經過分析，這可能是招聘詐騙訊息，具有多個可疑特徵。"
                }
            
            # 計算招聘信息的安全得分
            recruitment_safety_score = 0
            if has_job_bank:
                recruitment_safety_score += 3  # 使用正規人力銀行是很重要的安全指標
            if has_company_name:
                recruitment_safety_score += 2  # 提供完整公司名稱
            if has_phone:
                recruitment_safety_score += 1  # 提供電話
            if has_contact_person:
                recruitment_safety_score += 1  # 提供聯絡人
            if has_job_description:
                recruitment_safety_score += 1  # 提供工作內容
            if has_salary_info:
                recruitment_safety_score += 1  # 提供薪資資訊
            if has_location:
                recruitment_safety_score += 2  # 提供面試/工作地點
            if has_time_info:
                recruitment_safety_score += 1  # 提供工作/面試時間
            if has_suspicious_requests:
                recruitment_safety_score -= 5  # 有可疑要求大幅降低安全分數
            if has_salary_bait and not has_job_description:
                recruitment_safety_score -= 2  # 只有高薪誘餌但無詳細工作內容
            
            # 若招聘信息安全得分高，判定為低風險
            if recruitment_safety_score >= 5 and not has_suspicious_requests:
                logger.info(f"檢測到正常招聘訊息，安全得分: {recruitment_safety_score}")
                
                # 產生合適的解釋文本
                explanation = "這看起來是一則正常的求職招聘訊息，"
                if has_job_bank:
                    explanation += "透過正規人力銀行平台發布，"
                if has_company_name:
                    explanation += "有完整的公司名稱，"
                if has_phone:
                    explanation += "提供了聯絡電話，"
                if has_contact_person:
                    explanation += "有明確的聯絡窗口，"
                if has_location:
                    explanation += "提供了面試/工作地點，"
                if has_time_info:
                    explanation += "說明了工作/面試時間，"
                explanation += "整體來說風險較低。"
                
                suggestions = "✅ 求職安全提醒：\n"
                suggestions += "• 在面試前先查詢該公司的背景和評價\n"
                suggestions += "• 面試地點應選擇在公司正式辦公地點\n"
                suggestions += "• 留意是否要求預付任何費用（正常公司不會要求）\n"
                suggestions += "• 提供個人資料時應保持謹慎\n"
                suggestions += "• 若有疑慮，可透過104或1111等人力銀行官方管道查詢"
                
                return {
                    "success": True,
                    "message": "分析完成",
                    "result": {
                        "risk_level": "低風險",
                        "fraud_type": "正常招聘資訊",
                        "explanation": explanation,
                        "suggestions": suggestions,
                        "is_emerging": False,
                        "display_name": display_name,
                        "original_url": original_url,
                        "expanded_url": expanded_url,
                        "is_short_url": is_short_url,
                        "url_expanded_successfully": url_expanded_successfully
                    },
                    "raw_result": f"經過分析，這是正常的招聘資訊，安全得分: {recruitment_safety_score}"
                }

        # 檢查白名單網址
        url_pattern_detailed = re.compile(r'https?://[^\s\u4e00-\u9fff，。！？；：]+|www\.[^\s\u4e00-\u9fff，。！？；：]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s\u4e00-\u9fff，。！？；：]*)?')
        urls = url_pattern_detailed.findall(analysis_message)
        
        cleaned_urls = []
        for url in urls:
            cleaned_url = re.sub(r'[，。！？；：]+$', '', url)
            if cleaned_url:
                cleaned_urls.append(cleaned_url)
        
        normalized_safe_domains = {}
        for safe_domain, description in SAFE_DOMAINS.items():
            safe_domain_lower = safe_domain.lower()
            normalized_safe_domains[safe_domain_lower] = (safe_domain, description)
            
            if safe_domain_lower.startswith('www.'):
                normalized_safe_domains[safe_domain_lower[4:]] = (safe_domain, description)
            else:
                normalized_safe_domains['www.' + safe_domain_lower] = (safe_domain, description)
        
        for url in cleaned_urls:
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = 'https://' + url
                else:
                    url = 'https://' + url
            
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                
                if domain in normalized_safe_domains:
                    original_domain, site_description = normalized_safe_domains[domain]
                    logger.info(f"檢測到白名單中的域名: {domain} -> {original_domain}")
                    
                    # 獲取網頁標題並摘要
                    website_title = None
                    title_summary = None
                    if not is_short_url:
                        website_title = get_website_title(url)
                        if website_title:
                            title_summary = summarize_website_title(website_title, original_domain)
                    elif is_short_url and url_expanded_successfully:
                        website_title = page_title
                        if website_title:
                            title_summary = summarize_website_title(website_title, original_domain)
                    
                    # 特殊處理：lin.ee 需要檢查訊息內容
                    if domain == 'lin.ee':
                        # 檢查訊息內容是否包含明顯的詐騙關鍵詞
                        fraud_keywords = [
                            "投資", "獲利", "賺錢", "收益", "報酬", "保證", "穩賺", "高報酬", "低風險",
                            "限時", "優惠", "機會", "名額", "今天", "立即", "馬上", "快速",
                            "轉帳", "匯款", "付款", "先付", "保證金", "手續費", "會費",
                            "私聊", "加LINE", "加我", "聯繫我", "詳談", "私下", "一對一"
                        ]
                        
                        suspicious_content = any(keyword in user_message for keyword in fraud_keywords)
                        
                        if suspicious_content:
                            # 如果訊息內容可疑，不直接返回，繼續進行 OpenAI 分析
                            logger.warning(f"lin.ee 在白名單中但訊息內容可疑，進行完整分析")
                            analysis_message = f"這個訊息包含 LINE 官方短網址 {original_url}，但訊息內容可能涉及詐騙。請仔細分析整個訊息內容是否為詐騙，特別注意投資詐騙、購物詐騙等常見手法。訊息內容：{user_message}"
                            # 不返回，繼續進行分析
                        else:
                            # 如果訊息內容看起來正常，返回低風險
                            return {
                                "success": True,
                                "message": "分析完成",
                                "result": {
                                    "risk_level": "低風險",
                                    "fraud_type": "非詐騙相關",
                                    "explanation": f"這個網站是 {original_domain}，{site_description}，可以安心使用。" + (f"\n\n📄 內容：{title_summary}" if title_summary else ""),
                                    "suggestions": "這是正規網站，不必特別擔心。如有疑慮，建議您直接從官方管道進入該網站。",
                                    "is_emerging": False,
                                    "display_name": display_name,
                                    "original_url": original_url,
                                    "expanded_url": expanded_url,
                                    "is_short_url": is_short_url,
                                    "url_expanded_successfully": url_expanded_successfully,
                                    "page_title": website_title
                                },
                                "raw_result": f"經過分析，這是已知的可信任網站：{site_description}"
                            }
                    else:
                        # 其他白名單網域的一般處理
                        return {
                            "success": True,
                            "message": "分析完成",
                            "result": {
                                "risk_level": "低風險",
                                "fraud_type": "非詐騙相關",
                                "explanation": f"這個網站是 {original_domain}，{site_description}，可以安心使用。" + (f"\n\n📄 內容：{title_summary}" if title_summary else ""),
                                "suggestions": "這是正規網站，不必特別擔心。如有疑慮，建議您直接從官方管道進入該網站。",
                                "is_emerging": False,
                                "display_name": display_name,
                                                            "original_url": original_url,
                            "expanded_url": expanded_url,
                            "is_short_url": is_short_url,
                            "url_expanded_successfully": url_expanded_successfully,
                            "page_title": website_title
                        },
                        "raw_result": f"經過分析，這是已知的可信任網站：{site_description}"
                        }
                
                for safe_domain_key in SAFE_DOMAINS.keys():
                    safe_domain_lower = safe_domain_key.lower()
                    safe_domain_clean = safe_domain_lower[4:] if safe_domain_lower.startswith('www.') else safe_domain_lower
                    domain_clean = domain[4:] if domain.startswith('www.') else domain
                    
                    if domain_clean.endswith('.' + safe_domain_clean):
                        if domain_clean != safe_domain_clean:
                            subdomain_part = domain_clean[:-len('.' + safe_domain_clean)]
                            
                            if _is_legitimate_subdomain(subdomain_part):
                                site_description = SAFE_DOMAINS.get(safe_domain_key, "台灣常見的可靠網站")
                                logger.info(f"檢測到合法子網域: {domain} -> {safe_domain_key}")
                                
                                # 獲取網頁標題並摘要
                                website_title = None
                                title_summary = None
                                if not is_short_url:
                                    website_title = get_website_title(url)
                                    if website_title:
                                        title_summary = summarize_website_title(website_title, safe_domain_key)
                                elif is_short_url and url_expanded_successfully:
                                    website_title = page_title
                                    if website_title:
                                        title_summary = summarize_website_title(website_title, safe_domain_key)
                                
                                return {
                                    "success": True,
                                    "message": "分析完成",
                                    "result": {
                                        "risk_level": "低風險",
                                        "fraud_type": "非詐騙相關",
                                        "explanation": f"這個網站是 {safe_domain_key} 的子網域，{site_description}，可以安心使用。" + (f"\n\n📄 內容：{title_summary}" if title_summary else ""),
                                        "suggestions": "這是正規網站的子網域，不必特別擔心。如有疑慮，建議您直接從官方管道進入該網站。",
                                        "is_emerging": False,
                                        "display_name": display_name,
                                        "original_url": original_url,
                                        "expanded_url": expanded_url,
                                        "is_short_url": is_short_url,
                                        "url_expanded_successfully": url_expanded_successfully,
                                        "page_title": website_title
                                    },
                                    "raw_result": f"經過分析，這是已知可信任網站的子網域：{site_description}"
                                }
            except Exception as e:
                continue
        
        # 短網址無法展開的特殊處理
        special_notes = ""
        if is_short_url and not url_expanded_successfully:
            special_notes = """⚠️ 特別注意：這是一個短網址，但我們無法展開查看真正的目的地。

可能的原因：
1. 網址已失效或過期
2. 網站暫時無法訪問
3. 可能是惡意網址被封鎖

這種情況特別危險，因為：
• 短網址常被詐騙者用來隱藏真實的惡意網站
• 無法驗證真正的目的地
• 可能是釣魚網站或惡意軟體下載點

建議立即停止點擊，除非您非常確定這個連結的來源安全。"""
            logger.warning(f"無法展開的短網址: {original_url}，建議提高警覺")
        
        openai_prompt = f"""
        你是一位名為「防詐騙助手」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。你的說話風格要：\n1. 非常簡單易懂，像鄰居朋友在聊天\n2. 用溫暖親切的語氣，不要太正式\n3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號\n4. 避免複雜的專業術語，用日常生活的話來解釋\n5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議\n6. 回應要簡短，不要太長篇大論\n\n詐騙類型分類指南：\n1. 購物詐騙/虛假廣告：涉及商品購買、減肥產品、美容產品、健康食品等宣稱效果誇大的商品\n2. 投資詐騙：涉及投資理財、股票、基金、加密貨幣等金融投資行為\n3. 假交友詐騙：涉及交友、約會、婚戀等感情互動\n4. 釣魚網站：偽造的網站，試圖騙取用戶的個人或金融資料\n5. 假冒身分詐騙：冒充親友、公司、政府機構等身份\n6. 中獎詐騙：宣稱用戶中獎或獲得意外獎勵\n7. 求職詐騙：涉及工作機會、求職、兼職等就業相關內容\n8. 網路釣魚：通過電子郵件、簡訊等方式誘導用戶點擊惡意鏈接\n9. 失效短網址風險：無法展開或驗證的短網址\n10. 其他詐騙：不屬於上述類別的其他詐騙形式\n\n若分析的是產品效果的真實性（如減肥、美容產品等），請歸類為「購物詐騙/虛假廣告」而非投資詐騙。
        """
        
        if not openai_client:
            logger.error("OpenAI客戶端未初始化，無法進行分析")
            return {
                "success": False,
                "message": "AI分析服務暫時不可用，請稍後再試"
            }
        
        # 獲取網頁標題（如果還沒有獲取的話）
        website_title = None
        if original_url and not is_short_url:
            website_title = get_website_title(expanded_url or original_url)
        elif is_short_url and url_expanded_successfully and expanded_url:
            # 短網址已經在 expand_short_url 中獲取了標題，這裡使用 page_title
            website_title = page_title
        
        # 構建詳細的分析請求
        title_info = ""
        if website_title:
            title_info = f"\n網頁標題：{website_title}"
        
        analysis_request = f"""請分析以下訊息是否為詐騙，並按照以下格式回覆：

風險等級：[極低風險/低風險/中風險/高風險/極高風險]
詐騙類型：[根據上述分類指南選擇具體類型，不要使用"未知"]
分析說明：[用40字以內單句解釋為什麼這個訊息可疑或安全，不得條列式，要具體分析內容]
土豆建議：[給出具體的防範建議，使用emoji符號。高風險必須嚴肅具體，如"立即停止操作，直接聯繫官方客服確認！📞🔒"；低風險可幽默，如"放心啦，這只是正常的通知而已😊"]
新興手法：[是/否]

要分析的訊息：
{analysis_message}{title_info}

請仔細分析訊息內容，不要給出模糊的回答。如果是詐騙，要明確指出是哪種類型的詐騙。{f'網頁標題「{website_title}」也提供了重要的分析線索。' if website_title else ''}"""
        
        chat_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位專業的防詐騙分析師，專門幫助識別各種詐騙手法。你必須仔細分析每個訊息的內容，給出具體明確的分析結果，不能使用模糊的詞彙如'未知'。"},
                {"role": "user", "content": analysis_request}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        if chat_response and chat_response.choices:
            analysis_result = chat_response.choices[0].message.content.strip()
            logger.info(f"風險分析結果: {analysis_result[:100]}...")
            
            parsed_result = parse_fraud_analysis(analysis_result)
            parsed_result["display_name"] = display_name
            parsed_result["original_url"] = original_url
            parsed_result["expanded_url"] = expanded_url
            parsed_result["is_short_url"] = is_short_url
            parsed_result["url_expanded_successfully"] = url_expanded_successfully
            parsed_result["page_title"] = website_title or page_title
            
            if is_short_url and not url_expanded_successfully:
                if parsed_result["risk_level"] in ["低風險", "中風險", "極低風險"]:
                    parsed_result["risk_level"] = "高風險"
                
                if "失效" not in parsed_result["fraud_type"] and "短網址" not in parsed_result["fraud_type"]:
                    parsed_result["fraud_type"] = "失效短網址風險"
                
                base_explanation = parsed_result["explanation"]
                parsed_result["explanation"] = f"⚠️ 這是一個短網址，但我們無法展開查看真正的目的地。\n\n可能原因：\n• 網址已失效或過期\n• 網站暫時無法訪問\n• 可能是惡意網址被封鎖\n\n{base_explanation}\n\n💡 無法驗證的短網址特別危險，因為不知道會連到哪個網站，建議不要點擊。"
                
                parsed_result["suggestions"] = f"🚫 立即停止點擊這個短網址\n🔍 詢問傳送者這個連結的具體內容\n⚠️ 如果不確定來源，直接刪除或忽略\n🛡️ 遇到失效短網址要特別小心，可能是詐騙陷阱\n\n原建議：{parsed_result['suggestions']}"
            
            elif is_short_url and url_expanded_successfully:
                parsed_result["explanation"] = f"{parsed_result['explanation']}\n\n✅ 這個短網址已成功展開，真正的目的地是：{expanded_url}\n我們已經根據真實網站進行分析。"
            
            if not parsed_result.get("explanation") or parsed_result["explanation"] == "無法解析分析結果。":
                logger.warning("無法正確解析分析理由，使用原始回應替代")
                parsed_result["explanation"] = analysis_result.replace("風險等級：", "").replace("詐騙類型：", "").replace("說明：", "").replace("建議：", "").replace("新興手法：", "").strip()
                
                if not parsed_result["explanation"] or parsed_result["explanation"].strip() == "":
                    parsed_result["explanation"] = "這個內容看起來有點奇怪，建議不要輕易點擊或提供個人資料。如果不確定，可以請家人幫忙確認一下。"
            
            return {
                "success": True,
                "message": "分析完成",
                "result": parsed_result,
                "raw_result": analysis_result
            }
        else:
            logger.error("OpenAI API 返回空結果")
            return {
                "success": False,
                "message": "分析失敗，請稍後再試"
            }
            
    except Exception as e:
        logger.exception(f"使用OpenAI分析詐騙信息時發生錯誤: {e}")
        return {
            "success": False,
            "message": f"分析過程中發生錯誤: {str(e)}"
        }

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
        
    return 'OK'

@app.route("/", methods=['GET'])
def home():
    return "Line Bot Anti-Fraud is running!"

@app.route("/health", methods=['GET'])
def health_check():
    """健康檢查端點，用於 keep-alive 和監控"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server": "gunicorn",
        "service": "anti-fraud-linebot"
    }

@app.route("/keep-alive", methods=['GET'])
def keep_alive():
    """Keep-alive 端點，防止服務休眠"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "message": "Service is active",
        "uptime": str(datetime.now() - app_start_time) if 'app_start_time' in globals() else "unknown",
        "memory_usage": f"{process.memory_info().rss / 1024 / 1024:.1f}MB" if 'process' in globals() else "unknown",
        "active_users": len(user_conversation_state),
        "server": "gunicorn"
    }

@app.route("/fraud-statistics", methods=['GET'])
def fraud_statistics():
    """顯示詐騙統計數據頁面"""
    stats = firebase_manager.get_fraud_statistics()
    return render_template('statistics.html', stats=stats)

# 訊息發送重試機制
def _send_message_with_retry(reply_token, message_text, user_id, display_name, interaction_type, max_retries=2):
    """
    帶重連機制的訊息發送函數
    
    Args:
        reply_token: LINE回覆令牌
        message_text: 要發送的訊息內容
        user_id: 用戶ID
        display_name: 用戶顯示名稱
        interaction_type: 互動類型
        max_retries: 最大重試次數
        
    Returns:
        bool: 發送是否成功
    """
    import time
    import requests
    from requests.exceptions import ConnectionError, Timeout
    
    for attempt in range(max_retries + 1):
        try:
            if v3_messaging_api:
                from linebot.v3.messaging import TextMessage as V3TextMessage
                from linebot.v3.messaging import ReplyMessageRequest
                v3_messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[V3TextMessage(text=message_text)]
                    )
                )
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=message_text))
            
            # 保存互動記錄到Firebase
            firebase_manager.save_user_interaction(
                user_id, display_name, "系統訊息", interaction_type,
                is_fraud_related=False
            )
            
            logger.info(f"成功發送訊息給用戶 {display_name} (嘗試 {attempt + 1}/{max_retries + 1})")
            return True
            
        except LineBotApiError as e:
            logger.error(f"發送訊息時發生LINE API錯誤 (嘗試 {attempt + 1}/{max_retries + 1}): {e}")
            if "Invalid reply token" in str(e):
                # reply token 無效，不需要重試
                logger.warning(f"Reply token 無效，停止重試: {display_name}")
                return False
                
        except (ConnectionError, requests.exceptions.ConnectionError, Timeout) as e:
            logger.error(f"發送訊息時發生連接錯誤 (嘗試 {attempt + 1}/{max_retries + 1}): {e}")
            
            if attempt < max_retries:
                # 等待一段時間後重試
                wait_time = (attempt + 1) * 2  # 2秒, 4秒, 6秒...
                logger.info(f"等待 {wait_time} 秒後重試...")
                time.sleep(wait_time)
                continue
            else:
                # 所有重試都失敗，記錄最終失敗
                logger.error(f"所有重試都失敗，無法發送訊息給用戶 {display_name}")
                return False
                
        except Exception as e:
            logger.error(f"發送訊息時發生未知錯誤 (嘗試 {attempt + 1}/{max_retries + 1}): {e}")
            
            if attempt < max_retries:
                wait_time = (attempt + 1) * 2
                logger.info(f"等待 {wait_time} 秒後重試...")
                time.sleep(wait_time)
                continue
            else:
                return False
    
    return False

def _get_recovery_message_prefix(current_state, display_name):
    """
    獲取恢復訊息前綴（如果需要的話）
    
    Args:
        current_state: 當前用戶狀態
        display_name: 用戶顯示名稱
        
    Returns:
        str: 恢復訊息前綴，如果不需要則返回空字符串
    """
    if current_state.get("show_recovery_message", False):
        recovery_context = current_state.get("recovery_context", {})
        failed_type = recovery_context.get("failed_message_type")
        
        recovery_prefix = f"哈囉 {display_name}！我是土豆🥜\n\n" \
                        f"剛剛發生了一些技術問題（LINE和我切八段了QQ），不好意思讓您久等了！\n\n"
        
        if failed_type == "analysis_prompt":
            recovery_prefix += "您剛才想要分析訊息對吧？太好了，我現在可以幫您分析了！\n\n"
        else:
            recovery_prefix += "現在一切都恢復正常了！\n\n"
        
        # 清除恢復訊息狀態
        current_state["show_recovery_message"] = False
        if "recovery_context" in current_state:
            del current_state["recovery_context"]
        
        return recovery_prefix
    
    return ""

def _check_and_handle_connection_recovery(user_id, display_name, current_state):
    """
    檢查並處理連接恢復情況（不主動發送訊息）
    
    Args:
        user_id: 用戶ID
        display_name: 用戶顯示名稱
        current_state: 當前用戶狀態
        
    Returns:
        tuple: (是否需要恢復, 恢復上下文信息)
    """
    if current_state.get("connection_failed", False):
        # 用戶之前遇到連接問題，現在重新連接了
        logger.info(f"檢測到用戶 {display_name} 連接恢復")
        
        # 清除連接失敗狀態
        current_state["connection_failed"] = False
        failed_message_type = current_state.get("failed_message_type")
        failed_message_content = current_state.get("failed_message_content")
        
        # 保存恢復上下文信息
        recovery_info = {
            "failed_message_type": failed_message_type,
            "failed_message_content": failed_message_content
        }
        
        # 清除失敗訊息記錄
        if "failed_message_type" in current_state:
            del current_state["failed_message_type"]
        if "failed_message_content" in current_state:
            del current_state["failed_message_content"]
        
        user_conversation_state[user_id] = current_state
        
        return True, recovery_info
    
    return False, None

# 只有在handler存在時才添加事件處理器
if handler:
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        user_id = event.source.user_id
        profile = get_user_profile(user_id)
        display_name = profile.display_name if profile else "未知用戶"
        text_message = event.message.text
        reply_token = event.reply_token
        current_time = datetime.now()

        logger.info(f"Received message from {display_name} ({user_id}): {text_message}")

        # 檢查是否為群組訊息
        is_group_message = False
        group_id = None
        if hasattr(event.source, "type") and event.source.type in ["group", "room"]:
            is_group_message = True
            group_id = event.source.group_id if event.source.type == "group" else event.source.room_id
            logger.info(f"這是一則群組訊息 (類型: {event.source.type}, ID: {group_id})")
            
        # 更新用戶狀態
        current_state = user_conversation_state.get(user_id, {})
        current_state["last_time"] = current_time
        
        # 檢查是否需要處理連接恢復（僅記錄狀態，不主動發送訊息）
        need_recovery, recovery_info = _check_and_handle_connection_recovery(user_id, display_name, current_state)
        if need_recovery:
            # 設置恢復狀態，在用戶下次發送訊息時會自動包含恢復說明
            current_state["show_recovery_message"] = True
            current_state["recovery_context"] = recovery_info
            user_conversation_state[user_id] = current_state
            logger.info(f"檢測到用戶 {display_name} 連接恢復，已設置恢復提示狀態")
        
        # 檢查是否包含觸發關鍵詞或用戶處於等待分析狀態
        waiting_for_analysis = current_state.get("waiting_for_analysis", False)
        
        # 檢查是否包含觸發關鍵詞或「土豆幫我查」
        trigger_keywords = [bot_trigger_keyword, "土豆幫我查"]
        has_trigger = any(keyword in text_message for keyword in trigger_keywords)
        
        # 檢查是否包含URL（自動觸發分析）
        import re
        url_pattern = re.compile(r'(https?://[^\s\u4e00-\u9fff，。！？；：]+|www\.[^\s\u4e00-\u9fff，。！？；：]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s\u4e00-\u9fff，。！？；：]*)?)')
        has_url = bool(url_pattern.search(text_message))
        
        if not has_trigger and not waiting_for_analysis and not has_url:
            logger.info(f"訊息不包含觸發關鍵詞，也不在等待分析狀態，也不包含URL，忽略此訊息")
            return

        # 移除觸發關鍵詞
        cleaned_message = text_message
        if has_trigger:
            # 移除所有可能的觸發關鍵詞
            for keyword in trigger_keywords:
                cleaned_message = cleaned_message.replace(keyword, "")
            cleaned_message = cleaned_message.strip()
            logger.info(f"移除觸發關鍵詞後的訊息: {cleaned_message}")

        # 檢查是否為空訊息
        if not cleaned_message.strip():
            # 獲取恢復訊息前綴（如果需要的話）
            recovery_prefix = _get_recovery_message_prefix(current_state, display_name)
            user_conversation_state[user_id] = current_state  # 更新狀態
              
            # 創建Flex Message歡迎訊息
            welcome_flex = flex_message_service.create_welcome_flex_message(display_name, recovery_prefix)
            
            line_bot_api.reply_message(reply_token, welcome_flex)
            
            # 保存互動記錄到Firebase
            firebase_manager.save_user_interaction(
                user_id, display_name, text_message, "顯示歡迎訊息",
                is_fraud_related=False
            )
            return

        # 處理遊戲觸發
        if is_game_trigger(cleaned_message):
            logger.info(f"檢測到防詐騙測試觸發: {cleaned_message}")
            flex_message, error_message = start_potato_game(user_id)
            
            if flex_message:
                line_bot_api.reply_message(reply_token, flex_message)
                # 保存互動記錄到Firebase
                firebase_manager.save_user_interaction(
                    user_id, display_name, text_message, "開始防詐騙測驗遊戲",
                    is_fraud_related=False
                )
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
                # 保存互動記錄到Firebase
                firebase_manager.save_user_interaction(
                    user_id, display_name, text_message, error_message,
                    is_fraud_related=False
                )
            return

        # 檢查詐騙類型列表查詢
        if any(keyword in cleaned_message for keyword in ["詐騙類型列表", "詐騙類型", "詐騙手法", "詐騙種類", "常見詐騙"]):
            logger.info(f"檢測到詐騙類型列表查詢: {cleaned_message}")
            
            try:
                from fraud_knowledge import load_fraud_tactics
                fraud_tactics = load_fraud_tactics()
                
                if fraud_tactics:
                    fraud_types_flex = create_fraud_types_flex_message(fraud_tactics, display_name)
                    line_bot_api.reply_message(reply_token, fraud_types_flex)
                    # 保存互動記錄到Firebase
                    firebase_manager.save_user_interaction(
                        user_id, display_name, text_message, "提供詐騙類型列表",
                        is_fraud_related=False
                    )
                else:
                    error_text = "抱歉，詐騙類型資料載入失敗。\n\n💡 您可以：\n• 直接傳送可疑訊息給我分析\n• 說「防詐騙測試」進行知識測驗"
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
                    # 保存互動記錄到Firebase
                    firebase_manager.save_user_interaction(
                        user_id, display_name, text_message, error_text,
                        is_fraud_related=False
                    )
            except Exception as e:
                logger.error(f"處理詐騙類型查詢時發生錯誤: {e}")
                error_text = "抱歉，詐騙類型查詢功能暫時無法使用。\n\n💡 您可以：\n• 直接傳送可疑訊息給我分析\n• 說「防詐騙測試」進行知識測驗"
                line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
                # 保存互動記錄到Firebase
                firebase_manager.save_user_interaction(
                    user_id, display_name, text_message, error_text,
                    is_fraud_related=False
                )
            return

        # 檢查特定詐騙類型查詢
        for fraud_type, info in fraud_types.items():
            if fraud_type in cleaned_message:
                logger.info(f"檢測到特定詐騙類型查詢: {fraud_type}")
                
                try:
                    page_match = re.search(r'第(\d+)頁', cleaned_message)
                    page = int(page_match.group(1)) if page_match else 1
                    
                    fraud_detail_flex = flex_message_service.create_fraud_detail_flex_message(
                        fraud_type, 
                        info, 
                        display_name, 
                        page
                    )
                    
                    line_bot_api.reply_message(reply_token, fraud_detail_flex)
                    # 保存互動記錄到Firebase
                    firebase_manager.save_user_interaction(
                        user_id, display_name, text_message, f"提供{fraud_type}詳細說明",
                        is_fraud_related=False
                    )
                    return
                except Exception as e:
                    logger.error(f"創建詐騙類型詳細信息Flex Message失敗: {e}")
                    
                    response_text = f"🚨 **{fraud_type}詳細說明** 🚨\n\n"
                    
                    if isinstance(info, dict) and "description" in info:
                        description = info["description"]
                        response_text += f"📋 **說明**：{description}\n\n"
                        
                        if "sop" in info and isinstance(info["sop"], list) and info["sop"]:
                            response_text += "💡 **防範建議**：\n"
                            for step in info["sop"]:
                                response_text += f"{step}\n"
                        else:
                            response_text += "💡 **防範建議**：\n"
                            response_text += "🛡️ 遇到任何要求提供個人資料或金錢的情況，請先暫停並諮詢家人\n"
                            response_text += "🔍 對於可疑訊息，可以傳給我幫您分析\n"
                            response_text += "📞 如有疑慮，請撥打165反詐騙專線\n"
                    else:
                        response_text += f"📋 **說明**：{str(info)}\n\n"
                        response_text += "💡 **防範建議**：\n"
                        response_text += "🛡️ 遇到任何要求提供個人資料或金錢的情況，請先暫停並諮詢家人\n"
                        response_text += "🔍 對於可疑訊息，可以傳給我幫您分析\n"
                        response_text += "📞 如有疑慮，請撥打165反詐騙專線\n"
                    
                    response_text += f"\n如果您收到疑似{fraud_type}的訊息，歡迎直接傳給我分析！"
                
                line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text))
                # 保存互動記錄到Firebase
                firebase_manager.save_user_interaction(
                    user_id, display_name, text_message, f"提供{fraud_type}詳細說明(文字版)",
                    is_fraud_related=False
                )
                return

        # 檢查圖片分析請求 (將這部分移到分析請求檢查前面)
        if "分析圖片" in cleaned_message or "檢查圖片" in cleaned_message or "請幫我分析圖片" in cleaned_message:
            image_analysis_prompt = f"📷 {display_name}，請點擊左下角鍵盤後上傳您想分析的圖片！\n\n" \
                                  f"我可以分析以下類型的圖片：\n" \
                                  f"🔍 可疑網站或購物平台截圖\n" \
                                  f"💬 可疑LINE對話或通訊軟體截圖\n" \
                                  f"📱 可疑簡訊或手機通知截圖\n" \
                                  f"📧 可疑電子郵件或釣魚郵件截圖\n" \
                                  f"💰 投資廣告、理財方案或兼職廣告截圖\n" \
                                  f"🎮 遊戲或APP內交易截圖\n" \
                                  f"🎯 其他任何可疑內容截圖\n\n" \
                                  f"⏱️ 請直接上傳圖片，分析需要約10-15秒，請耐心等待！"
            
            try:
                if v3_messaging_api:
                    from linebot.v3.messaging import TextMessage as V3TextMessage
                    from linebot.v3.messaging import ReplyMessageRequest
                    v3_messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[V3TextMessage(text=image_analysis_prompt)]
                       )
                    )
                    logger.info(f"已回覆圖片分析提示訊息: {user_id}")
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=image_analysis_prompt))
                    logger.info(f"已回覆圖片分析提示訊息 (舊版API): {user_id}")
                
                # 保存互動記錄到Firebase
                firebase_manager.save_user_interaction(
                    user_id, display_name, text_message, "提供圖片分析說明",
                    is_fraud_related=False
                )
            except LineBotApiError as e:
                logger.error(f"回覆圖片分析提示訊息時發生錯誤: {e}")
                if "Invalid reply token" in str(e):
                    try:
                        if v3_messaging_api:
                            from linebot.v3.messaging import TextMessage as V3TextMessage
                            from linebot.v3.messaging import PushMessageRequest
                            v3_messaging_api.push_message(
                                PushMessageRequest(
                                    to=user_id,
                                    messages=[V3TextMessage(text=image_analysis_prompt)]
                               )
                            )
                        else:
                            line_bot_api.push_message(user_id, TextSendMessage(text=image_analysis_prompt))
                        logger.info(f"圖片分析提示訊息使用push_message成功: {user_id}")
                        
                        # 保存互動記錄到Firebase
                        firebase_manager.save_user_interaction(
                            user_id, display_name, text_message, "提供圖片分析說明(push)",
                            is_fraud_related=False
                        )
                    except Exception as push_error:
                        logger.error(f"圖片分析提示訊息使用push_message也失敗: {push_error}")
            return

        # 檢查「我要查詐」請求
        if "我要查詐" in cleaned_message:
            logger.info(f"檢測到我要查詐請求: {cleaned_message}")
            
            current_state["waiting_for_analysis"] = True
            user_conversation_state[user_id] = current_state
            
            # 獲取恢復訊息前綴（如果需要的話）
            recovery_prefix = _get_recovery_message_prefix(current_state, display_name)
            user_conversation_state[user_id] = current_state  # 更新狀態
            
            prompt_message = f"{recovery_prefix}好的 {display_name}，我會智能分析您提供的內容！\n\n" \
                           f"請直接把您收到的可疑訊息、網址或截圖傳給我，我會自動判斷類型並進行分析：\n\n" \
                           f"💡 支援的內容類型：\n" \
                           f"• 📝 文字訊息（詐騙簡訊、可疑對話等）\n" \
                           f"• 🌐 網址連結（可疑網站、釣魚網址等）\n" \
                           f"• 📷 圖片截圖（直接上傳即可）\n" \
                           f"• 📧 郵件內容（可疑郵件、釣魚郵件等）\n\n" \
                           f"⏱️ 分析時間約10-15秒，請耐心等待！"
            
            try:
                if v3_messaging_api:
                    from linebot.v3.messaging import TextMessage as V3TextMessage
                    from linebot.v3.messaging import ReplyMessageRequest
                    v3_messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[V3TextMessage(text=prompt_message)]
                       )
                    )
                    logger.info(f"已回覆我要查詐提示訊息: {user_id}")
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=prompt_message))
                    logger.info(f"已回覆我要查詐提示訊息 (舊版API): {user_id}")
                
                # 保存互動記錄到Firebase
                firebase_manager.save_user_interaction(
                    user_id, display_name, text_message, "提供我要查詐說明",
                    is_fraud_related=False
                )
            except LineBotApiError as e:
                logger.error(f"回覆我要查詐提示訊息時發生錯誤: {e}")
                if "Invalid reply token" in str(e):
                    try:
                        if v3_messaging_api:
                            from linebot.v3.messaging import TextMessage as V3TextMessage
                            from linebot.v3.messaging import PushMessageRequest
                            v3_messaging_api.push_message(
                                PushMessageRequest(
                                    to=user_id,
                                    messages=[V3TextMessage(text=prompt_message)]
                               )
                            )
                        else:
                            line_bot_api.push_message(user_id, TextSendMessage(text=prompt_message))
                        logger.info(f"我要查詐提示訊息使用push_message成功: {user_id}")
                        
                        # 保存互動記錄到Firebase
                        firebase_manager.save_user_interaction(
                            user_id, display_name, text_message, "提供我要查詐說明(push)",
                            is_fraud_related=False
                        )
                    except Exception as push_error:
                        logger.error(f"我要查詐提示訊息使用push_message也失敗: {push_error}")
            return

        # 檢查分析請求但沒有內容（修改檢查邏輯，排除包含圖片相關的文本）
        analysis_request_keywords = ["請幫我分析這則訊息", "幫我分析訊息", "請分析這則訊息", "請幫我分析", "分析這則訊息"]
        is_analysis_request = any(keyword in cleaned_message for keyword in analysis_request_keywords) and "圖片" not in cleaned_message
        
        if is_analysis_request and (len(cleaned_message) < 20 or cleaned_message.rstrip("：:") in analysis_request_keywords):
            logger.info(f"檢測到分析請求但沒有提供具體內容: {cleaned_message}")
            
            current_state["waiting_for_analysis"] = True
            user_conversation_state[user_id] = current_state
            
            # 獲取恢復訊息前綴（如果需要的話）
            recovery_prefix = _get_recovery_message_prefix(current_state, display_name)
            user_conversation_state[user_id] = current_state  # 更新狀態
            
            prompt_message = f"{recovery_prefix}好的 {display_name}，我會幫您分析可疑訊息！\n\n" \
                           f"請直接把您收到的可疑訊息或網址傳給我，我會立即為您分析風險程度。\n\n" \
                           f"💡 您可以：\n" \
                           f"• 轉傳收到的可疑的文字訊息\n" \
                           f"• 了解最新具療效的醫學知識(如Onda超微波減脂、高壓氧艙)\n" \
                           f"• ⚠️FB、IG不易判別，請提供貼文內網址(或使用截圖)\n" \
                           f"• 貼上可疑的網址連結\n" \
                           f"• 描述您遇到的可疑情況"
            
            # 嘗試發送分析提示訊息，包含重連機制
            success = _send_message_with_retry(
                reply_token, prompt_message, user_id, display_name, 
                "提供分析請求說明", max_retries=2
            )
            
            if not success:
                # 如果所有重試都失敗，設置用戶狀態以便下次自動處理
                current_state["connection_failed"] = True
                current_state["failed_message_type"] = "analysis_prompt"
                current_state["failed_message_content"] = prompt_message
                user_conversation_state[user_id] = current_state
                logger.warning(f"無法發送分析提示訊息給用戶 {display_name}，已設置重試狀態")
            
            return

        # 判斷是否需要進行詐騙分析
        if waiting_for_analysis:
            logger.info(f"用戶處於等待分析狀態，強制執行詐騙分析: {cleaned_message}")
            current_state["waiting_for_analysis"] = False
            user_conversation_state[user_id] = current_state
            perform_fraud_analysis = True
        else:
            # 使用 should_perform_fraud_analysis 函數判斷是否應該進行詐騙分析
            perform_fraud_analysis = should_perform_fraud_analysis(cleaned_message, user_id)
            logger.info(f"決定是否執行詐騙分析: {perform_fraud_analysis}")
        
        # 根據判斷結果執行詐騙分析或閒聊模式
        if perform_fraud_analysis:
            # 檢查是否為產品真偽詢問
            product_name = extract_health_product(text_message, bot_trigger_keyword)
            
            # 檢查是否包含白名單關鍵詞，即使問句格式不標準也可以直接分析
            if not product_name and bot_trigger_keyword in text_message:
                for keyword in BEAUTY_HEALTH_WHITELIST:
                    if keyword in text_message:
                        logger.info(f"直接從白名單關鍵詞提取產品名: {keyword}")
                        product_name = keyword
                        break
            
            if product_name:
                logger.info(f"檢測到產品真偽詢問: {product_name}")
                
                # 檢查產品名稱是否足夠具體
                if len(product_name) >= 2:
                    logger.info(f"執行健康產品分析: {product_name}")
                    
                    analysis_result = analyze_health_product(product_name, display_name, user_id)
                    
                    if analysis_result and analysis_result.get("success", False):
                        analysis_data = analysis_result.get("result", {})
                        flex_message = create_analysis_flex_message(analysis_data, display_name, text_message, user_id)
                        
                        if flex_message:
                            try:
                                line_bot_api.reply_message(reply_token, flex_message)
                                logger.info(f"健康產品分析回覆成功: {user_id}")
                                
                                # 保存互動記錄到Firebase
                                firebase_manager.save_user_interaction(
                                    user_id, display_name, text_message, f"健康產品分析: {product_name}",
                                    is_fraud_related=True,
                                    fraud_type=analysis_data.get("fraud_type"),
                                    risk_level=analysis_data.get("risk_level")
                                )
                            except LineBotApiError as e:
                                logger.error(f"發送健康產品分析Flex訊息時發生錯誤: {e}")
                                if "Invalid reply token" in str(e):
                                    try:
                                        line_bot_api.push_message(user_id, flex_message)
                                        logger.info(f"健康產品分析回覆令牌無效，改用push_message成功: {user_id}")
                                        
                                        # 保存互動記錄到Firebase
                                        firebase_manager.save_user_interaction(
                                            user_id, display_name, text_message, f"健康產品分析: {product_name}",
                                            is_fraud_related=True,
                                            fraud_type=analysis_data.get("fraud_type"),
                                            risk_level=analysis_data.get("risk_level")
                                        )
                                    except Exception as push_error:
                                        logger.error(f"健康產品分析使用push_message也失敗: {push_error}")
                        else:
                            # 如果Flex消息創建失敗，發送基本文本消息
                            text_response = f"🔍 產品分析結果\n\n{analysis_data.get('explanation', '無法解析產品資訊')}\n\n{analysis_data.get('suggestions', '請諮詢專業醫療人員意見')}"
                            
                            try:
                                line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))
                                
                                # 保存互動記錄到Firebase
                                firebase_manager.save_user_interaction(
                                    user_id, display_name, text_message, f"健康產品分析(文字): {product_name}",
                                    is_fraud_related=True,
                                    fraud_type=analysis_data.get("fraud_type"),
                                    risk_level=analysis_data.get("risk_level")
                                )
                            except Exception as text_error:
                                logger.error(f"發送健康產品分析文本回覆失敗: {text_error}")
                        
                        return
                    else:
                        logger.warning(f"健康產品分析失敗: {product_name}")
                        # 如果健康產品分析失敗，會繼續執行一般詐騙分析
            
            # 執行詐騙分析
            logger.info(f"進入詐騙分析模式: {cleaned_message}")
            analysis_result = detect_fraud_with_chatgpt(cleaned_message, display_name, user_id)
            
            if analysis_result and analysis_result.get("success", False):
                analysis_data = analysis_result.get("result", {})
                
                # 檢查是否是圖片URL分析，如果是則使用預先創建的flex_message
                if analysis_result.get("flex_message"):
                    flex_message = analysis_result.get("flex_message")
                    logger.info("使用圖片URL分析的預先創建Flex Message")
                # 檢查是否是網域變形攻擊
                elif analysis_data.get("is_domain_spoofing", False):
                    spoofing_result = analysis_data.get("spoofing_result", {})
                    
                    unified_analysis_data = {
                        "risk_level": "極高",
                        "fraud_type": "網域偽裝攻擊",
                        "explanation": f"⚠️ 詐騙集團可能假冒此網域騙取您的信用卡或銀行帳戶個資，請務必小心！\n\n🔴 可疑網域: {spoofing_result.get('spoofed_domain', '未知')}\n🟢 正版網域: {spoofing_result.get('original_domain', '未知')}\n📝 說明: {spoofing_result.get('risk_explanation', '這是一個可疑的假冒網域')}",
                        "suggestions": "🚫 千萬不要點擊可疑網址或提供任何個人資料\n🔍 若需使用正版網站，請直接搜尋官方網站\n📞 可撥打165反詐騙專線確認或諮詢"
                    }
                    
                    flex_message = create_analysis_flex_message(unified_analysis_data, display_name, cleaned_message, user_id)
                else:
                    flex_message = create_analysis_flex_message(analysis_data, display_name, cleaned_message, user_id)
                
                # 發送Flex消息
                if flex_message:
                    try:
                        line_bot_api.reply_message(reply_token, flex_message)
                        logger.info(f"使用舊版API回覆分析成功: {user_id}")
                        
                        # 保存互動記錄到Firebase
                        firebase_manager.save_user_interaction(
                            user_id, display_name, text_message, "詐騙分析結果",
                            is_fraud_related=True,
                            fraud_type=analysis_data.get("fraud_type"),
                            risk_level=analysis_data.get("risk_level")
                        )
                    except LineBotApiError as e:
                        logger.error(f"發送Flex Message時發生錯誤: {e}")
                        if "Invalid reply token" in str(e):
                            try:
                                line_bot_api.push_message(user_id, flex_message)
                                logger.info(f"分析回覆令牌無效，改用push_message成功: {user_id}")
                                
                                # 保存互動記錄到Firebase
                                firebase_manager.save_user_interaction(
                                    user_id, display_name, text_message, "詐騙分析結果(push)",
                                    is_fraud_related=True,
                                    fraud_type=analysis_data.get("fraud_type"),
                                    risk_level=analysis_data.get("risk_level")
                                )
                            except Exception as push_error:
                                logger.error(f"分析使用push_message也失敗: {push_error}")
                    except Exception as e:
                        logger.error(f"發送Flex Message時發生未知錯誤: {e}")
                        # 發送基本文本消息
                        risk_level = analysis_data.get("risk_level", "不確定")
                        fraud_type = analysis_data.get("fraud_type", "未知")
                        explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
                        suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
                        
                        text_response = f"🔍 風險分析結果\n\n詐騙類型：{fraud_type}\n\n說明：{explanation}\n\n建議：{suggestions}"
                        
                        try:
                            line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))
                            
                            # 保存互動記錄到Firebase
                            firebase_manager.save_user_interaction(
                                user_id, display_name, text_message, "詐騙分析結果(文字)",
                                is_fraud_related=True,
                                fraud_type=fraud_type,
                                risk_level=risk_level
                            )
                        except Exception as text_error:
                            logger.error(f"發送文本回覆也失敗: {text_error}")
                else:
                    # 如果Flex消息創建失敗，發送基本文本消息
                    risk_level = analysis_data.get("risk_level", "不確定")
                    fraud_type = analysis_data.get("fraud_type", "未知")
                    explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
                    suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
                    
                    text_response = f"🔍 風險分析結果\n\n詐騙類型：{fraud_type}\n\n說明：{explanation}\n\n建議：{suggestions}"
                    
                    try:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))
                        
                        # 保存互動記錄到Firebase
                        firebase_manager.save_user_interaction(
                            user_id, display_name, text_message, "詐騙分析結果(備用文字)",
                            is_fraud_related=True,
                            fraud_type=fraud_type,
                            risk_level=risk_level
                        )
                    except Exception as text_error:
                        logger.error(f"發送文本回覆失敗: {text_error}")
            else:
                # 分析失敗的情況
                error_message = analysis_result.get("message", "分析失敗，請稍後再試") if analysis_result else "分析失敗，請稍後再試"
                try:
                    if v3_messaging_api:
                        from linebot.v3.messaging import TextMessage as V3TextMessage
                        from linebot.v3.messaging import ReplyMessageRequest
                        v3_messaging_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=reply_token,
                                messages=[V3TextMessage(text=error_message)]
                           )
                        )
                    else:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
                    
                    # 保存互動記錄到Firebase
                    firebase_manager.save_user_interaction(
                        user_id, display_name, text_message, "分析失敗",
                        is_fraud_related=False
                    )
                except Exception as error_send_error:
                    logger.error(f"發送錯誤訊息失敗: {error_send_error}")
        else:
            # 閒聊模式
            logger.info(f"進入一般聊天模式: {cleaned_message}")
            try:
                # 檢查用戶狀態是否需要提供防詐騙教學
                current_state = user_conversation_state.get(user_id, {})
                need_fraud_prevention_tips = current_state.get("need_fraud_prevention_tips", False)
                
                system_prompt = "你是一位名為「土豆」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。你的說話風格要：\n1. 非常簡單易懂，像鄰居朋友在聊天\n2. 用溫暖親切的語氣，不要太正式\n3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號\n4. 避免複雜的專業術語，用日常生活的話來解釋\n5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議\n6. 回應要簡短，不要太長篇大論\n\n詐騙類型分類指南：\n1. 購物詐騙/虛假廣告：涉及商品購買、減肥產品、美容產品、健康食品等宣稱效果誇大的商品\n2. 投資詐騙：涉及投資理財、股票、基金、加密貨幣等金融投資行為\n3. 假交友詐騙：涉及交友、約會、婚戀等感情互動\n4. 釣魚網站：偽造的網站，試圖騙取用戶的個人或金融資料\n5. 假冒身分詐騙：冒充親友、公司、政府機構等身份\n6. 中獎詐騙：宣稱用戶中獎或獲得意外獎勵\n7. 求職詐騙：涉及工作機會、求職、兼職等就業相關內容\n8. 網路釣魚：通過電子郵件、簡訊等方式誘導用戶點擊惡意鏈接\n9. 失效短網址風險：無法展開或驗證的短網址\n10. 其他詐騙：不屬於上述類別的其他詐騙形式\n\n若分析的是產品效果的真實性（如減肥、美容產品等），請歸類為「購物詐騙/虛假廣告」而非投資詐騙。"
                
                # 如果是防詐騙教學請求，添加特殊指令
                if need_fraud_prevention_tips:
                    logger.info(f"用戶 {user_id} 需要防詐騙教學回應")
                    
                    # 移除標記，避免重複觸發
                    current_state.pop("need_fraud_prevention_tips", None)
                    user_conversation_state[user_id] = current_state
                    
                    # 添加防詐騙教學專用提示詞
                    system_prompt += "\n\n用戶正在詢問如何防止被詐騙，這是一個重要的教育時刻。請提供以下內容：\n1. 3-5條簡單實用的防詐騙建議，每條前面加上適當的emoji\n2. 重點強調「停、看、聽、問」的防詐騙原則\n3. 針對常見詐騙類型（如假投資、假交友、釣魚網站）各提供1個防範要點\n4. 提醒用戶可以隨時詢問土豆關於詐騙分析和辨識\n\n回答應該結構清晰，語氣友善且堅定，內容要實用且易於記憶，總長度控制在300字以內。"
                
                chat_response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                     {"role": "system", "content": system_prompt},
                     {"role": "user", "content": cleaned_message}
                    ],
                    temperature=CHAT_TEMPERATURE,
                    max_tokens=CHAT_MAX_TOKENS
                )
                
                if chat_response and chat_response.choices:
                    chat_reply = chat_response.choices[0].message.content.strip()
                    
                    if random.random() < CHAT_TIP_PROBABILITY and not need_fraud_prevention_tips:
                        tips = get_anti_fraud_tips()
                        if tips:
                            random_tip = random.choice(tips)
                            chat_reply += f"\n\n💡 小提醒：{random_tip}"
                    
                    if len(chat_reply) > LINE_MESSAGE_SAFE_LENGTH:
                        chat_reply = chat_reply[:LINE_MESSAGE_SAFE_LENGTH] + "..."
                    
                    introduction = f"\n\n💫 我是您的專業防詐騙助手！經過全面測試，我能為您提供：\n🔍 文字或網站分析\n🎯 防詐騙知識測驗\n📚 詐騙案例查詢\n\n有任何可疑訊息都歡迎直接傳給我分析喔！"
                    
                    if user_id not in first_time_chatters and not need_fraud_prevention_tips:
                        first_time_chatters.add(user_id)
                        if len(chat_reply + introduction) <= LINE_MESSAGE_SAFE_LENGTH:
                            chat_reply += introduction
                    
                    try:
                        if v3_messaging_api:
                            from linebot.v3.messaging import TextMessage as V3TextMessage
                            from linebot.v3.messaging import ReplyMessageRequest
                            v3_messaging_api.reply_message(
                                ReplyMessageRequest(
                                    reply_token=reply_token,
                                    messages=[V3TextMessage(text=chat_reply)]
                               )
                            )
                            logger.info(f"使用v3 API回覆成功: {user_id}")
                        else:
                            line_bot_api.reply_message(reply_token, TextSendMessage(text=chat_reply))
                        
                        # 保存互動記錄到Firebase
                        firebase_manager.save_user_interaction(
                            user_id, display_name, text_message, chat_reply,
                            is_fraud_related=False
                        )
                    except LineBotApiError as e:
                        logger.error(f"使用LINE API回覆時發生錯誤: {e}")
                        if "Invalid reply token" in str(e):
                            try:
                                if v3_messaging_api:
                                    from linebot.v3.messaging import TextMessage as V3TextMessage
                                    from linebot.v3.messaging import PushMessageRequest
                                    
                                    v3_messaging_api.push_message(
                                        PushMessageRequest(
                                            to=user_id,
                                            messages=[V3TextMessage(text=chat_reply)]
                                       )
                                    )
                                else:
                                    line_bot_api.push_message(user_id, TextSendMessage(text=chat_reply))
                                logger.info(f"回覆令牌無效，改用push_message成功: {user_id}")
                                
                                # 保存互動記錄到Firebase
                                firebase_manager.save_user_interaction(
                                    user_id, display_name, text_message, chat_reply,
                                    is_fraud_related=False
                                )
                            except Exception as push_error:
                                logger.error(f"使用push_message也失敗: {push_error}")
                else:
                    fallback_message = "我現在有點忙，不過如果您有可疑訊息需要分析，我隨時可以幫忙喔！ 😊"
                    
                    try:
                        if v3_messaging_api:
                            from linebot.v3.messaging import TextMessage as V3TextMessage
                            from linebot.v3.messaging import ReplyMessageRequest
                            v3_messaging_api.reply_message(
                                ReplyMessageRequest(
                                    reply_token=reply_token,
                                    messages=[V3TextMessage(text=fallback_message)]
                               )
                            )
                        else:
                            line_bot_api.reply_message(reply_token, TextSendMessage(text=fallback_message))
                    except LineBotApiError as e:
                        logger.error(f"發送fallback訊息時發生LINE API錯誤: {e}")
                        if "Invalid reply token" in str(e):
                            try:
                                if v3_messaging_api:
                                    from linebot.v3.messaging import TextMessage as V3TextMessage
                                    from linebot.v3.messaging import PushMessageRequest
                                    
                                    v3_messaging_api.push_message(
                                        PushMessageRequest(
                                            to=user_id,
                                            messages=[V3TextMessage(text=fallback_message)]
                                       )
                                    )
                                else:
                                    line_bot_api.push_message(user_id, TextSendMessage(text=fallback_message))
                                logger.info(f"fallback訊息使用push_message成功: {user_id}")
                            except Exception as push_error:
                                logger.error(f"發送fallback訊息時使用push_message也失敗: {push_error}")
            
            except Exception as e:
                logger.exception(f"生成聊天回應時發生錯誤: {e}")
                fallback_message = "不好意思，我現在有點狀況，不過如果您有可疑訊息需要分析，我隨時可以幫忙！ 😊"
                
                try:
                    if v3_messaging_api:
                        from linebot.v3.messaging import TextMessage as V3TextMessage
                        from linebot.v3.messaging import ReplyMessageRequest
                        v3_messaging_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=reply_token,
                                messages=[V3TextMessage(text=fallback_message)]
                           )
                        )
                    else:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=fallback_message))
                except LineBotApiError as e:
                    logger.error(f"發送錯誤fallback訊息時發生LINE API錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        try:
                            if v3_messaging_api:
                                from linebot.v3.messaging import TextMessage as V3TextMessage
                                from linebot.v3.messaging import PushMessageRequest
                                
                                v3_messaging_api.push_message(
                                    PushMessageRequest(
                                        to=user_id,
                                        messages=[V3TextMessage(text=fallback_message)]
                                   )
                                )
                            else:
                                line_bot_api.push_message(user_id, TextSendMessage(text=fallback_message))
                            logger.info(f"錯誤fallback訊息使用push_message成功: {user_id}")
                        except Exception as push_error:
                            logger.error(f"發送錯誤fallback訊息時使用push_message也失敗: {push_error}")
            
    @handler.add(PostbackEvent)
    def handle_postback(event):
        """處理PostbackEvent（按鈕點擊事件）"""
        user_id = event.source.user_id
        postback_data = event.postback.data
        reply_token = event.reply_token
        
        profile = get_user_profile(user_id)
        display_name = profile.display_name if profile else "未知用戶"
        
        logger.info(f"Received postback from {display_name} ({user_id}): {postback_data}")
        
        try:
            if postback_data.startswith('action='):
                parts = postback_data.split('&')
                action_part = parts[0]
                action = action_part.split('=')[1]
                
                params = {}
                for part in parts[1:]:
                    if '=' in part:
                        key, value = part.split('=', 1)
                        params[key] = value
                
                logger.info(f"解析的動作: {action}, 參數: {params}")
                
                if action == 'start_potato_game':
                    flex_message, error_message = start_potato_game(user_id)
                    
                    if flex_message:
                        line_bot_api.reply_message(reply_token, flex_message)
                        # 保存互動記錄到Firebase
                        firebase_manager.save_user_interaction(
                            user_id, display_name, "點擊開始防詐騙測驗", "開始防詐騙測驗遊戲",
                            is_fraud_related=False
                        )
                    else:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
                        # 保存互動記錄到Firebase
                        firebase_manager.save_user_interaction(
                            user_id, display_name, "點擊開始防詐騙測驗", error_message,
                            is_fraud_related=False
                        )
                        
                elif action == 'potato_game_answer':
                    answer_index = int(params.get('answer', 0))
                    is_correct, result_flex = handle_potato_game_answer(user_id, answer_index)
                    
                    if is_correct is None and result_flex is None:
                        logger.info(f"忽略用戶 {user_id} 在冷卻時間內的重複點擊")
                        return
                    
                    line_bot_api.reply_message(reply_token, result_flex)
                    # 保存互動記錄到Firebase
                    firebase_manager.save_user_interaction(
                        user_id, display_name, f"防詐騙測驗答題: {answer_index}", 
                        f"答題結果: {'正確' if is_correct else '錯誤'}",
                        is_fraud_related=False
                    )
                    
                elif action == 'show_main_menu':
                    reply_text = f"嗨 {display_name}！我是土豆🥜\n你的反詐小助手，請提供你想查證的圖片、文字甚至是網址，我都能替你查證👍\n讓我用三大功能保護你！\n\n" \
                                f"🔍 我要查詐：\n智能分析文字、網址或截圖，立刻識破詐騙！\n" \
                                f"🎯 防詐騙測驗：\n玩問答提升你的防詐意識，輕鬆識破詐騙！\n" \
                                f"📚 詐騙案例：\n案例分析分享，了解9大詐騙類型。\n" \
                                f"💬 日常閒聊：\n陪你談天說地 甚至可以輸入：\n土豆 蔥爆牛肉怎麼做😂\n\n" \
                                f"💡 點擊下方按鈕，或直接告訴我你需要什麼！"
                    
                    # 使用 emoji 的 QuickReply 格式，簡潔美觀
                    quick_reply = QuickReply(items=[
                        QuickReplyButton(
                            action=MessageAction(
                                label="🔍 我要查詐", 
                                text=f"{bot_trigger_keyword} 我要查詐"
                            )
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="🎯 防詐騙測驗", 
                                text=f"{bot_trigger_keyword} 防詐騙測試"
                            )
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="📚 詐騙案例", 
                                text=f"{bot_trigger_keyword} 詐騙類型列表"
                            )
                        ),
                    ])
                    
                    mention_text = f"@{display_name} {reply_text}"
                    if len(mention_text) <= LINE_MESSAGE_MAX_LENGTH:
                        reply_text = mention_text
                    
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
                    
                        
                elif action == 'report_feedback':
                    feedback_message = f"📝 回報註記功能開發中！\n\n" \
                                     f"感謝 {display_name} 想要回報分析結果的意見。\n\n" \
                                     f"這個功能正在開發中，之後您可以：\n" \
                                     f"• 👍 標記分析結果是否準確\n" \
                                     f"• 📝 提供改善建議\n" \
                                     f"• 🚨 回報漏判或誤判\n\n" \
                                     f"敬請期待！🎉"
                    
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=feedback_message))
                    
                else:
                    logger.warning(f"未知的postback動作: {action}")
                    line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，我不太明白您想要做什麼，請重新嘗試！"))
            else:
                logger.warning(f"無法解析的postback數據: {postback_data}")
                line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，我不太明白您想要做什麼，請重新嘗試！"))
                
        except Exception as e:
            logger.exception(f"處理postback事件時發生錯誤: {e}")
            line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，處理您的請求時發生錯誤，請稍後再試！"))

    @handler.add(MessageEvent, message=ImageMessage)
    def handle_image_message(event):
        """處理圖片訊息"""
        try:
            user_id = event.source.user_id
            profile = get_user_profile(user_id)
            display_name = profile.display_name if profile else "未知用戶"
            reply_token = event.reply_token
            
            context_message = ""
            analysis_type = "GENERAL"
            
            # 檢查是否在「我要查詐」狀態
            current_state = user_conversation_state.get(user_id, {})
            waiting_for_analysis = current_state.get("waiting_for_analysis", False)
            
            if waiting_for_analysis:
                # 清除等待分析狀態
                current_state.pop("waiting_for_analysis", None)
                user_conversation_state[user_id] = current_state
                context_message = "用戶透過「我要查詐」功能上傳的圖片"
                analysis_type = "FRAUD_ANALYSIS"
                logger.info(f"檢測到我要查詐狀態下的圖片上傳: {user_id}")
            
            user_state = get_user_state(user_id)
            if user_state and "image_analysis_context" in user_state:
                context_message = user_state.get("image_analysis_context", "")
                analysis_type = user_state.get("image_analysis_type", "GENERAL")
                user_state.pop("image_analysis_context", None)
                user_state.pop("image_analysis_type", None)
                update_user_state(user_id, user_state)
            
            flex_message, raw_result = image_handler.handle_image_message(
                event.message.id, user_id, display_name, context_message, analysis_type
            )
            
            if flex_message:
                try:
                    line_bot_api.reply_message(reply_token, flex_message)
                    logger.info(f"使用舊版API回覆圖片分析成功: {user_id}")
                    
                    # 保存互動記錄到Firebase
                    # 處理raw_result現在是完整的分析結果字典
                    risk_level = None
                    fraud_type = None
                    is_fraud_related = False
                    
                    if raw_result:
                        if isinstance(raw_result, dict):
                            risk_level = raw_result.get("risk_level")
                            fraud_type = raw_result.get("fraud_type")
                            is_fraud_related = risk_level not in ["無風險", "低", "低風險"] if risk_level else False
                        elif isinstance(raw_result, str):
                            # 向後兼容：如果仍然是字串，設定預設值
                            logger.warning(f"raw_result是字串格式，可能是舊版本的返回值: {raw_result[:100]}...")
                            is_fraud_related = True  # 保守估計
                    
                    firebase_manager.save_user_interaction(
                        user_id, display_name, "上傳圖片分析", "圖片分析結果",
                        is_fraud_related=is_fraud_related,
                        fraud_type=fraud_type,
                        risk_level=risk_level
                    )
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆圖片分析時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        try:
                            line_bot_api.push_message(user_id, flex_message)
                            logger.info(f"圖片分析回覆令牌無效，改用push_message成功: {user_id}")
                            
                            # 保存互動記錄到Firebase
                            firebase_manager.save_user_interaction(
                                user_id, display_name, "上傳圖片分析", "圖片分析結果(push)",
                                is_fraud_related=is_fraud_related,
                                fraud_type=fraud_type,
                                risk_level=risk_level
                            )
                        except Exception as push_error:
                            logger.error(f"圖片分析使用push_message也失敗: {push_error}")
            else:
                error_message = "抱歉，無法分析此圖片，請稍後再試。"
                
                try:
                    line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text=error_message)
                    )
                    
                    # 保存互動記錄到Firebase
                    firebase_manager.save_user_interaction(
                        user_id, display_name, "上傳圖片分析", error_message,
                        is_fraud_related=False
                    )
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆圖片錯誤訊息時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        try:
                            line_bot_api.push_message(user_id, TextSendMessage(text=error_message))
                            logger.info(f"圖片錯誤訊息回覆令牌無效，改用push_message成功: {user_id}")
                            
                            # 保存互動記錄到Firebase
                            firebase_manager.save_user_interaction(
                                user_id, display_name, "上傳圖片分析", error_message,
                                is_fraud_related=False
                            )
                        except Exception as push_error:
                            logger.error(f"圖片錯誤訊息使用push_message也失敗: {push_error}")
                
        except LineBotApiError as e:
            logger.error(f"處理圖片訊息時發生LINE API錯誤: {e}")
        except Exception as e:
            logger.exception(f"處理圖片訊息時發生錯誤: {e}")
            try:
                error_message = "處理圖片時發生錯誤，請稍後再試。"
                
                try:
                    if v3_messaging_api:
                        from linebot.v3.messaging import TextMessage as V3TextMessage
                        from linebot.v3.messaging import ReplyMessageRequest
                        v3_messaging_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=event.reply_token,
                                messages=[V3TextMessage(text=error_message)]
                           )
                        )
                    else:
                        line_bot_api.reply_message(reply_token,
                            TextSendMessage(text=error_message)
                        )
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆最終錯誤訊息時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        try:
                            if v3_messaging_api:
                                from linebot.v3.messaging import TextMessage as V3TextMessage
                                from linebot.v3.messaging import PushMessageRequest
                                
                                v3_messaging_api.push_message(
                                    PushMessageRequest(
                                        to=user_id,
                                        messages=[V3TextMessage(text=error_message)]
                                   )
                                )
                            else:
                                line_bot_api.push_message(user_id, TextSendMessage(text=error_message))
                            logger.info(f"最終錯誤訊息回覆令牌無效，改用push_message成功: {user_id}")
                        except Exception as push_error:
                            logger.error(f"最終錯誤訊息使用push_message也失敗: {push_error}")
            except:
                pass

else:
    logger.warning("LINE Bot handler 未初始化，無法處理訊息事件")

def should_perform_fraud_analysis(message: str, user_id: str = None) -> bool:
    """判斷是否應該進行詐騙分析"""
    message_lower = message.lower().strip()
    
    # 訊息太短的情況下不做分析
    if len(message_lower) < 5:
        return False
    
    # 1. 檢查是否為醫美和健康相關白名單關鍵詞的查詢
    if bot_trigger_keyword in message:
        # 檢查是否包含醫美健康白名單關鍵詞
        for keyword in BEAUTY_HEALTH_WHITELIST:
            if keyword in message:
                logger.info(f"檢測到醫美健康白名單關鍵詞: {keyword}")
                return True
    
    # 2. 如果使用者明確請求分析訊息，則直接進行詐騙分析
    explicit_analysis_requests = [
        "請幫我分析這則訊息", "幫我分析訊息", "請分析這則訊息", "幫我分析", 
        "分析這則訊息", "分析一下這個", "檢查這個訊息", "看看這是不是詐騙"
    ]
    
    if any(request in message_lower for request in explicit_analysis_requests):
        logger.info(f"使用者明確要求分析訊息: {message_lower}")
        return True
    
    # 3. 檢查是否包含URL，如果包含則自動進行分析
    import re
    url_pattern = re.compile(r'(https?://[^\s\u4e00-\u9fff，。！？；：]+|www\.[^\s\u4e00-\u9fff，。！？；：]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s\u4e00-\u9fff，。！？；：]*)?)')
    if url_pattern.search(message):
        logger.info("檢測到URL，觸發詐騙分析")
        return True
    
    # 4. 檢查是否為健康產品或醫美療程的真偽詢問
    if bot_trigger_keyword in message:
        product_name = extract_health_product(message, bot_trigger_keyword)
        if product_name:
            logger.info(f"檢測到健康產品/醫美療程詢問: {product_name}")
            return True
    
    # 保留原有的簡單檢查，作為備用
    product_query_patterns = [
        r'.*?是真的嗎\??$',
        r'.*?真的假的\??$',
        r'.*?是騙人的嗎\??$',
        r'.*?有效果嗎\??$',
        r'.*?有用嗎\??$',
        r'.*?有效嗎\??$',
        r'.*?有人用過嗎\??$',
        r'.*?怎麼樣\??$',
        r'.*?好用嗎\??$',
        r'.*?推薦嗎\??$',
        r'.*?效果如何\??$',
        r'.*?有沒有用\??$',
        r'.*?有沒有效\??$',
        r'.*?好不好\??$',
        r'.*?真的能.*?嗎\??$',
        r'.*?會有效果嗎\??$',
        r'.*?真的會.*?嗎\??$'
    ]
    
    for pattern in product_query_patterns:
        if re.match(pattern, message_lower):
            logger.info(f"檢測到一般產品真偽詢問: {message_lower}")
            return True
    
    # 5. 排除明確是功能查詢或問候語的情況
    if any(keyword in message_lower for keyword in function_inquiry_keywords):
        return False
    
    # 6. 特殊處理"教我如何防詐騙"類請求
    anti_fraud_teaching_patterns = [
        "防止被詐騙", "避免被詐騙", "防詐騙", "防範詐騙", 
        "怎麼防詐騙", "怎樣防詐騙", "如何防詐騙", 
        "詐騙手法", "詐騙技巧", "詐騙方式", "詐騙案例",
        "防止受騙", "避免受騙", "教我防詐騙"
    ]
    
    teaching_keywords = ["教我", "告訴我", "如何", "怎麼", "怎樣", "方法"]
    
    # 檢查是否是防詐騙教學請求
    is_anti_fraud_teaching_request = (
        any(pattern in message_lower for pattern in anti_fraud_teaching_patterns) and
        any(keyword in message_lower for keyword in teaching_keywords)
    )
    
    if is_anti_fraud_teaching_request:
        logger.info(f"檢測到防詐騙教學請求: {message_lower}，將通過閒聊模式處理")
        
        # 使用用戶狀態，標記需要提供防詐騙教學回應
        if user_id:
            user_state = get_user_state(user_id)
            user_state["need_fraud_prevention_tips"] = True
            update_user_state(user_id, user_state)
            logger.info(f"已標記用戶 {user_id} 需要防詐騙教學回應")
        
        # 返回False使其進入閒聊模式，但帶有特殊標記
        return False
    
    # 7. 排除明確是閒聊的常見問題
    chat_patterns = [
        "怎麼做", "做法", "食譜", "教我", "告訴我", 
        "介紹", "推薦", "什麼是", "解釋", "說明",
        "好吃", "好玩", "有趣", "最近", "天氣",
        "你認為", "你覺得", "你喜歡", "笑話", "故事"
    ]
    
    if any(pattern in message_lower for pattern in chat_patterns):
        logger.info(f"檢測到閒聊模式關鍵詞: {message_lower}")
        return False
    
    # 8. 排除情感表達和問候語
    emotion_patterns = [
        "謝謝", "感謝", "開心", "難過", "生氣", "傷心", 
        "好玩", "有趣", "無聊", "好笑", "感動", "感覺",
        "喜歡", "愛", "恨", "討厭", "煩", "敏感"
    ]
    
    if any(pattern in message_lower for pattern in emotion_patterns):
        logger.info(f"檢測到情感表達關鍵詞: {message_lower}")
        return False
    
    greetings = ["你好", "哈囉", "嗨", "hi", "hello", "早安", "午安", "晚安", "再見", "謝謝", "感謝"]
    if any(greeting in message_lower for greeting in greetings) and len(message_lower) < 15:
        return False
    
    # 9. 排除特定功能關鍵詞
    if any(keyword in message_lower for keyword in ["詐騙類型", "詐騙手法", "詐騙種類", "常見詐騙"]):
        return False
    
    if is_game_trigger(message):
        return False
    
    if is_weather_related(message):
        return False
    
    # 10. 排除特定的誤判情況
    false_positives = {
        "兵免役是真的嗎": "可能是關於兵役的一般問題",
        "兵役免役是真的嗎": "可能是關於兵役的一般問題",
        "我可以免役嗎": "可能是關於兵役的一般問題",
        "免役是真的嗎": "可能是關於兵役的一般問題",
        "是真的嗎": "問句太廣泛，需要更多上下文",
        "這是真的嗎": "問句太廣泛，需要更多上下文"
    }
    
    for phrase, reason in false_positives.items():
        if phrase in message_lower:
            logger.info(f"排除誤判情況: '{phrase}' - {reason}")
            return False
    
    # 11. 詐騙關鍵詞分類，計算分數來判斷
    fraud_keywords = {
        # 高風險詐騙關鍵詞 (每個詞配2分)
        "高風險": [
            "詐騙", "被騙", "騙", "詐騙集團", "假冒", "詐騙手法", 
            "騙錢", "騙子", "釣魚", "釣魚網站", "假網站"
        ],
        
        # 金融相關詐騙關鍵詞 (每個詞配1分)
        "金融": [
            "投資", "賺錢", "兼職", "入金", "儲值", "銀行", "轉帳", 
            "匯款", "匯錢", "儲值", "比特幣", "虛擬貨幣", "錢包", 
            "出金", "股票", "期貨", "外匯", "退款", "贖回", "回報率",
            "利潤", "分潤"
        ],
        
        # 個資相關詐騙關鍵詞 (每個詞配1分)
        "個資": [
            "個資", "帳號", "密碼", "身份證", "信用卡", "卡號", "驗證碼", 
            "驗證", "銀行帳號", "金融卡", "網路銀行", "盜用", "洩漏", 
            "資料外洩"
        ],
        
        # 社交相關詐騙關鍵詞 (每個詞配1分)
        "社交": [
            "交友", "約會", "戀愛", "感情", "交往", "婚戀", "網戀",
            "一夜情", "相親", "愛情", "陌生人", "帥哥", "美女"
        ],
        
        # 緊急關鍵詞 (每個詞配1分)
        "緊急": [
            "急", "限時", "搶", "快", "緊急", "立即", "馬上", "趕快",
            "最後機會", "僅此一次", "倒數", "限量", "搶購"
        ]
    }
    
    # 計算詐騙風險得分
    fraud_score = 0
    matched_keywords = []
    
    # 高風險詐騙關鍵詞，每個詞配2分
    for keyword in fraud_keywords["高風險"]:
        if keyword in message_lower:
            fraud_score += 2
            matched_keywords.append(keyword)
    
    # 其他類別關鍵詞，每個詞配1分
    for category in ["金融", "個資", "社交", "緊急"]:
        for keyword in fraud_keywords[category]:
            if keyword in message_lower:
                fraud_score += 1
                matched_keywords.append(keyword)
    
    # 檢查是否有疑問詞，增加分數
    question_words = ["嗎", "呢", "吧", "?", "？", "如何", "怎麼", "怎樣"]
    if any(word in message_lower for word in question_words):
        fraud_score += 1
    
    # 若總分達到閾值（>=3分），則進行詐騙分析
    if fraud_score >= 3:
        logger.info(f"詐騙風險得分: {fraud_score}，匹配關鍵詞: {matched_keywords}，觸發詐騙分析")
        return True
    
    # 如果以上條件都不符合，則視為閒聊
    logger.info(f"詐騙風險得分: {fraud_score}，不足以觸發詐騙分析，視為閒聊")
    return False

# 初始化FlexMessageService
flex_message_service = FlexMessageService()

def extract_health_product(query, bot_trigger_keyword='土豆幫我看'):
    """
    從用戶查詢中提取健康產品或醫美療程名稱。
    
    參數:
        query (str): 用戶的查詢文本
        bot_trigger_keyword (str): 機器人的觸發關鍵詞，預設為'土豆'
        
    返回:
        str: 提取出的產品名稱，如果無法提取則返回None
    """
    # 先檢查是否包含白名單關鍵詞，直接返回第一個匹配的關鍵詞
    if bot_trigger_keyword in query:
        cleaned_query = query.replace(bot_trigger_keyword, "").strip()
        for keyword in BEAUTY_HEALTH_WHITELIST:
            if keyword in cleaned_query:
                logger.info(f"從白名單直接匹配到產品: {keyword}")
                return keyword
    
    # 終極版正則表達式 - 處理各種複雜的格式問題
    pattern = re.compile(
        r'.*?' + re.escape(bot_trigger_keyword) + r'.*?' +  # 匹配觸發詞及其前後文字
        r'(?:' +  # 開始匹配各種引導詞或前綴
        r'(?:請問|我想問|我問一下|想了解)?[,，~～\s]*' +  # 問句引導詞
        r'(?:你知道|知道|了解)?[,，~～\s]*' +  # 知識性引導詞
        r'(?:那個|這個)?[,，~～\s]*' +  # 指示詞
        r'(?:什麼|所謂)?[,，~～\s]*' +  # 疑問詞
        r')?' +
        r'(.*?)' +  # 捕獲組：產品/療程名稱
        r'(?:' +  # 開始匹配問句結尾
        r'是真的嗎|真的假的|是騙人的嗎|' +  # 真偽型問句
        r'有效果嗎|有用嗎|有效嗎|有人用過嗎|怎麼樣|好用嗎|推薦嗎|效果如何|有沒有用|有沒有效|好不好|' +  # 效果型問句
        r'真的能\S+嗎|會有效果嗎|真的會\S+嗎' +  # 能力型問句
        r')' +
        r'[啊呢吧呀哦]?[?？]?$'  # 語氣詞和問號
    )
    
    match = pattern.search(query)
    if not match:
        # 嘗試更寬鬆的模式：包含關鍵詞且有疑問詞
        loose_pattern = re.compile(
            r'.*?' + re.escape(bot_trigger_keyword) + r'.*?' +  # 匹配觸發詞
            r'.*?([\u4e00-\u9fff]{2,10})(?:.*?(?:嗎|呢|怎麼樣|如何|可以|安全|效果)[?？]?)?'  # 匹配2-10個中文字符後跟疑問詞
        )
        loose_match = loose_pattern.search(query)
        if loose_match:
            potential_product = loose_match.group(1)
            logger.info(f"使用寬鬆模式匹配到可能的產品: {potential_product}")
            return clean_product_name(potential_product)
        return None
    
    product_name = match.group(1)
    return clean_product_name(product_name)

def clean_product_name(text):
    """
    清理從用戶查詢中提取的產品名稱，移除不必要的前綴、後綴和干擾詞。
    
    參數:
        text (str): 提取的原始產品名稱文本
        
    返回:
        str: 清理後的產品名稱
    """
    if not text:
        return text
    
    # 保存原始文本用於特殊情況處理
    original_text = text
    
    # 移除開頭的標點和空白
    text = re.sub(r'^[,，~～、\s]+', '', text)
    
    # 移除請問、那個、什麼等前綴詞
    text = re.sub(r'^(?:請問|我想問|那個|這個|什麼|所謂)[,，~～、\s]*', '', text)
    
    # 移除「知道」、「了解」等詞
    text = re.sub(r'^(?:你知道|知道|了解)[,，~～、\s]*', '', text)
    
    # 移除「說」、「聽說」等引述詞及其前後內容
    text = re.sub(r'^.*?(?:說|聽說|告訴我)[,，~～、\s]*', '', text)
    text = re.sub(r'^的說[,，~～、\s]*', '', text)
    
    # 移除描述性片段
    text = re.sub(r'我昨天看到廣告有一款', '', text)
    text = re.sub(r'有人跟我說', '', text)
    
    # 移除額外的干擾字符
    text = text.replace('啊，', '').replace('~', '').replace('，', '')
    
    # 處理特殊情況
    if '知道' in text and '提升' in text:
        text = re.sub(r'知道', '', text)
    
    # 處理「我想了解」等前綴
    text = re.sub(r'^我想了解', '', text)
    
    # 處理長句中的產品名稱，通常取前面部分
    if '可以' in text and len(text) > 15:
        text = text.split('可以')[0].strip()
    
    # 處理「效果」、「功效」等詞
    text = re.sub(r'效果$', '', text)
    
    # 處理「在家裡自己用」等描述
    text = re.sub(r'在家裡自己用$', '', text)
    text = re.sub(r'在家裡自己用真的會$', '', text)
    
    # 處理「的效果」等後綴
    text = re.sub(r'的效果$', '', text)
    
    # 處理「這個」結尾
    text = re.sub(r'這個$', '', text)
    
    # 處理尾部「真的」等詞
    text = re.sub(r'真的$', '', text)
    
    # 處理超聲刀拉提的 -> 超聲刀拉提
    text = re.sub(r'的$', '', text)
    
    # 處理特殊情況 - 從上下文推斷產品名稱
    special_cases = {
        '能祛斑': '光電美容機',
        '微針滾輪在家裡自己用': '微針滾輪',
        '微針滾輪在家裡自己用真的會': '微針滾輪'
    }
    
    if text in special_cases:
        text = special_cases[text]
    
    # 如果文本非常短（例如 "能祛斑"），但原始文本包含更多信息，可能需要特殊處理
    if len(text) < 5 and len(original_text) > 15:
        # 嘗試提取完整產品名
        if "光電美容機" in original_text:
            text = "光電美容機"
        elif "電波拉皮" in original_text:
            text = "電波拉皮"
    
    # 如果仍然包含「那個什麼」，嘗試移除它
    text = re.sub(r'^那個什麼', '', text)
    
    # 處理「喝」開頭的情況
    if text.startswith('喝'):
        text = text[1:]
    
    # 處理長句中包含「可以改善」、「可以調理」等
    if '可以改善' in text:
        text = text.split('可以改善')[0].strip()
    elif '可以調理' in text:
        text = text.split('可以調理')[0].strip()
    
    # 如果仍然是未清理的長句，可能需要截取關鍵部分
    if len(text) > 30:
        # 嘗試只保留括號前的部分加括號內容
        if '(' in text and ')' in text:
            bracket_pos = text.find('(')
            text_before = text[:bracket_pos].strip()
            bracket_content = text[bracket_pos:]
            bracket_end = bracket_content.find(')') + 1
            if bracket_end > 0:
                bracket_content = bracket_content[:bracket_end]
            text = text_before + bracket_content
    
    # 最後的修飾和檢查
    text = text.strip()
    
    # 檢查是否有「有助」等詞
    if '有助' in text:
        text = text.split('有助')[0].strip()
    
    return text

def analyze_health_product(product_name, display_name="朋友", user_id=None):
    """專門分析健康產品、減肥產品和美容療程，提供客觀中立的分析"""
    try:
        # 拼接專門的分析提示詞
        analysis_prompt = f"""
        請以醫學專家和消費者保護專家的角度，對以下產品/療程進行客觀分析：
        ---
        {product_name}
        ---
        
        請根據科學證據和醫學研究，按照以下格式回答：
        
        產品/療程名稱：[產品或療程的完整名稱]
        原理描述：[用簡單易懂的語言解釋其聲稱的工作原理]
        科學依據：[是否有科學研究支持其效果，有哪些研究結果]
        潛在風險：[使用該產品或療程可能帶來的健康風險]
        替代方案：[更有科學依據的替代方法]
        消費建議：[給消費者的客觀建議]
        風險評級：[低風險/中風險/高風險] - 根據產品安全性和宣傳可信度
        
        請使用客觀中立的語氣，不要過度否定或肯定，而是基於已知的科學證據進行分析。
        如果資訊不足，請明確說明。
        """
        
        if not openai_client:
            logger.warning("OpenAI客戶端未初始化，使用模擬數據進行產品分析")
            
            # 使用模擬數據進行分析
            mock_analysis = f"""
            產品/療程名稱：{product_name}
            原理描述：該產品聲稱通過「超微波」技術直接作用於脂肪細胞，促進脂肪分解和代謝，從而達到減脂效果。
            科學依據：目前醫學文獻中尚無「超微波」這一特定技術的明確科學證據。大多數非侵入性減脂技術需要長期、系統性的臨床研究支持其有效性和安全性。
            潛在風險：可能存在皮膚刺激、暫時性不適等問題。過度宣傳效果可能導致消費者不切實際的期望，影響正常的健康管理計劃。
            替代方案：科學證據支持的減重方法包括均衡飲食、規律運動、生活方式改變，必要時在專業醫生指導下進行。
            消費建議：建議先諮詢專業醫師意見，不要僅依賴產品宣傳做決定。比較不同減重方法的成本效益，優先選擇有科學依據的方案。
            風險評級：中風險 - 主要風險來自可能的誇大宣傳和缺乏足夠科學證據，而非產品本身的安全性問題。
            """
            
            parsed_result = parse_health_product_analysis(mock_analysis, display_name)
            parsed_result["display_name"] = display_name
            
            return {
                "success": True,
                "message": "模擬分析完成",
                "result": parsed_result,
                "raw_result": mock_analysis
            }
        
        chat_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位專業醫學和消費者保護專家，負責對健康產品、減肥產品和美容療程進行客觀分析。你應該基於科學證據提供分析，語氣要中立客觀，不要過度否定或肯定。你的回應應該幫助消費者做出明智的選擇。"},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        if chat_response and chat_response.choices:
            analysis_result = chat_response.choices[0].message.content.strip()
            logger.info(f"健康產品分析結果: {analysis_result[:100]}...")
            
            # 解析結果
            parsed_result = parse_health_product_analysis(analysis_result, display_name)
            parsed_result["display_name"] = display_name
            
            return {
                "success": True,
                "message": "分析完成",
                "result": parsed_result,
                "raw_result": analysis_result
            }
        else:
            logger.error("OpenAI API 返回空結果")
            return {
                "success": False,
                "message": "分析失敗，請稍後再試"
            }
            
    except Exception as e:
        logger.exception(f"分析健康產品時發生錯誤: {e}")
        return {
            "success": False,
            "message": f"分析過程中發生錯誤: {str(e)}"
        }

def parse_health_product_analysis(analysis_result, display_name="朋友"):
    """解析健康產品分析結果"""
    try:
        lines = analysis_result.strip().split('\n')
        result = {
            "product_name": "未知產品",
            "principle": "無法解析產品原理。",
            "scientific_basis": "無法解析科學依據。",
            "potential_risks": "無法解析潛在風險。",
            "alternatives": "無法解析替代方案。",
            "consumer_advice": "無法解析消費建議。",
            "risk_level": "中風險",
        }
        
        # 將解析結果映射到我們的詐騙分析格式
        fraud_result = {
            "risk_level": "低(請依自身狀況評估)",
            "fraud_type": "健康諮詢",
            "explanation": "無法解析分析結果。",
            "suggestions": "建議謹慎處理。",
            "is_emerging": False,
            "display_name": display_name
        }
        
        for line in lines:
            line = line.strip()
            if "產品/療程名稱：" in line or "產品/療程名稱:" in line:
                result["product_name"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "原理描述：" in line or "原理描述:" in line:
                result["principle"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "科學依據：" in line or "科學依據:" in line:
                result["scientific_basis"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "潛在風險：" in line or "潛在風險:" in line:
                result["potential_risks"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "替代方案：" in line or "替代方案:" in line:
                result["alternatives"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "消費建議：" in line or "消費建議:" in line:
                result["consumer_advice"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "風險評級：" in line or "風險評級:" in line:
                # 忽略原始分析的風險等級，統一設為低風險
                pass
        
        # 構建精簡的解釋文本
        explanation = f"「{result['product_name']}」科學分析：\n\n"
        explanation += f"🔍 原理：{result['principle'][:120]}{'...' if len(result['principle']) > 120 else ''}\n\n"
        explanation += f"📊 科學依據：{result['scientific_basis'][:120]}{'...' if len(result['scientific_basis']) > 120 else ''}\n\n"
        explanation += f"⚠️ 潛在風險：{result['potential_risks'][:120]}{'...' if len(result['potential_risks']) > 120 else ''}"
        
        fraud_result["explanation"] = explanation
        
        # 構建精簡的建議文本
        suggestions = f"💡 替代方案：{result['alternatives'][:120]}{'...' if len(result['alternatives']) > 120 else ''}\n\n"
        suggestions += f"🛒 建議：{result['consumer_advice'][:120]}{'...' if len(result['consumer_advice']) > 120 else ''}"
        
        fraud_result["suggestions"] = suggestions
        
        return fraud_result
        
    except Exception as e:
        logger.error(f"解析健康產品分析結果時發生錯誤: {e}")
        return {
            "risk_level": "低(請依自身狀況評估)",
            "fraud_type": "健康諮詢",
            "explanation": "此產品/療程可能宣傳效果誇大，請謹慎考慮並諮詢專業醫療人員意見。",
            "suggestions": "🔍 購買前先查詢相關科學研究\n🛡️ 諮詢專業醫生或相關專家\n⚠️ 警惕誇大的宣傳和效果承諾",
            "is_emerging": False,
            "display_name": display_name
        }

def get_website_title(url):
    """獲取網站的標題"""
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
        })
        
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            # 先嘗試自動檢測的編碼
            content = response.text
            
            # 如果自動檢測的編碼有問題，嘗試手動指定常見的中文編碼
            if any(char in content for char in ['â', 'ã', 'Ã', 'å']):  # 常見的UTF-8亂碼特徵
                # 嘗試重新用UTF-8解碼
                try:
                    content = response.content.decode('utf-8')
                except UnicodeDecodeError:
                    # 如果UTF-8失敗，嘗試其他編碼
                    try:
                        content = response.content.decode('big5')
                    except UnicodeDecodeError:
                        try:
                            content = response.content.decode('gb2312')
                        except UnicodeDecodeError:
                            # 最後嘗試忽略錯誤
                            content = response.content.decode('utf-8', errors='ignore')
            
            # 只讀取前 4KB 來獲取標題，避免處理整個頁面
            content = content[:4096]
            
            # 使用正則表達式提取標題
            import re
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                # 清理標題中的多餘空白和換行
                title = re.sub(r'\s+', ' ', title)
                # 解碼HTML實體
                import html
                title = html.unescape(title)
                logger.info(f"成功獲取網站標題: {url} -> {title}")
                return title
        
        response.close()
        return None
        
    except Exception as e:
        logger.warning(f"獲取網站標題失敗: {url} - {e}")
        return None

def summarize_website_title(title, domain=None):
    """將網頁標題摘要為8-10字的簡潔說明"""
    if not title:
        return None
    
    try:
        # 移除常見的網站後綴
        title_clean = title
        suffixes_to_remove = [
            '- 聯合新聞網', '| 聯合新聞網', '- 中央社', '| 中央社', 
            '- 民視新聞網', '| 民視新聞網', '- 自由時報', '| 自由時報',
            '- ETtoday新聞雲', '| ETtoday新聞雲', '- 三立新聞網', '| 三立新聞網',
            '- PChome', '| PChome', '- Yahoo', '| Yahoo',
            '- Facebook', '| Facebook', '- LINE', '| LINE',
            '- Google', '| Google', '- YouTube', '| YouTube'
        ]
        
        for suffix in suffixes_to_remove:
            if suffix in title_clean:
                title_clean = title_clean.split(suffix)[0].strip()
        
        # 移除其他常見分隔符後的內容
        separators = [' | ', ' - ', ' │ ', ' ｜ ', ' — ']
        for sep in separators:
            if sep in title_clean:
                parts = title_clean.split(sep)
                # 取最長的部分作為主要內容
                title_clean = max(parts, key=len).strip()
        
        # 如果標題太長，智能截取
        if len(title_clean) > 12:
            # 嘗試找到合適的截取點
            cut_points = ['！', '？', '。', '：', ':', '，', ',']
            for i, char in enumerate(title_clean):
                if char in cut_points and 8 <= i <= 15:
                    title_clean = title_clean[:i+1]
                    break
            else:
                # 如果沒有找到合適的截取點，直接截取前12字
                if len(title_clean) > 12:
                    title_clean = title_clean[:10] + "..."
        
        # 針對不同類型的內容進行分類摘要
        if any(keyword in title_clean for keyword in ['加好友', 'Add Friend', '聊天']):
            return "LINE加好友頁面"
        elif any(keyword in title_clean for keyword in ['首頁', 'Home', '官網']):
            return f"{domain or '網站'}首頁" if domain else "網站首頁"
        elif any(keyword in title_clean for keyword in ['購物', '商品', '優惠', '特價']):
            if len(title_clean) > 10:
                return f"購物：{title_clean[:8]}..."
            return f"購物：{title_clean}"
        elif '!' in title_clean or '！' in title_clean:
            # 新聞標題通常有驚嘆號，提取關鍵信息
            if len(title_clean) > 12:
                # 找到第一個驚嘆號的位置
                exclamation_positions = []
                if '!' in title_clean:
                    exclamation_positions.append(title_clean.find('!'))
                if '！' in title_clean:
                    exclamation_positions.append(title_clean.find('！'))
                
                if exclamation_positions:
                    exclamation_pos = min([pos for pos in exclamation_positions if pos >= 0])
                    if exclamation_pos > 0:
                        key_part = title_clean[:exclamation_pos+1]
                        if len(key_part) <= 12:
                            return key_part
                        else:
                            return key_part[:10] + "..."
            return title_clean
        elif any(keyword in title_clean for keyword in ['新聞', '報導', '消息', '快訊']):
            if len(title_clean) > 10:
                return f"新聞：{title_clean[:8]}..."
            return f"新聞：{title_clean}"
        else:
            # 一般內容，保持簡潔
            return title_clean
            
    except Exception as e:
        logger.warning(f"摘要標題時發生錯誤: {e}")
        return title[:10] + "..." if len(title) > 10 else title

def analyze_credit_card_3d_verification(message, display_name="朋友"):
    """
    智能分析信用卡3D驗證簡訊，根據金額、幣別、卡號末四碼等因素判定風險等級
    
    Args:
        message: 簡訊內容
        display_name: 用戶顯示名稱
        
    Returns:
        dict: 分析結果
    """
    import re
    
    # 檢測是否為3D驗證簡訊的關鍵詞
    verification_keywords = [
        '驗證', '認證', '確認', '交易', '刷卡', '消費', '網路交易', 
        '信用卡', '末四碼', '驗證碼', '認證碼', '3D', 'OTP'
    ]
    
    # 檢查是否包含3D驗證相關關鍵詞
    if not any(keyword in message for keyword in verification_keywords):
        return None
    
    # 提取金額信息
    amount_patterns = [
        r'([A-Z]{3})\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # USD$1,200
        r'新臺幣([A-Z]{3})\$(\d{1,3}(?:,\d{3})*)',  # 新臺幣TWD$1,200
        r'交易新臺幣([A-Z]{3})\$(\d{1,3}(?:,\d{3})*)',  # 交易新臺幣TWD$1,200
        r'([A-Z]{3})(\d{1,3}(?:,\d{3})*)',  # TWD1200
        r'NT\$(\d{1,3}(?:,\d{3})*)',  # NT$1200
        r'新台幣\s*(\d{1,3}(?:,\d{3})*)',  # 新台幣1200
        r'(\d{1,3}(?:,\d{3})*)\s*元',  # 1200元
    ]
    
    currency = "TWD"  # 預設台幣
    amount = 0
    
    for pattern in amount_patterns:
        matches = re.findall(pattern, message)
        if matches:
            if isinstance(matches[0], tuple) and len(matches[0]) == 2:
                # 有幣別的情況
                currency, amount_str = matches[0]
                amount = int(amount_str.replace(',', ''))
                break
            elif isinstance(matches[0], str):
                # 只有金額的情況
                amount = int(matches[0].replace(',', ''))
                break
    
    # 提取卡號末四碼 - 改進正則表達式
    card_last_four_patterns = [
        r'末四碼[：:\s]*(\d{4})',  # 末四碼 8219
        r'卡末四碼[：:\s]*(\d{4})',  # 卡末四碼 8219
        r'信用卡[（(]末四碼[：:\s]*(\d{4})[）)]',  # 信用卡(末四碼:8219)
    ]
    
    card_last_four = None
    for pattern in card_last_four_patterns:
        matches = re.findall(pattern, message)
        if matches:
            card_last_four = matches[0]
            break
    
    # 風險評估邏輯 - 純粹基於交易特性
    risk_level = "低風險"
    fraud_type = "信用卡3D驗證簡訊"
    explanation = ""
    suggestions = []
    
    # 1. 境外交易（非台幣）- 高風險
    if currency and currency.upper() not in ['TWD', 'NT']:
        risk_level = "高風險"
        fraud_type = "境外信用卡交易驗證"
        explanation = f"⚠️ 這是一筆境外信用卡交易驗證簡訊。\n\n"
        explanation += f"💳 交易金額：{currency.upper()}{amount:,}\n"
        if card_last_four:
            explanation += f"🔢 卡號末四碼：{card_last_four}\n"
        explanation += f"\n🌍 境外交易風險相對較高，詐騙集團常利用海外支付平台進行詐騙。"
        
        suggestions = [
            "🔍 仔細核對刷卡項目、金額與幣別是否正確",
            "⚠️ 確認是否為您本人進行的海外交易",
            "🛡️ 如非本人交易，立即聯繫信用卡客服停卡",
            "💡 海外交易詐騙風險較高，請特別謹慎",
            "📞 有疑慮時可撥打信用卡背面客服電話確認"
        ]
    
    # 2. 高金額交易（>3000台幣或等值） - 中風險
    elif amount > 3000:
        risk_level = "中風險"
        fraud_type = "高金額信用卡交易驗證"
        explanation = f"💳 這是一筆金額較高的信用卡交易驗證。\n\n"
        explanation += f"💰 交易金額：{currency}${amount:,}\n"
        if card_last_four:
            explanation += f"🔢 卡號末四碼：{card_last_four}\n"
        explanation += f"\n⚠️ 由於單筆金額較高，建議您仔細確認交易內容。"
        
        suggestions = [
            "🔍 確認刷卡項目與金額是否符合您的消費",
            "💡 高金額交易請特別謹慎核對",
            "✅ 確認是本人交易後再輸入驗證碼",
            "🛡️ 如有疑慮，可先聯繫商家或信用卡客服",
            "⚠️ 不要在可疑網站或陌生連結輸入驗證碼"
        ]
    
    # 3. 一般小額台幣交易 - 低風險
    else:
        risk_level = "低風險"
        fraud_type = "一般信用卡3D驗證"
        explanation = f"✅ 這看起來是一般的信用卡3D驗證簡訊。\n\n"
        explanation += f"💰 交易金額：NT${amount:,}\n"
        if card_last_four:
            explanation += f"🔢 卡號末四碼：{card_last_four}\n"
        explanation += f"\n💡 金額不高且為台幣交易，風險相對較低。"
        
        suggestions = [
            "✅ 確認是您本人的交易後可安心輸入驗證碼",
            "🔍 養成習慣：每次都確認交易金額與商家",
            "🛡️ 驗證碼只能在正確的交易頁面輸入",
            "💡 如有任何疑慮，可聯繫信用卡客服確認",
            "⚠️ 絕不要將驗證碼提供給任何人（包括客服）"
        ]
    
    # 添加通用安全提醒
    explanation += f"\n\n🔐 重要提醒：3D驗證碼是您的交易密碼，只能在銀行或商家的安全頁面輸入，絕不要透過電話、簡訊或其他方式提供給任何人。"
    
    return {
        "success": True,
        "message": "信用卡3D驗證分析完成",
        "result": {
            "risk_level": risk_level,
            "fraud_type": fraud_type,
            "explanation": explanation,
            "suggestions": suggestions,
            "is_emerging": False,
            "display_name": display_name,
            "transaction_amount": amount,
            "currency": currency,
            "card_last_four": card_last_four,
            "analysis_type": "信用卡3D驗證分析"
        }
    }

def is_credit_card_3d_verification(message):
    """
    檢測訊息是否為信用卡3D驗證簡訊
    
    Args:
        message: 訊息內容
        
    Returns:
        bool: 是否為3D驗證簡訊
    """
    # 3D驗證簡訊的特徵關鍵詞組合
    verification_indicators = [
        ('末四碼', '驗證'),
        ('末四碼', '認證'),
        ('信用卡', '驗證碼'),
        ('網路交易', '驗證'),
        ('刷卡', '驗證碼'),
        ('交易', '認證碼'),
        ('消費', '驗證'),
        ('3D', '驗證'),
        ('OTP', '驗證')
    ]
    
    # 檢查是否包含金額格式
    amount_patterns = [
        r'([A-Z]{3})\$?\d{1,3}(?:,\d{3})*',  # USD$1,200
        r'NT\$?\d{1,3}(?:,\d{3})*',  # NT$1200
        r'新台幣\s*\d{1,3}(?:,\d{3})*',  # 新台幣1200
        r'\d{1,3}(?:,\d{3})*\s*元',  # 1200元
    ]
    
    has_amount = any(re.search(pattern, message) for pattern in amount_patterns)
    has_verification_keywords = any(
        all(keyword in message for keyword in keywords) 
        for keywords in verification_indicators
    )
    
    return has_amount and has_verification_keywords

def analyze_email_fraud(email_content, sender_email=None, display_name="朋友"):
    """
    使用ChatGPT智能分析郵件詐騙，根據內容、發信者、敏感詞彙等進行綜合判斷
    
    Args:
        email_content: 郵件內容
        sender_email: 發信者郵件地址（可選）
        display_name: 用戶顯示名稱
        
    Returns:
        dict: 分析結果
    """
    import re
    import urllib.parse
    
    # 如果沒有OpenAI客戶端，使用基礎規則分析
    if not openai_client:
        logger.warning("OpenAI客戶端未初始化，使用基礎規則分析")
        return analyze_email_fraud_basic(email_content, sender_email, display_name)
    
    # 準備分析提示
    analysis_prompt = f"""
請分析以下內容是否為詐騙郵件。請特別注意以下幾個關鍵點：

**重要：首先判斷這是否真的是郵件內容**
- 如果內容看起來像是 LINE 聊天對話、客服自動回覆、或正常的服務查詢對話，請判定為「低風險」
- 如果內容包含「感謝加入好友」、「整新機查詢」、「官方帳號」、「自動回覆」等字眼，很可能是正常的客服對話

1. **郵件內容分析**：
   - 檢查是否包含繳費、付款、費用等敏感詞彙
   - 識別郵件中聲稱的發信機構（如台電、遠通電收、銀行等）
   - 分析語言表達是否專業、是否有錯字或奇怪用詞
   - **特別注意**：正常的服務查詢或客服對話不應判定為詐騙

2. **發信者驗證**：
   - 發信者郵件地址：{sender_email if sender_email else '未提供'}
   - 如果有發信者地址，請檢查網域是否與聲稱的機構匹配
   - 台灣主要機構的正確網域：
     * 遠通電收：fetc.net.tw
     * 台灣電力公司：taipower.com.tw
     * 中華電信：cht.com.tw
     * 台灣自來水公司：water.gov.tw
     * 政府機構：通常以 .gov.tw 結尾

3. **詐騙手法識別**：
   - 網域偽裝攻擊（使用相似但不同的網域）
   - 緊急性語言（立即、馬上、限時等）
   - 威脅性內容（停用服務、法律責任等）

**重要風險等級判定規則**：
- 如果發信網域與聲稱機構不符（domain_mismatch=true），必須判定為「極高風險」
- 如果包含繳費要求且發信者身份可疑，應判定為「高風險」或「極高風險」
- 只有在網域完全匹配且內容正常時，才可判定為「低風險」或「中風險」

郵件內容：
{email_content}

請以純JSON格式回應，不要包含任何其他文字或markdown標記，只返回JSON對象：

{{
    "risk_level": "極高風險/高風險/中風險/低風險",
    "fraud_type": "詐騙類型描述",
    "explanation": "用40字以內單句解釋為什麼這個郵件可疑或安全",
    "suggestions": ["建議1", "建議2", "建議3"],
    "is_emerging": false,
    "analysis_details": {{
        "sender_domain": "發信者網域",
        "claimed_organization": "聲稱的機構",
        "expected_domain": "該機構的正確網域",
        "domain_mismatch": true/false,
        "sensitive_keywords": ["發現的敏感詞彙"],
        "threat_indicators": ["威脅性指標"]
    }}
}}

重要提醒：
1. 只返回JSON對象，不要加上任何說明文字
2. 如果analysis_details中domain_mismatch為true，risk_level必須是「極高風險」
3. 確保所有字串都用雙引號包圍
"""

    try:
        logger.info(f"使用ChatGPT分析郵件詐騙內容")
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一個專業的郵件詐騙分析專家，專門識別各種郵件詐騙手法，特別是台灣地區的詐騙模式。"},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        
        analysis_result = response.choices[0].message.content.strip()
        logger.info(f"ChatGPT郵件分析完成，結果長度: {len(analysis_result)}")
        
        # 解析JSON回應
        import json
        import re
        
        # 嘗試提取JSON內容
        def extract_json_from_response(text):
            """從回應中提取JSON內容"""
            # 移除markdown代碼塊標記
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)
            
            # 尋找JSON對象
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json_match.group(0)
            
            return text.strip()
        
        try:
            # 先嘗試直接解析
            try:
                result_data = json.loads(analysis_result)
            except json.JSONDecodeError:
                # 如果失敗，嘗試提取JSON部分
                extracted_json = extract_json_from_response(analysis_result)
                logger.info(f"提取的JSON內容: {extracted_json[:200]}...")
                result_data = json.loads(extracted_json)
            
            # 確保必要欄位存在
            if "risk_level" not in result_data:
                result_data["risk_level"] = "中風險"
            if "fraud_type" not in result_data:
                result_data["fraud_type"] = "郵件內容分析"
            if "explanation" not in result_data:
                result_data["explanation"] = analysis_result
            if "suggestions" not in result_data:
                result_data["suggestions"] = ["建議謹慎處理此郵件", "如有疑慮請聯繫相關機構確認"]
            
            # 添加額外資訊
            result_data["display_name"] = display_name
            result_data["analysis_type"] = "ChatGPT郵件詐騙分析"
            result_data["sender_email"] = sender_email
            
            return {
                "success": True,
                "message": "ChatGPT郵件詐騙分析完成",
                "result": result_data,
                "raw_result": analysis_result
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"ChatGPT回應不是有效的JSON格式: {e}，原始回應: {analysis_result[:200]}...")
            return {
                "success": True,
                "message": "ChatGPT郵件詐騙分析完成",
                "result": {
                    "risk_level": "中風險",
                    "fraud_type": "郵件內容分析",
                    "explanation": analysis_result,
                    "suggestions": [
                        "建議謹慎處理此郵件",
                        "如有疑慮請聯繫相關機構確認",
                        "不要點擊郵件中的可疑連結",
                        "不要提供個人敏感資料"
                    ],
                    "is_emerging": False,
                    "display_name": display_name,
                    "analysis_type": "ChatGPT郵件詐騙分析",
                    "sender_email": sender_email
                },
                "raw_result": analysis_result
            }
            
    except Exception as e:
        logger.error(f"ChatGPT郵件分析時發生錯誤: {e}")
        # 降級到基礎規則分析
        return analyze_email_fraud_basic(email_content, sender_email, display_name)


def analyze_email_fraud_basic(email_content, sender_email=None, display_name="朋友"):
    """
    基礎規則的郵件詐騙分析（當ChatGPT不可用時使用）
    """
    import re
    import urllib.parse
    
    # 1. 檢查郵件內容是否包含URL
    # 更精確的URL檢測，避免誤判郵件標題等內容
    url_patterns = [
        r'https?://[^\s<>"{}|\\^`\[\]]+',  # http/https URL
        r'(?:^|\s)(www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?)',  # www開頭的URL
    ]
    
    found_urls = []
    for pattern in url_patterns:
        matches = re.findall(pattern, email_content)
        if isinstance(matches[0], tuple) if matches else False:
            # 如果是tuple，取第一個元素（捕獲組）
            found_urls.extend([match[0] if isinstance(match, tuple) else match for match in matches])
        else:
            found_urls.extend(matches)
    
    # 過濾掉明顯不是URL的內容
    filtered_urls = []
    for url in found_urls:
        # 排除郵件地址
        if '@' in url and not url.startswith(('http://', 'https://', 'www.')):
            continue
        # 排除過短的內容
        if len(url) < 5:
            continue
        # 排除明顯的郵件標題格式和非URL內容
        if (url.upper() in ['RTK.UI', 'FETC.SERVICE', 'TELENET.BE'] or 
            '.' not in url or 
            len(url.split('.')) < 2 or
            not any(char.isalpha() for char in url.split('.')[-1])):
            continue
        filtered_urls.append(url)
    
    # 移除重複的URL
    found_urls = list(set(filtered_urls))
    
    # 如果有URL，優先分析URL
    if found_urls:
        for url in found_urls:
            # 確保URL有協議
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = 'https://' + url
                else:
                    url = 'https://' + url
            
            # 檢查是否為短網址
            short_url_domains = [
                'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly', 
                'is.gd', 'buff.ly', 'adf.ly', 'short.link', 'tiny.cc',
                'reurl.cc', 'pse.is', 'lihi.io', 'lin.ee'
            ]
            
            domain = urllib.parse.urlparse(url).netloc.lower()
            if any(short_domain in domain for short_domain in short_url_domains):
                # 短網址處理
                expanded_url = expand_short_url(url)
                if expanded_url and expanded_url != url:
                    # 分析展開後的URL - 簡化版本，不依賴OpenAI
                    return {
                        "success": True,
                        "message": "郵件詐騙分析完成",
                        "result": {
                            "risk_level": "中風險",
                            "fraud_type": "郵件包含短網址",
                            "explanation": f"郵件中包含短網址，已展開為：{expanded_url}\n\n建議您謹慎處理，確認網址的安全性。",
                            "suggestions": [
                                "不要立即點擊郵件中的連結",
                                "確認發信者身份是否可信",
                                "可以複製網址到瀏覽器手動輸入",
                                "如有疑慮請聯繫相關機構確認"
                            ],
                            "is_emerging": False,
                            "display_name": display_name,
                            "analysis_type": "郵件詐騙分析",
                            "original_url": url,
                            "expanded_url": expanded_url
                        }
                    }
                else:
                    return {
                        "success": True,
                        "message": "郵件詐騙分析完成",
                        "result": {
                            "risk_level": "高風險",
                            "fraud_type": "可疑短網址郵件",
                            "explanation": f"郵件中包含無法展開的短網址：{url}",
                            "suggestions": ["不要點擊郵件中的可疑連結", "直接聯繫官方客服確認"],
                            "is_emerging": False,
                            "display_name": display_name,
                            "analysis_type": "郵件詐騙分析"
                        }
                    }
            else:
                # 一般URL - 簡化版本，不依賴OpenAI
                return {
                    "success": True,
                    "message": "郵件詐騙分析完成",
                    "result": {
                        "risk_level": "中風險",
                        "fraud_type": "郵件包含網址連結",
                        "explanation": f"郵件中包含網址：{url}\n\n建議您謹慎處理，確認網址的安全性和發信者身份。",
                        "suggestions": [
                            "不要立即點擊郵件中的連結",
                            "確認發信者身份是否可信",
                            "檢查網址是否為官方網站",
                            "如有疑慮請聯繫相關機構確認"
                        ],
                        "is_emerging": False,
                        "display_name": display_name,
                        "analysis_type": "郵件詐騙分析",
                        "url": url
                    }
                }
    
    # 2. 沒有URL的情況，檢查敏感文字
    sensitive_keywords = [
        '繳費', '付款', '費用', '暫停使用', '銀行往來', '帳單', '欠費', 
        '催繳', '逾期', '停用', '恢復服務', '立即繳費', '點擊繳費',
        '信用卡', '轉帳', '匯款', '驗證', '更新資料', '確認身分'
    ]
    
    has_sensitive_content = any(keyword in email_content for keyword in sensitive_keywords)
    
    if not has_sensitive_content:
        return {
            "success": True,
            "message": "郵件詐騙分析完成",
            "result": {
                "risk_level": "低風險",
                "fraud_type": "一般郵件",
                "explanation": "郵件內容未發現明顯的詐騙特徵或敏感詞彙。",
                "suggestions": ["保持警覺", "如有疑慮可聯繫相關機構確認"],
                "is_emerging": False,
                "display_name": display_name,
                "analysis_type": "郵件詐騙分析"
            }
        }
    
    # 3. 有敏感文字，尋找發信來源
    legitimate_organizations = {
        '台灣電力公司': 'taipower.com.tw',
        '台電': 'taipower.com.tw',
        '台灣自來水公司': 'water.gov.tw',
        '自來水公司': 'water.gov.tw',
        '台北自來水事業處': 'water.taipei.gov.tw',
        '台北自來水': 'water.taipei.gov.tw',
        '欣欣天然氣': 'sinshin.com.tw',
        '遠通電收': 'fetc.net.tw',
        '中華電信': 'cht.com.tw',
        '台灣大哥大': 'taiwanmobile.com',
        '遠傳電信': 'fetnet.net',
        '亞太電信': 'aptg.com.tw',
        '台灣之星': 'tstartel.com',
        '國稅局': 'gov.tw',
        '健保署': 'nhi.gov.tw',
        '勞保局': 'bli.gov.tw'
    }
    
    # 在郵件內容中尋找機構名稱
    found_organization = None
    expected_domain = None
    
    for org_name, domain in legitimate_organizations.items():
        if org_name in email_content:
            found_organization = org_name
            expected_domain = domain
            break
    
    if not found_organization:
        # 沒找到合法機構但有敏感詞彙
        return {
            "success": True,
            "message": "郵件詐騙分析完成",
            "result": {
                "risk_level": "中風險",
                "fraud_type": "可疑繳費郵件",
                "explanation": f"郵件包含繳費相關敏感詞彙，但無法確認發信機構身分。發現的敏感詞彙包括：{', '.join([kw for kw in sensitive_keywords if kw in email_content])}",
                "suggestions": [
                    "不要點擊郵件中的任何連結",
                    "直接聯繫相關機構官方客服確認",
                    "透過官方網站或APP查詢帳單狀態",
                    "如有疑慮可撥打165反詐騙專線"
                ],
                "is_emerging": False,
                "display_name": display_name,
                "analysis_type": "郵件詐騙分析"
            }
        }
    
    # 4. 找到合法機構，檢查發信者網域
    if sender_email:
        sender_domain = sender_email.split('@')[-1].lower() if '@' in sender_email else None
        
        if sender_domain and expected_domain:
            if expected_domain.lower() in sender_domain or sender_domain == expected_domain.lower():
                # 網域匹配，可能是合法郵件
                return {
                    "success": True,
                    "message": "郵件詐騙分析完成",
                    "result": {
                        "risk_level": "低風險",
                        "fraud_type": f"疑似{found_organization}官方郵件",
                        "explanation": f"郵件聲稱來自{found_organization}，發信網域({sender_domain})與預期網域({expected_domain})相符。",
                        "suggestions": [
                            "雖然網域相符，仍建議透過官方管道確認",
                            "不要在郵件連結中輸入敏感資料",
                            "可直接前往官方網站查詢帳單"
                        ],
                        "is_emerging": False,
                        "display_name": display_name,
                        "analysis_type": "郵件詐騙分析"
                    }
                }
            else:
                # 網域不匹配，可能是詐騙
                return {
                    "success": True,
                    "message": "郵件詐騙分析完成",
                    "result": {
                        "risk_level": "極高風險",
                        "fraud_type": f"假冒{found_organization}的詐騙郵件",
                        "explanation": f"🚨 **網域偽裝攻擊警告！**\n\n郵件聲稱來自{found_organization}，但發信網域({sender_domain})與官方網域({expected_domain})不符。\n\n這是典型的網域偽裝攻擊，詐騙集團假冒合法機構騙取個人資料或金錢。",
                        "suggestions": [
                            "🚨 立即刪除此郵件，絕不要點擊任何連結",
                            "🚫 不要提供任何個人資料或付款資訊",
                            f"📞 如有疑慮，請直接撥打{found_organization}官方客服電話",
                            "🛡️ 可撥打165反詐騙專線檢舉此詐騙郵件",
                            f"🌐 如需繳費，請直接前往{found_organization}官方網站"
                        ],
                        "is_emerging": False,
                        "display_name": display_name,
                        "analysis_type": "郵件詐騙分析",
                        "spoofed_domain": sender_domain,
                        "legitimate_domain": expected_domain,
                        "organization": found_organization
                    }
                }
    
    # 5. 沒有發信者資訊但找到合法機構
    return {
        "success": True,
        "message": "郵件詐騙分析完成",
        "result": {
            "risk_level": "高風險",
            "fraud_type": f"疑似假冒{found_organization}的郵件",
            "explanation": f"⚠️ **需要特別注意！**\n\n郵件聲稱來自{found_organization}並包含繳費相關內容，但無法確認發信者身分。\n\n由於涉及敏感的繳費資訊，建議您格外謹慎。",
            "suggestions": [
                "🔍 不要點擊郵件中的任何連結",
                f"📞 直接撥打{found_organization}官方客服電話確認",
                f"🌐 透過{found_organization}官方網站查詢帳單狀態",
                "🛡️ 如有疑慮可撥打165反詐騙專線諮詢",
                "💡 合法機構通常不會透過郵件要求立即付款"
            ],
            "is_emerging": False,
            "display_name": display_name,
            "analysis_type": "郵件詐騙分析",
            "organization": found_organization,
            "expected_domain": expected_domain
        }
    }

if __name__ == '__main__':
    # 檢查環境變數
    validate_environment()
    
    port = int(os.environ.get('PORT', 5001))
    
    logger.info(f"啟動防詐騙機器人服務，端口: {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 