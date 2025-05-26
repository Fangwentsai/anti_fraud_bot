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

# 為了向下兼容，保留舊的變數名稱
function_inquiry_keywords = FUNCTION_INQUIRY_KEYWORDS
follow_up_patterns = FOLLOW_UP_PATTERNS
fraud_prevention_game_trigger_keywords = FRAUD_PREVENTION_GAME_TRIGGER_KEYWORDS
bot_trigger_keyword = BOT_TRIGGER_KEYWORD
analysis_prompts = ANALYSIS_PROMPTS

def expand_short_url(url):
    """嘗試展開短網址，返回原始URL和展開後的URL"""
    parsed_url = urlparse(url)
    is_short_url = False
    for domain in SHORT_URL_DOMAINS:
        if domain in parsed_url.netloc:
            is_short_url = True
            break
    
    if not is_short_url:
        return url, url, False, False
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        try:
            response = session.head(url, allow_redirects=True, timeout=10)
            expanded_url = response.url
        except Exception:
            response = session.get(url, allow_redirects=True, timeout=10, stream=True)
            expanded_url = response.url
            response.close()
        
        if expanded_url != url and expanded_url:
            logger.info(f"成功展開短網址: {url} -> {expanded_url}")
            return url, expanded_url, True, True
        else:
            logger.warning(f"短網址無法展開或已失效: {url}")
            return url, url, True, False
            
    except requests.exceptions.Timeout:
        logger.warning(f"展開短網址超時: {url}")
        return url, url, True, False
    except requests.exceptions.ConnectionError:
        logger.warning(f"展開短網址連接失敗: {url}")
        return url, url, True, False
    except Exception as e:
        logger.error(f"展開短網址時出錯: {e}")
        return url, url, True, False

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
        lines = analysis_result.strip().split('\n')
        result = {
            "risk_level": "中風險",
            "fraud_type": "未知",
            "explanation": "無法解析分析結果。",
            "suggestions": "建議謹慎處理。",
            "is_emerging": False
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith("風險等級：") or line.startswith("風險等級:"):
                result["risk_level"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif line.startswith("詐騙類型：") or line.startswith("詐騙類型:"):
                result["fraud_type"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif line.startswith("說明：") or line.startswith("說明:"):
                result["explanation"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif line.startswith("建議：") or line.startswith("建議:"):
                result["suggestions"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif line.startswith("新興手法：") or line.startswith("新興手法:"):
                emerging_text = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                result["is_emerging"] = emerging_text in ["是", "Yes", "true", "True"]
        
        if not result["explanation"] or result["explanation"] == "無法解析分析結果。":
            clean_text = analysis_result
            for prefix in ["風險等級：", "風險等級:", "詐騙類型：", "詐騙類型:", "說明：", "說明:", "建議：", "建議:", "新興手法：", "新興手法:"]:
                clean_text = clean_text.replace(prefix, "")
            
            clean_lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
            if clean_lines:
                result["explanation"] = clean_lines[0]
        
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
        original_url = None
        expanded_url = None
        is_short_url = False
        url_expanded_successfully = False
        
        url_pattern = re.compile(r'(https?://[^\s\u4e00-\u9fff，。！？；：]+|www\.[^\s\u4e00-\u9fff，。！？；：]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s\u4e00-\u9fff，。！？；：]*)?)')
        url_match = url_pattern.search(user_message)
        
        if url_match:
            original_url = url_match.group(0)
            original_url = re.sub(r'[，。！？；：]+$', '', original_url)
            
            if not original_url.startswith(('http://', 'https://')):
                original_url = 'https://' + original_url
                
            original_url, expanded_url, is_short_url, url_expanded_successfully = expand_short_url(original_url)
            
            if is_short_url and url_expanded_successfully:
                analysis_message = user_message.replace(url_match.group(0), f"{original_url} (展開後: {expanded_url})")
                logger.info(f"已展開短網址進行分析: {original_url} -> {expanded_url}")
            else:
                analysis_message = user_message
        else:
            analysis_message = user_message

        # 檢查網域變形攻擊
        spoofing_result = detect_domain_spoofing(analysis_message, SAFE_DOMAINS)
        if spoofing_result['is_spoofed']:
            logger.warning(f"檢測到網域變形攻擊: {spoofing_result['spoofed_domain']} 模仿 {spoofing_result['original_domain']}")
            return {
                "success": True,
                "message": "分析完成",
                "result": {
                    "risk_level": "高風險",
                    "fraud_type": "網域變形詐騙",
                    "explanation": spoofing_result['risk_explanation'],
                    "suggestions": f"• 立即停止使用這個網站\n• 不要輸入任何個人資料或密碼\n• 如需使用正牌網站，請直接搜尋 {spoofing_result['original_domain']} 或從書籤進入\n• 將此可疑網址回報給165反詐騙專線",
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
                    return {
                        "success": True,
                        "message": "分析完成",
                        "result": {
                            "risk_level": "低風險",
                            "fraud_type": "非詐騙相關",
                            "explanation": f"這個網站是 {original_domain}，{site_description}，可以安心使用。",
                            "suggestions": "這是正規網站，不必特別擔心。如有疑慮，建議您直接從官方管道進入該網站。",
                            "is_emerging": False,
                            "display_name": display_name,
                            "original_url": original_url,
                            "expanded_url": expanded_url,
                            "is_short_url": is_short_url,
                            "url_expanded_successfully": url_expanded_successfully
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
                                return {
                                    "success": True,
                                    "message": "分析完成",
                                    "result": {
                                        "risk_level": "低風險",
                                        "fraud_type": "非詐騙相關",
                                        "explanation": f"這個網站是 {safe_domain_key} 的子網域，{site_description}，可以安心使用。",
                                        "suggestions": "這是正規網站的子網域，不必特別擔心。如有疑慮，建議您直接從官方管道進入該網站。",
                                        "is_emerging": False,
                                        "display_name": display_name,
                                        "original_url": original_url,
                                        "expanded_url": expanded_url,
                                        "is_short_url": is_short_url,
                                        "url_expanded_successfully": url_expanded_successfully
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
        你是一位名為「防詐騙助手」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。
        
        {special_notes}
        
        以下是需要分析的信息：
        ---
        {analysis_message}
        ---
        
        請按照以下固定格式回答，每一行都必須包含：
        
        風險等級：[極高/高/中高/中/低/極低/無風險]
        詐騙類型：[具體的詐騙類型，如：釣魚網站、假交友詐騙、投資詐騙、失效短網址等]
        說明：[用簡單易懂的話解釋為什麼有風險或沒有風險，像鄰居朋友在聊天的語氣，避免複雜術語。如果是無法展開的短網址，請特別說明這種情況的危險性]
        建議：[用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號，給出簡單明確的防範建議]
        新興手法：[是/否]
        """
        
        if not openai_client:
            logger.error("OpenAI客戶端未初始化，無法進行分析")
            return {
                "success": False,
                "message": "AI分析服務暫時不可用，請稍後再試"
            }
        
        chat_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位名為「防詐騙助手」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。你的說話風格要：\n1. 非常簡單易懂，像鄰居朋友在聊天\n2. 用溫暖親切的語氣，不要太正式\n3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號\n4. 避免複雜的專業術語，用日常生活的話來解釋\n5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議\n6. 回應要簡短，不要太長篇大論"},
                {"role": "user", "content": openai_prompt}
            ],
            temperature=0.2,
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

@app.route("/fraud-statistics", methods=['GET'])
def fraud_statistics():
    """顯示詐騙統計數據頁面"""
    stats = firebase_manager.get_fraud_statistics()
    return render_template('statistics.html', stats=stats)

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
        
        # 檢查是否包含觸發關鍵詞或用戶處於等待分析狀態
        waiting_for_analysis = current_state.get("waiting_for_analysis", False)
        
        if bot_trigger_keyword not in text_message and not waiting_for_analysis:
            logger.info(f"訊息不包含觸發關鍵詞 '{bot_trigger_keyword}'，也不在等待分析狀態，忽略此訊息")
            return

        # 移除觸發關鍵詞
        cleaned_message = text_message
        if bot_trigger_keyword in text_message:
            cleaned_message = text_message.replace(bot_trigger_keyword, "").strip()
            logger.info(f"移除觸發關鍵詞後的訊息: {cleaned_message}")

        # 檢查是否為空訊息
        if not cleaned_message.strip():
            reply_text = f"嗨 {display_name}！我是土豆🥜\n你的防詐小助手，記得用土豆開頭喔！\n" \
                        f"讓我用4大服務保護你：\n\n" \
                        f"🔍 網站安全檢查：\n立刻分析假冒、釣魚網站！\n" \
                        f"📷 上傳截圖分析：\n不想輸入文字嗎？！直接截圖給我！\n" \
                        f"🎯 防詐騙測驗：\n玩問答提升你的防詐意識，輕鬆識破詐騙！\n" \
                        f"📚 詐騙案例：\n案例分析分享，了解9大詐騙類型。\n" \
                        f"💬 日常閒聊：\n陪你談天說地 甚至可以輸入：\n土豆 蔥爆牛肉怎麼做😂\n\n" \
                        f"💡 點擊下方按鈕，或直接告訴我你需要什麼！"
                
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="🔍 檢查網站安全", text=f"{bot_trigger_keyword} 請幫我分析這則訊息：")),
                QuickReplyButton(action=MessageAction(label="📷 上傳截圖分析", text=f"{bot_trigger_keyword} 請幫我分析圖片：")),
                QuickReplyButton(action=MessageAction(label="🎯 防詐騙測驗", text=f"{bot_trigger_keyword} 防詐騙測試")),
                QuickReplyButton(action=MessageAction(label="📚 詐騙案例", text=f"{bot_trigger_keyword} 詐騙類型列表")),
            ])
            
            mention_text = f"@{display_name} {reply_text}"
            if len(mention_text) <= LINE_MESSAGE_MAX_LENGTH:
                reply_text = mention_text
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
            
            try:
                import time
                time.sleep(1)
                
                unified_flex = FlexSendMessage(
                    alt_text="土豆的服務選單",
                    contents=BubbleContainer(
                        size="kilo",
                        header=BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(
                                    text="🥜 土豆的服務選單",
                                    weight="bold",
                                    size="lg",
                                    color="#1DB446"
                                )
                            ],
                            background_color="#F0F0F0",
                            padding_all="sm"
                        ),
                        body=BoxComponent(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                ButtonComponent(
                                    style="primary",
                                    color="#FF6B6B",
                                    action=MessageAction(
                                        label="🔍 檢查網站安全",
                                        text=f"{bot_trigger_keyword} 請幫我分析這則訊息："
                                    )
                                ),
                                ButtonComponent(
                                    style="primary", 
                                    color="#F39C12",
                                    action=MessageAction(
                                        label="📷 上傳截圖分析",
                                        text=f"{bot_trigger_keyword} 請幫我分析圖片："
                                    )
                                ),
                                ButtonComponent(
                                    style="primary",
                                    color="#4ECDC4",
                                    action=MessageAction(
                                        label="🎯 防詐騙測驗",
                                        text=f"{bot_trigger_keyword} 防詐騙測試"
                                    )
                                ),
                                ButtonComponent(
                                    style="primary",
                                    color="#45B7D1", 
                                    action=MessageAction(
                                        label="📚 詐騙案例",
                                        text=f"{bot_trigger_keyword} 詐騙類型列表"
                                    )
                                )
                            ]
                        )
                    )
                )
                
                if is_group_message:
                    line_bot_api.push_message(event.source.group_id, unified_flex)
                else:
                    line_bot_api.push_message(user_id, unified_flex)
                logger.info("已發送統一的彩色Flex Message按鈕")
                
            except LineBotApiError as e:
                if e.status_code == 429:
                    logger.warning(f"達到LINE API月度限制，無法發送額外按鈕: {e}")
                else:
                    logger.error(f"LINE API其他錯誤: {e}")
            except Exception as e:
                logger.error(f"發送統一按鈕時發生未知錯誤: {e}")
            
            return

        # 處理遊戲觸發
        if is_game_trigger(cleaned_message):
            logger.info(f"檢測到防詐騙測試觸發: {cleaned_message}")
            flex_message, error_message = start_potato_game(user_id)
            
            if flex_message:
                line_bot_api.reply_message(reply_token, flex_message)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
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
                else:
                    error_text = "抱歉，詐騙類型資料載入失敗。\n\n💡 您可以：\n• 直接傳送可疑訊息給我分析\n• 說「防詐騙測試」進行知識測驗"
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
            except Exception as e:
                logger.error(f"處理詐騙類型查詢時發生錯誤: {e}")
                error_text = "抱歉，詐騙類型查詢功能暫時無法使用。\n\n💡 您可以：\n• 直接傳送可疑訊息給我分析\n• 說「防詐騙測試」進行知識測驗"
                line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
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
                return

        # 檢查分析請求但沒有內容
        analysis_request_keywords = ["請幫我分析這則訊息", "幫我分析訊息", "請分析這則訊息", "請幫我分析", "分析這則訊息"]
        is_analysis_request = any(keyword in cleaned_message for keyword in analysis_request_keywords)
        
        if is_analysis_request and (len(cleaned_message) < 20 or cleaned_message.rstrip("：:") in analysis_request_keywords):
            logger.info(f"檢測到分析請求但沒有提供具體內容: {cleaned_message}")
            
            current_state["waiting_for_analysis"] = True
            user_conversation_state[user_id] = current_state
            
            prompt_message = f"好的 {display_name}，我會幫您分析可疑訊息！\n\n" \
                           f"請直接把您收到的可疑訊息或網址傳給我，我會立即為您分析風險程度。\n\n" \
                           f"💡 您可以：\n" \
                           f"• 轉傳可疑的文字訊息\n" \
                           f"• ⚠️FB,IG不易判別，請提供貼文內網址\n" \
                           f"• 貼上可疑的網址連結\n" \
                           f"• 描述您遇到的可疑情況"
            
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
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=prompt_message))
            except LineBotApiError as e:
                logger.error(f"發送分析提示訊息時發生LINE API錯誤: {e}")
                return
            except Exception as e:
                logger.error(f"發送分析提示訊息時發生未知錯誤: {e}")
            return

        # 檢查圖片分析請求
        if "分析圖片" in cleaned_message or "檢查圖片" in cleaned_message:
            image_analysis_prompt = f"📷 {display_name}，請上傳您想要分析的圖片！\n\n" \
                                  f"我可以幫您分析：\n" \
                                  f"🔍 可疑網站截圖\n" \
                                  f"💬 詐騙對話截圖\n" \
                                  f"📱 可疑簡訊截圖\n" \
                                  f"📧 釣魚郵件截圖\n" \
                                  f"💰 投資廣告截圖\n" \
                                  f"🎯 其他可疑內容截圖\n\n" \
                                  f"請直接上傳圖片，大約10-15秒就能立即為您分析！"
            
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
                    except Exception as push_error:
                        logger.error(f"圖片分析提示訊息使用push_message也失敗: {push_error}")
            return

        # 判斷是否需要進行詐騙分析
        if waiting_for_analysis:
            logger.info(f"用戶處於等待分析狀態，強制執行詐騙分析: {cleaned_message}")
            current_state["waiting_for_analysis"] = False
            user_conversation_state[user_id] = current_state
        
        # 執行詐騙分析
        analysis_result = detect_fraud_with_chatgpt(cleaned_message, display_name, user_id)
        
        if analysis_result and analysis_result.get("success", False):
            analysis_data = analysis_result.get("result", {})
            
            # 檢查是否是網域變形攻擊
            if analysis_data.get("is_domain_spoofing", False):
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
                except LineBotApiError as e:
                    logger.error(f"發送Flex Message時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        try:
                            line_bot_api.push_message(user_id, flex_message)
                            logger.info(f"分析回覆令牌無效，改用push_message成功: {user_id}")
                        except Exception as push_error:
                            logger.error(f"分析使用push_message也失敗: {push_error}")
                except Exception as e:
                    logger.error(f"發送Flex Message時發生未知錯誤: {e}")
                    # 發送基本文本消息
                    risk_level = analysis_data.get("risk_level", "不確定")
                    fraud_type = analysis_data.get("fraud_type", "未知")
                    explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
                    suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
                    
                    text_response = f"🔍 風險分析結果\n\n風險等級：{risk_level}\n詐騙類型：{fraud_type}\n\n說明：{explanation}\n\n建議：{suggestions}"
                    
                    try:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))
                    except Exception as text_error:
                        logger.error(f"發送文本回覆也失敗: {text_error}")
            else:
                # 如果Flex消息創建失敗，發送基本文本消息
                risk_level = analysis_data.get("risk_level", "不確定")
                fraud_type = analysis_data.get("fraud_type", "未知")
                explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
                suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
                
                text_response = f"🔍 風險分析結果\n\n風險等級：{risk_level}\n詐騙類型：{fraud_type}\n\n說明：{explanation}\n\n建議：{suggestions}"
                
                try:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))
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
            except Exception as error_send_error:
                logger.error(f"發送錯誤訊息失敗: {error_send_error}")
        
        return

        # 正常的詐騙分析判斷
        if should_perform_fraud_analysis(cleaned_message, user_id):
            logger.info(f"執行詐騙分析: {cleaned_message}")
            analysis_result = detect_fraud_with_chatgpt(cleaned_message, display_name, user_id)
            
            if analysis_result and analysis_result.get("success", False):
                analysis_data = analysis_result.get("result", {})
                
                if analysis_data.get("is_domain_spoofing", False):
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
                
                if flex_message:
                    try:
                        line_bot_api.reply_message(reply_token, flex_message)
                        logger.info(f"使用舊版API回覆網頁分析成功: {user_id}")
                    except LineBotApiError as e:
                        logger.error(f"發送Flex Message時發生錯誤: {e}")
                        if "Invalid reply token" in str(e):
                            try:
                                line_bot_api.push_message(user_id, flex_message)
                                logger.info(f"網頁分析回覆令牌無效，改用push_message成功: {user_id}")
                            except Exception as push_error:
                                logger.error(f"網頁分析使用push_message也失敗: {push_error}")
                    except Exception as e:
                        logger.error(f"發送Flex Message時發生未知錯誤: {e}")
                        risk_level = analysis_data.get("risk_level", "不確定")
                        fraud_type = analysis_data.get("fraud_type", "未知")
                        explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
                        suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
                        
                        text_response = f"🔍 風險分析結果\n\n風險等級：{risk_level}\n詐騙類型：{fraud_type}\n\n說明：{explanation}\n\n建議：{suggestions}"
                        
                        try:
                            line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))
                        except Exception as text_error:
                            logger.error(f"發送文本回覆也失敗: {text_error}")
                else:
                    risk_level = analysis_data.get("risk_level", "不確定")
                    fraud_type = analysis_data.get("fraud_type", "未知")
                    explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
                    suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
                    
                    text_response = f"🔍 風險分析結果\n\n風險等級：{risk_level}\n詐騙類型：{fraud_type}\n\n說明：{explanation}\n\n建議：{suggestions}"
                    
                    try:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))
                    except Exception as text_error:
                        logger.error(f"發送文本回覆失敗: {text_error}")
            else:
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
                except Exception as error_send_error:
                    logger.error(f"發送錯誤訊息失敗: {error_send_error}")
            
            return

        logger.info(f"進入一般聊天模式: {cleaned_message}")
        try:
            chat_response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                 {"role": "system", "content": "你是一位名為「土豆」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。你的說話風格要：\n1. 非常簡單易懂，像鄰居朋友在聊天\n2. 用溫暖親切的語氣，不要太正式\n3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號\n4. 避免複雜的專業術語，用日常生活的話來解釋\n5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議\n6. 回應要簡短，不要太長篇大論"},
                 {"role": "user", "content": cleaned_message}
                ],
                temperature=CHAT_TEMPERATURE,
                max_tokens=CHAT_MAX_TOKENS
            )
            
            if chat_response and chat_response.choices:
                chat_reply = chat_response.choices[0].message.content.strip()
                
                if random.random() < CHAT_TIP_PROBABILITY:
                    tips = get_anti_fraud_tips()
                    if tips:
                        random_tip = random.choice(tips)
                        chat_reply += f"\n\n💡 小提醒：{random_tip}"
                
                if len(chat_reply) > LINE_MESSAGE_SAFE_LENGTH:
                    chat_reply = chat_reply[:LINE_MESSAGE_SAFE_LENGTH] + "..."
                
                introduction = f"\n\n💫 我是您的專業防詐騙助手！經過全面測試，我能為您提供：\n🔍 網站安全檢查\n🎯 防詐騙知識測驗\n📚 詐騙案例查詢\n\n有任何可疑訊息都歡迎直接傳給我分析喔！"
                
                if user_id not in first_time_chatters:
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
                    else:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
                        
                elif action == 'potato_game_answer':
                    answer_index = int(params.get('answer', 0))
                    is_correct, result_flex = handle_potato_game_answer(user_id, answer_index)
                    
                    if is_correct is None and result_flex is None:
                        logger.info(f"忽略用戶 {user_id} 在冷卻時間內的重複點擊")
                        return
                    
                    line_bot_api.reply_message(reply_token, result_flex)
                    
                elif action == 'show_main_menu':
                    reply_text = f"嗨 {display_name}！我是土豆🥜\n你的防詐小助手，記得用土豆開頭喔！\n" \
                                f"讓我用4大服務保護你：\n\n" \
                                f"🔍 網站安全檢查：\n立刻分析假冒、釣魚網站！\n" \
                                f"📷 上傳截圖分析：\n不想輸入文字嗎？！直接截圖給我！\n" \
                                f"🎯 防詐騙測驗：\n玩問答提升你的防詐意識，輕鬆識破詐騙！\n" \
                                f"📚 詐騙案例：\n案例分析分享，了解9大詐騙類型。\n" \
                                f"💬 日常閒聊：\n陪你談天說地 甚至可以輸入：\n土豆 蔥爆牛肉怎麼做😂\n\n" \
                                f"💡 點擊下方按鈕，或直接告訴我你需要什麼！"
                    
                    quick_reply = QuickReply(items=[
                        QuickReplyButton(action=MessageAction(label="🔍 檢查網站安全", text=f"{bot_trigger_keyword} 請幫我分析這則訊息：")),
                        QuickReplyButton(action=MessageAction(label="📷 上傳截圖分析", text=f"{bot_trigger_keyword} 請幫我分析圖片：")),
                        QuickReplyButton(action=MessageAction(label="🎯 防詐騙測驗", text=f"{bot_trigger_keyword} 防詐騙測試")),
                        QuickReplyButton(action=MessageAction(label="📚 詐騙案例", text=f"{bot_trigger_keyword} 詐騙類型列表")),
                    ])
                    
                    mention_text = f"@{display_name} {reply_text}"
                    if len(mention_text) <= LINE_MESSAGE_MAX_LENGTH:
                        reply_text = mention_text
                    
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
                    
                    try:
                        import time
                        time.sleep(1)
                        
                        unified_flex = FlexSendMessage(
                            alt_text="土豆的服務選單",
                            contents=BubbleContainer(
                                size="kilo",
                                header=BoxComponent(
                                    layout="vertical",
                                    contents=[
                                        TextComponent(
                                            text="🥜 土豆的服務選單",
                                            weight="bold",
                                            size="lg",
                                            color="#1DB446"
                                        )
                                    ],
                                    background_color="#F0F0F0",
                                    padding_all="sm"
                                ),
                                body=BoxComponent(
                                    layout="vertical",
                                    spacing="sm",
                                    contents=[
                                        ButtonComponent(
                                            style="primary",
                                            color="#FF6B6B",
                                            action=MessageAction(
                                                label="🔍 檢查網站安全",
                                                text=f"{bot_trigger_keyword} 請幫我分析這則訊息："
                                            )
                                        ),
                                        ButtonComponent(
                                            style="primary", 
                                            color="#F39C12",
                                            action=MessageAction(
                                                label="📷 上傳截圖分析",
                                                text=f"{bot_trigger_keyword} 請幫我分析圖片："
                                            )
                                        ),
                                        ButtonComponent(
                                            style="primary",
                                            color="#4ECDC4",
                                            action=MessageAction(
                                                label="🎯 防詐騙測驗",
                                                text=f"{bot_trigger_keyword} 防詐騙測試"
                                            )
                                        ),
                                        ButtonComponent(
                                            style="primary",
                                            color="#45B7D1", 
                                            action=MessageAction(
                                                label="📚 詐騙案例",
                                                text=f"{bot_trigger_keyword} 詐騙類型列表"
                                            )
                                        )
                                    ]
                                )
                            )
                        )
                        
                        line_bot_api.push_message(user_id, unified_flex)
                        
                    except LineBotApiError as e:
                        if e.status_code == 429:
                            logger.warning(f"達到LINE API月度限制，無法發送額外按鈕: {e}")
                        else:
                            logger.error(f"LINE API其他錯誤: {e}")
                    except Exception as e:
                        logger.error(f"發送統一按鈕時發生未知錯誤: {e}")
                        
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
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆圖片分析時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        try:
                            line_bot_api.push_message(user_id, flex_message)
                            logger.info(f"圖片分析回覆令牌無效，改用push_message成功: {user_id}")
                        except Exception as push_error:
                            logger.error(f"圖片分析使用push_message也失敗: {push_error}")
            else:
                error_message = "抱歉，無法分析此圖片，請稍後再試。"
                
                try:
                    line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text=error_message)
                    )
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆圖片錯誤訊息時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        try:
                            line_bot_api.push_message(user_id, TextSendMessage(text=error_message))
                            logger.info(f"圖片錯誤訊息回覆令牌無效，改用push_message成功: {user_id}")
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
    
    if len(message_lower) < 3:
        return False
    
    if any(keyword in message_lower for keyword in function_inquiry_keywords):
        return False
    
    greetings = ["你好", "哈囉", "嗨", "hi", "hello", "早安", "午安", "晚安", "再見", "謝謝", "感謝"]
    if any(greeting in message_lower for greeting in greetings) and len(message_lower) < 10:
        return False
    
    if any(keyword in message_lower for keyword in ["詐騙類型", "詐騙手法", "詐騙種類", "常見詐騙"]):
        return False
    
    if is_game_trigger(message):
        return False
    
    if is_weather_related(message):
        return False
    
    analysis_request_keywords = ["請幫我分析這則訊息", "幫我分析訊息", "請分析這則訊息", "請幫我分析", "分析這則訊息"]
    if any(keyword in message and len(message.strip()) < 20 for keyword in analysis_request_keywords):
        logger.info("檢測到純粹的分析請求（沒有具體內容），不觸發詐騙分析")
        return False
    
    import re
    url_pattern = re.compile(r'(https?://[^\s\u4e00-\u9fff，。！？；：]+|www\.[^\s\u4e00-\u9fff，。！？；：]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s\u4e00-\u9fff，。！？；：]*)?)')
    if url_pattern.search(message):
        logger.info("檢測到URL，觸發詐騙分析")
        return True
    
    explicit_analysis_requests = [
        "這是詐騙嗎", "這可靠嗎", "這是真的嗎", 
        "這安全嗎", "可以相信嗎", "有問題嗎", "是騙人的嗎"
    ]
    if any(request in message_lower for request in explicit_analysis_requests):
        logger.info("檢測到明確分析請求")
        return True
    
    analysis_request_patterns = [
        "請幫我分析", "幫我分析", "請分析", "分析一下", "幫忙分析",
        "請檢查", "幫我檢查", "檢查一下", "幫忙檢查"
    ]
    
    for pattern in analysis_request_patterns:
        if pattern in message:
            remaining_content = message.replace(pattern, "").strip()
            if len(remaining_content) > 3:
                logger.info(f"檢測到分析請求關鍵詞：{pattern}，且有具體內容")
                return True
    
    analysis_keywords = ["分析", "詐騙", "安全", "可疑", "風險", "網站", "連結", "投資", "賺錢"]
    question_words = ["嗎", "呢", "吧", "?", "？"]
    
    has_analysis_keyword = any(keyword in message_lower for keyword in analysis_keywords)
    has_question_word = any(word in message_lower for word in question_words)
    
    if has_analysis_keyword and has_question_word:
        logger.info("檢測到分析關鍵詞+疑問詞組合")
        return True
    
    fraud_keywords = ["詐騙", "被騙", "轉帳", "匯款", "投資", "賺錢", "兼職", "工作", "銀行", "帳號", "密碼", "個資", "中獎", "免費", "限時", "急"]
    fraud_count = sum(1 for keyword in fraud_keywords if keyword in message_lower)
    
    if fraud_count >= 2:
        logger.info(f"檢測到 {fraud_count} 個詐騙關鍵詞")
        return True
    
    return False

# 初始化FlexMessageService
flex_message_service = FlexMessageService()

if __name__ == '__main__':
    # 檢查環境變數
    validate_environment()
    
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"啟動防詐騙機器人服務，端口: {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 