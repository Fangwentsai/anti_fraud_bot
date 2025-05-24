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
    ButtonComponent, URIAction, PostbackAction
)
from firebase_manager import FirebaseManager
from domain_spoofing_detector import detect_domain_spoofing
from dotenv import load_dotenv
import time

# 導入新的模組化組件
from config import *
from fraud_knowledge import load_fraud_tactics, get_anti_fraud_tips, get_fraud_features, analyze_fraud_keywords
from weather_service import handle_weather_query, is_weather_related
from flex_message_service import (
    create_analysis_flex_message, create_domain_spoofing_flex_message,
    create_donation_flex_message, create_weather_flex_message,
    create_fraud_types_flex_message
)
from game_service import (
    start_potato_game, handle_potato_game_answer, is_game_trigger, get_user_game_state
)

# 指定 .env 文件的路徑
# 優先從當前目錄載入，然後嘗試其他路徑
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
    # 嘗試載入預設的.env
    load_dotenv()
    print("嘗試載入預設的.env文件")

# 設置環境變數（如果在Render等平台上）

# 使用配置模組中的常數
# SHORT_URL_DOMAINS 現在從 config.py 導入

# 從JSON文件載入安全網域列表
def load_safe_domains():
    """從safe_domains.json文件載入安全網域列表"""
    try:
        # 獲取當前腳本的目錄
        script_dir = os.path.dirname(os.path.abspath(__file__))
        safe_domains_path = os.path.join(script_dir, 'safe_domains.json')
        
        with open(safe_domains_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 扁平化分類的安全網域字典
            flattened_safe_domains = {}
            for category, domains in data['safe_domains'].items():
                if isinstance(domains, dict):
                    flattened_safe_domains.update(domains)
                else:
                    logger.warning(f"類別 '{category}' 的格式不正確: {type(domains)}")
            
            return flattened_safe_domains, data['donation_domains']
    except FileNotFoundError:
        print("找不到safe_domains.json文件，使用預設的安全網域列表")
        # 提供基本的預設列表作為備用
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
        # 提供基本的預設列表作為備用
        default_safe_domains = {
            "google.com": "Google 搜尋引擎",
            "facebook.com": "Facebook 社群網站",
            "youtube.com": "YouTube 影音平台",
            "gov.tw": "中華民國政府網站",
            "165.npa.gov.tw": "165反詐騙諮詢專線"
        }
        default_donation_domains = []
        return default_safe_domains, default_donation_domains

# 設置日誌（需要在載入安全網域之前初始化）
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

# Line API 設定 - 使用配置模組，添加安全檢查
if LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    logger.info("LINE Bot API 初始化成功")
else:
    line_bot_api = None
    handler = None
    logger.warning("LINE Bot API 初始化失敗：缺少必要的環境變數")

# OpenAI設定 - 使用新版本的客戶端初始化，添加錯誤處理
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=30.0,  # 設置超時
            max_retries=3   # 設置重試次數
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

# 用戶遊戲狀態
user_game_state = {}

# 用戶最後聊天時間記錄
user_last_chat_time = {}
user_pending_analysis = {} # 用於追蹤等待用戶澄清的分析請求
first_time_chatters = set()  # 追蹤首次聊天的用戶

# 用戶對話狀態
user_conversation_state = {}  # 格式: {user_id: {"last_time": timestamp, "waiting_for_analysis": True/False}}

# 使用配置模組中的常數
# CHAT_TIP_PROBABILITY, BOT_TRIGGER_KEYWORD 等現在從 config.py 導入
# 關鍵詞和模式現在從 config.py 導入：
# - FUNCTION_INQUIRY_KEYWORDS (原 function_inquiry_keywords)
# - FOLLOW_UP_PATTERNS (原 follow_up_patterns)
# - FRAUD_PREVENTION_GAME_TRIGGER_KEYWORDS (原 fraud_prevention_game_trigger_keywords)  
# - BOT_TRIGGER_KEYWORD (原 bot_trigger_keyword)
# - ANALYSIS_PROMPTS (原 analysis_prompts)

# 為了向下兼容，保留舊的變數名稱
function_inquiry_keywords = FUNCTION_INQUIRY_KEYWORDS
follow_up_patterns = FOLLOW_UP_PATTERNS
fraud_prevention_game_trigger_keywords = FRAUD_PREVENTION_GAME_TRIGGER_KEYWORDS
bot_trigger_keyword = BOT_TRIGGER_KEYWORD
analysis_prompts = ANALYSIS_PROMPTS

def expand_short_url(url):
    """
    嘗試展開短網址，返回原始URL和展開後的URL
    
    Args:
        url: 可能的短網址
    
    Returns:
        tuple: (原始URL, 展開後的URL, 是否為短網址, 是否成功展開)
    """
    # 檢查是否為短網址
    parsed_url = urlparse(url)
    is_short_url = False
    for domain in SHORT_URL_DOMAINS:
        if domain in parsed_url.netloc:
            is_short_url = True
            break
    
    if not is_short_url:
        return url, url, False, False
    
    # 嘗試展開短網址
    try:
        session = requests.Session()
        response = session.head(url, allow_redirects=True, timeout=5)
        expanded_url = response.url
        
        if expanded_url != url:
            logger.info(f"成功展開短網址: {url} -> {expanded_url}")
            return url, expanded_url, True, True
        else:
            logger.warning(f"URL可能不是短網址或無法展開: {url}")
            return url, url, True, False
    except Exception as e:
        logger.error(f"展開短網址時出錯: {e}")
        return url, url, True, False

# 定義防詐小知識
anti_fraud_tips = []  # 現在使用 get_anti_fraud_tips() 函數
fraud_types = load_fraud_tactics()  # 從模組載入


# 載入詐騙話術資料 - 使用模組化版本
fraud_tactics = load_fraud_tactics()

def create_suspicious_ad_warning_message(display_name, ad_description="兼職計劃旅程"):
    """創建可疑廣告警告訊息，使用emoji代替數字編號"""
    warning_message = f"@{display_name} 聽起來這個廣告有點讓人疑惑，尤其是牽涉到「{ad_description}」這類說法時，我們要特別小心。這類廣告常見於詐騙手法裡，可能會利用「兼職」或「免費旅遊」的誘因，誘使你留下個人資料，甚至進一步要求匯款或購買昂貴課程。\n\n建議你可以先做以下幾件事：\n\n"
    
    warning_message += "🚫 不要急著留下信箱或任何個人資料，先觀察和詢問更多細節。\n"
    warning_message += "🔍 查詢這個廣告的來源，例如公司名稱或負責人資料，看看是否有正當的背景。\n"
    warning_message += "🌐 搜尋網路評價或負評，看看其他人有沒有遭遇過類似的詐騙。\n"
    warning_message += "🛡️ 如果覺得不安全，直接忽略或封鎖廣告，避免被騙。\n\n"
    
    warning_message += "如果方便的話，可以把廣告內容或截圖分享給我，我可以幫你分析得更詳細喔！你的安全最重要，我會一直陪著你。😊"
    
    return warning_message
load_fraud_tactics()

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
        
        # 如果說明為空，嘗試從整個回應中提取
        if not result["explanation"] or result["explanation"] == "無法解析分析結果。":
            # 移除標籤，取得剩餘內容作為說明
            clean_text = analysis_result
            for prefix in ["風險等級：", "風險等級:", "詐騙類型：", "詐騙類型:", "說明：", "說明:", "建議：", "建議:", "新興手法：", "新興手法:"]:
                clean_text = clean_text.replace(prefix, "")
            
            # 清理並取得有意義的內容
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
    # 合法的子網域特徵
    if not subdomain_part or len(subdomain_part) > 20:  # 太長的子網域可疑
        return False
    
    # 常見的合法子網域前綴
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
        'en', 'english', 'zh', 'chinese'
    ]
    
    # 檢查是否為已知的合法前綴
    if subdomain_part.lower() in legitimate_prefixes:
        return True
    
    # 檢查是否包含可疑字元或模式
    suspicious_patterns = [
        '-tw-', '-official-', '-secure-', '-login-', '-bank-',
        'phishing', 'fake', 'scam', 'fraud', 'malware'
    ]
    
    for pattern in suspicious_patterns:
        if pattern in subdomain_part.lower():
            return False
    
    # 檢查是否只包含字母、數字和連字符
    import re
    if not re.match(r'^[a-zA-Z0-9-]+$', subdomain_part):
        return False
    
    # 不能以連字符開始或結束
    if subdomain_part.startswith('-') or subdomain_part.endswith('-'):
        return False
    
    return True

def detect_fraud_with_chatgpt(user_message, display_name="朋友", user_id=None):
    """使用OpenAI的API檢測詐騙信息"""
    import re
    from urllib.parse import urlparse
    
    try:
        # 檢查訊息是否包含URL
        original_url = None
        expanded_url = None
        is_short_url = False
        url_expanded_successfully = False
        
        # 改進的URL提取正則表達式，確保只提取有效的URL部分
        # 支援二級域名如 .com.tw, .co.uk 等
        url_pattern = re.compile(r'(https?://[^\s\u4e00-\u9fff，。！？；：]+|www\.[^\s\u4e00-\u9fff，。！？；：]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s\u4e00-\u9fff，。！？；：]*)?)')
        url_match = url_pattern.search(user_message)
        
        if url_match:
            original_url = url_match.group(0)
            # 移除末尾可能的標點符號
            original_url = re.sub(r'[，。！？；：]+$', '', original_url)
            
            # 確保URL開頭是http://或https://
            if not original_url.startswith(('http://', 'https://')):
                original_url = 'https://' + original_url
                
            # 展開可能的短網址
            original_url, expanded_url, is_short_url, url_expanded_successfully = expand_short_url(original_url)
            
            # 如果是短網址且成功展開，調整分析訊息
            if is_short_url and url_expanded_successfully:
                # 將原始訊息中的短網址替換為展開後的URL，以便於分析
                analysis_message = user_message.replace(url_match.group(0), f"{original_url} (展開後: {expanded_url})")
                logger.info(f"已展開短網址進行分析: {original_url} -> {expanded_url}")
            else:
                analysis_message = user_message
        else:
            analysis_message = user_message

        # 首先檢查網域變形攻擊
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
                    "is_domain_spoofing": True,  # 特殊標記
                    "spoofing_result": spoofing_result  # 包含完整的變形檢測結果
                },
                "raw_result": f"網域變形攻擊檢測：{spoofing_result['spoofing_type']} - {spoofing_result['risk_explanation']}"
            }

        # 檢查訊息是否包含白名單中的網址 - 改進版
        # 提取URL進行精確匹配，支援二級域名
        url_pattern_detailed = re.compile(r'https?://[^\s\u4e00-\u9fff，。！？；：]+|www\.[^\s\u4e00-\u9fff，。！？；：]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s\u4e00-\u9fff，。！？；：]*)?')
        urls = url_pattern_detailed.findall(analysis_message)
        
        # 清理提取的URL，移除末尾標點符號
        cleaned_urls = []
        for url in urls:
            cleaned_url = re.sub(r'[，。！？；：]+$', '', url)
            if cleaned_url:  # 確保不是空字串
                cleaned_urls.append(cleaned_url)
        
        # 創建標準化的安全網域列表（包含www和非www版本）
        normalized_safe_domains = {}
        for safe_domain, description in SAFE_DOMAINS.items():
            safe_domain_lower = safe_domain.lower()
            normalized_safe_domains[safe_domain_lower] = (safe_domain, description)
            
            # 添加www和非www版本
            if safe_domain_lower.startswith('www.'):
                normalized_safe_domains[safe_domain_lower[4:]] = (safe_domain, description)
            else:
                normalized_safe_domains['www.' + safe_domain_lower] = (safe_domain, description)
        
        # 檢查每個提取的URL
        for url in cleaned_urls:
            # 標準化URL
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = 'https://' + url
                else:
                    url = 'https://' + url
            
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                
                # 檢查是否完全匹配白名單網域
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
                
                # 檢查是否為合法的子網域（例如 event.liontravel.com）
                for safe_domain_key in SAFE_DOMAINS.keys():
                    safe_domain_lower = safe_domain_key.lower()
                    # 移除www前綴進行比較
                    safe_domain_clean = safe_domain_lower[4:] if safe_domain_lower.startswith('www.') else safe_domain_lower
                    domain_clean = domain[4:] if domain.startswith('www.') else domain
                    
                    # 檢查是否為合法子網域（必須是 *.safe_domain 的格式）
                    if domain_clean.endswith('.' + safe_domain_clean) and domain_clean != safe_domain_clean:
                        # 確保是真正的子網域，不是變形攻擊
                        subdomain_part = domain_clean[:-len('.' + safe_domain_clean)]
                        # 子網域部分不能包含可疑字元或過長
                        if self._is_legitimate_subdomain(subdomain_part):
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
                # URL解析失敗，繼續檢查下一個
                continue
        # 如果是短網址但無法展開，提高風險評估
        special_notes = ""
        if is_short_url and not url_expanded_successfully:
            special_notes = "這是個短網址，但我們無法展開查看真正的目的地，這種情況要特別小心。短網址常被詐騙者利用來隱藏真實的惡意網站。除非您非常確定這個連結安全，否則不建議點擊。"
            logger.warning(f"無法展開的短網址: {original_url}，建議提高警覺")
        
        openai_prompt = f"""
        你是一位名為「防詐騙助手」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。你的說話風格要：
        1. 非常簡單易懂，像鄰居朋友在聊天
        2. 用溫暖親切的語氣，不要太正式
        3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號
        4. 避免複雜的專業術語，用日常生活的話來解釋
        5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議
        6. 回應要簡短，不要太長篇大論
        
        {special_notes}
        
        以下是需要分析的信息：
        ---
        {analysis_message}
        ---
        
        請用繁體中文回答，避免直接使用問候語。直接開始分析。回答應簡潔直接，像是鄰居朋友給出的貼心提醒。
        """
        
        # 調用OpenAI API (修正為新版API格式)
        if not openai_client:
            logger.error("OpenAI客戶端未初始化，無法進行分析")
            return {
                "success": False,
                "message": "AI分析服務暫時不可用，請稍後再試"
            }
        
        chat_response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "你是一位名為「防詐騙助手」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。你的說話風格要：\n1. 非常簡單易懂，像鄰居朋友在聊天\n2. 用溫暖親切的語氣，不要太正式\n3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號\n4. 避免複雜的專業術語，用日常生活的話來解釋\n5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議\n6. 回應要簡短，不要太長篇大論"},
                {"role": "user", "content": openai_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        if chat_response and chat_response.choices:
            analysis_result = chat_response.choices[0].message.content.strip()
            logger.info(f"風險分析結果: {analysis_result[:100]}...")  # 僅記錄部分結果
            
            # 將結果解析成結構化格式
            parsed_result = parse_fraud_analysis(analysis_result)
            
            # 添加一個使用者可識別的標識
            parsed_result["display_name"] = display_name
            
            # 添加URL相關信息
            parsed_result["original_url"] = original_url
            parsed_result["expanded_url"] = expanded_url
            parsed_result["is_short_url"] = is_short_url
            parsed_result["url_expanded_successfully"] = url_expanded_successfully
            
            # 如果是短網址但無法展開，提高風險等級
            if is_short_url and not url_expanded_successfully:
                if parsed_result["risk_level"] == "低風險":
                    parsed_result["risk_level"] = "中風險"
                    parsed_result["explanation"] = f"{parsed_result['explanation']}\n\n⚠️ 此外，這是一個短網址但無法展開查看真正的目的地，這點也要特別小心。"
                
                if "短網址" not in parsed_result["explanation"]:
                    parsed_result["explanation"] = f"{parsed_result['explanation']}\n\n⚠️ 要注意這是一個短網址(像是縮短過的網址)，無法看到真正要去的網站，這種情況要特別小心。"
                
                if "短網址" not in parsed_result["suggestions"]:
                    parsed_result["suggestions"] = f"{parsed_result['suggestions']}\n• 遇到短網址時，最好先詢問傳送連結的人是什麼內容，或者乾脆不要點擊。"
            
            # 如果是短網址且成功展開，在結果中加入說明
            if is_short_url and url_expanded_successfully:
                parsed_result["explanation"] = f"{parsed_result['explanation']}\n\n這個連結是短網址，已經幫您展開查看真正的目的地是: {expanded_url}"
            
            # 檢查解析結果，確保所有必要欄位都有值
            if not parsed_result.get("explanation") or parsed_result["explanation"] == "無法解析分析結果。":
                # 如果無法正確解析理由，直接使用原始回應
                logger.warning("無法正確解析分析理由，使用原始回應替代")
                parsed_result["explanation"] = analysis_result.replace("風險等級：", "").replace("詐騙類型：", "").replace("說明：", "").replace("建議：", "").replace("新興手法：", "").strip()
                
                # 確保理由不為空
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
        
        # 檢查是否包含觸發關鍵詞 "防詐騙助手"或者用戶處於等待分析狀態
        waiting_for_analysis = current_state.get("waiting_for_analysis", False)
        
        # 如果是群組訊息，需要檢查是否包含觸發關鍵詞，或者用戶處於等待分析狀態
        if is_group_message and bot_trigger_keyword not in text_message and not waiting_for_analysis:
            logger.info(f"群組訊息不包含觸發關鍵詞 '{bot_trigger_keyword}'，也不在等待分析狀態，忽略此訊息")
            return

        # 在群組中移除觸發關鍵詞，以便後續處理
        cleaned_message = text_message
        if is_group_message and bot_trigger_keyword in text_message:
            cleaned_message = text_message.replace(bot_trigger_keyword, "").strip()
            logger.info(f"移除觸發關鍵詞後的訊息: {cleaned_message}")

        # 檢查是否為空訊息（移除觸發詞後）
        if not cleaned_message.strip():
            # 土豆的熱情自我介紹
            reply_text = f"嗨嗨 {display_name}！我是土豆 🥔 很開心你叫我！\n\n" \
                        f"我是專業的防詐騙小助手，經過全面測試，已經準備好用四項超強服務保護你：\n\n" \
                        f"🔍 **網站安全檢查**\n" \
                        f"    ✨ 把可疑網址丟給我，我立刻幫你檢查安全性\n" \
                        f"    ✨ 自動抓出假冒購物網站、釣魚網站等壞蛋\n\n" \
                        f"🎯 **防詐騙知識測驗**\n" \
                        f"    ✨ 跟我玩問答遊戲，提升你的防詐騙能力\n" \
                        f"    ✨ 學會識破31種常見詐騙手法\n\n" \
                        f"📚 **詐騙案例查詢**\n" \
                        f"    ✨ 真實詐騙案例分析，讓你看清騙子手法\n" \
                        f"    ✨ 涵蓋9大類詐騙類型完整說明\n\n" \
                        f"☁️ **天氣預報查詢**\n" \
                        f"    ✨ 台灣各縣市即時天氣，想知道哪裡都可以\n" \
                        f"    ✨ 溫度、降雨機率通通有\n\n" \
                        f"💡 **超簡單使用**：直接點下面的按鈕，或是直接跟我說你想要什麼服務！"
                
            # 統一QuickReply按鈕（個人和群組完全一樣）
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="🔍 檢查網站安全", text=f"{bot_trigger_keyword} 請幫我分析這則訊息：")),
                QuickReplyButton(action=MessageAction(label="🎯 防詐騙測驗", text=f"{bot_trigger_keyword} 防詐騙測試")),
                QuickReplyButton(action=MessageAction(label="📚 詐騙案例", text=f"{bot_trigger_keyword} 詐騙類型列表")),
                QuickReplyButton(action=MessageAction(label="☁️ 查詢天氣", text=f"{bot_trigger_keyword} 今天天氣"))
            ])
            
            # 統一使用mention功能（個人和群組完全一樣）
            mention_text = f"@{display_name} {reply_text}"
            if len(mention_text) <= LINE_MESSAGE_MAX_LENGTH:
                reply_text = mention_text
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
            
            # 統一發送彩色的Flex Message按鈕（群組和個人聊天都一樣）
            try:
                import time
                time.sleep(1)  # 稍等一下再發送按鈕
                
                # 創建統一的彩色Flex Message按鈕
                unified_flex = FlexSendMessage(
                    alt_text="土豆的服務選單",
                    contents=BubbleContainer(
                        size="kilo",
                        header=BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(
                                    text="🥔 土豆的服務選單",
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
                                ),
                                ButtonComponent(
                                    style="primary",
                                    color="#96CEB4",
                                    action=MessageAction(
                                        label="☁️ 查詢天氣", 
                                        text=f"{bot_trigger_keyword} 今天天氣"
                                    )
                                )
                            ]
                        )
                    )
                )
                
                # 統一發送到正確的目標
                if is_group_message:
                    line_bot_api.push_message(event.source.group_id, unified_flex)
                else:
                    line_bot_api.push_message(user_id, unified_flex)
                logger.info("已發送統一的彩色Flex Message按鈕")
                
            except Exception as e:
                logger.error(f"發送統一按鈕時發生錯誤: {e}")
            
            return

        # 處理遊戲觸發 - 移到詐騙檢測前面
        if is_game_trigger(cleaned_message):
            logger.info(f"檢測到防詐騙測試觸發: {cleaned_message}")
            flex_message, error_message = start_potato_game(user_id)
            
            if flex_message:
                line_bot_api.reply_message(reply_token, flex_message)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
            return

        # 檢查用戶詢問詐騙類型清單
        if any(keyword in cleaned_message for keyword in ["詐騙類型", "詐騙手法", "詐騙種類", "常見詐騙"]):
            fraud_list = "🚨 **常見詐騙類型一覽** 🚨\n\n"
            for fraud_type, description in fraud_types.items():
                fraud_list += f"🔸 **{fraud_type}**\n   {description[:50]}...\n\n"
            
            fraud_list += "💡 如需詳細了解某個詐騙類型，請直接輸入該詐騙名稱！\n\n"
            fraud_list += "⚠️ 如果收到可疑訊息，請直接傳給我分析喔！"
            
            # 截斷過長的訊息
            if len(fraud_list) > LINE_MESSAGE_SAFE_LENGTH:
                fraud_list = fraud_list[:LINE_MESSAGE_SAFE_LENGTH] + "\n\n(更多資訊請分別查詢各詐騙類型)"
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=fraud_list))
            return

        # 檢查是否詢問特定詐騙類型
        for fraud_type, description in fraud_types.items():
            if fraud_type in cleaned_message:
                response_text = f"🚨 **{fraud_type}詳細說明** 🚨\n\n"
                response_text += f"📋 **說明**：{description}\n\n"
                response_text += "💡 **防範建議**：\n"
                response_text += "🛡️ 遇到任何要求提供個人資料或金錢的情況，請先暫停並諮詢家人\n"
                response_text += "🔍 對於可疑訊息，可以傳給我幫您分析\n"
                response_text += "📞 如有疑慮，請撥打165反詐騙專線\n\n"
                response_text += f"如果您收到疑似{fraud_type}的訊息，歡迎直接傳給我分析！"
                
                line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text))
                return

        # 檢查是否為分析請求但沒有內容
        analysis_request_keywords = ["請幫我分析這則訊息", "幫我分析訊息", "請分析這則訊息", "請幫我分析", "分析這則訊息"]
        is_analysis_request = any(keyword in cleaned_message for keyword in analysis_request_keywords)
        
        # 如果是分析請求但內容太短或只是請求本身，則提示用戶提供內容
        if is_analysis_request and (len(cleaned_message) < 20 or cleaned_message.rstrip("：:") in analysis_request_keywords):
            logger.info(f"檢測到分析請求但沒有提供具體內容: {cleaned_message}")
            
            # 設置用戶狀態為等待分析
            current_state["waiting_for_analysis"] = True
            user_conversation_state[user_id] = current_state
            
            prompt_message = f"好的 {display_name}，我會幫您分析可疑訊息！\n\n" \
                           f"請直接把您收到的可疑訊息或網址傳給我，我會立即為您分析風險程度。\n\n" \
                           f"💡 您可以：\n" \
                           f"• 轉傳可疑的文字訊息\n" \
                           f"• 貼上可疑的網址連結\n" \
                           f"• 描述您遇到的可疑情況"
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=prompt_message))
            return

        # 執行詐騙分析
        if should_perform_fraud_analysis(cleaned_message, user_id) or waiting_for_analysis:
            logger.info(f"開始詐騙分析: {cleaned_message[:50]}...")
            
            # 清除等待分析狀態
            if waiting_for_analysis:
                current_state["waiting_for_analysis"] = False
                user_conversation_state[user_id] = current_state
            
            # 分析前先發送等待訊息（在重要分析時）
            should_send_wait = len(cleaned_message) > 100 or any(url_word in cleaned_message.lower() for url_word in ['http', 'www', '.com', '.tw'])
            if should_send_wait:
                wait_message = "🔍 正在分析中，請稍候..."
                line_bot_api.reply_message(reply_token, TextSendMessage(text=wait_message))
            
            analysis_result = detect_fraud_with_chatgpt(cleaned_message, display_name, user_id)
            
            if analysis_result["success"]:
                # 記錄到Firebase
                try:
                    firebase_manager.save_user_interaction(
                        user_id=user_id,
                        display_name=display_name,
                        message=cleaned_message,
                        response=str(analysis_result["result"]),
                        is_fraud_related=True,
                        fraud_type=analysis_result["result"].get("fraud_type"),
                        risk_level=analysis_result["result"].get("risk_level")
                    )
                except Exception as e:
                    logger.error(f"記錄到Firebase時發生錯誤: {e}")
                
                # 檢查是否為網域變形攻擊
                if analysis_result["result"].get("is_domain_spoofing", False):
                    spoofing_result = analysis_result["result"]["spoofing_result"]
                    flex_message = create_domain_spoofing_flex_message(spoofing_result, display_name, cleaned_message)
                    
                    if should_send_wait:
                        # 使用push message發送結果（因為已經用過reply了）
                        try:
                            if event.source.type == 'group':
                                # 群組訊息：發送到群組
                                line_bot_api.push_message(event.source.group_id, flex_message)
                            else:
                                # 個人訊息：發送到個人
                                line_bot_api.push_message(user_id, flex_message)
                        except LineBotApiError as e:
                            logger.error(f"LINE API錯誤: {e}")
                            if e.status_code == 429:
                                # 達到月度限制，發送簡單文字訊息
                                simple_warning = f"⚠️ 高風險警告！\\n\\n{spoofing_result.get('risk_explanation', '這個網址可能是詐騙網站')}"
                                try:
                                    line_bot_api.reply_message(reply_token, TextSendMessage(text=simple_warning))
                                except:
                                    logger.error("無法發送簡單警告訊息")
                    else:
                        try:
                            line_bot_api.reply_message(reply_token, flex_message)
                        except LineBotApiError as e:
                            logger.error(f"LINE API錯誤: {e}")
                            if e.status_code == 429:
                                # 達到月度限制，發送簡單文字訊息
                                simple_warning = f"⚠️ 高風險警告！\\n\\n{spoofing_result.get('risk_explanation', '這個網址可能是詐騙網站')}"
                                line_bot_api.reply_message(reply_token, TextSendMessage(text=simple_warning))
                            else:
                                # 其他API錯誤，嘗試發送簡單訊息
                                simple_warning = f"⚠️ 檢測到可疑網址！\\n\\n{spoofing_result.get('risk_explanation', '請小心這個網站')}"
                                line_bot_api.reply_message(reply_token, TextSendMessage(text=simple_warning))
                else:
                    # 一般詐騙分析結果
                    flex_message = create_analysis_flex_message(analysis_result["result"], display_name, cleaned_message)
                    
                    if should_send_wait:
                        # 使用push message發送結果（因為已經用過reply了）
                        try:
                            if event.source.type == 'group':
                                # 群組訊息：發送到群組
                                line_bot_api.push_message(event.source.group_id, flex_message)
                            else:
                                # 個人訊息：發送到個人
                                line_bot_api.push_message(user_id, flex_message)
                        except LineBotApiError as e:
                            logger.error(f"LINE API錯誤: {e}")
                            if e.status_code == 429:
                                # 達到月度限制，發送簡單文字訊息
                                simple_result = f"📊 分析結果\\n\\n{analysis_result['result'].get('explanation', '請小心這個訊息')}"
                                try:
                                    line_bot_api.reply_message(reply_token, TextSendMessage(text=simple_result))
                                except:
                                    logger.error("無法發送簡單分析結果")
                    else:
                        try:
                            line_bot_api.reply_message(reply_token, flex_message)
                        except LineBotApiError as e:
                            logger.error(f"LINE API錯誤: {e}")
                            if e.status_code == 429:
                                # 達到月度限制，發送簡單文字訊息
                                simple_result = f"📊 分析結果\\n\\n{analysis_result['result'].get('explanation', '請小心這個訊息')}"
                                line_bot_api.reply_message(reply_token, TextSendMessage(text=simple_result))
                            else:
                                # 其他API錯誤，嘗試發送簡單訊息
                                simple_result = f"📊 分析完成\\n\\n{analysis_result['result'].get('explanation', '分析結果已產生')}"
                                line_bot_api.reply_message(reply_token, TextSendMessage(text=simple_result))
                
                # 隨機顯示贊助信息
                if random.random() < DONATION_SHOW_PROBABILITY:
                    try:
                        donation_flex = create_donation_flex_message()
                        line_bot_api.push_message(user_id, donation_flex)
                    except Exception as e:
                        logger.error(f"發送贊助訊息時發生錯誤: {e}")
            else:
                error_message = f"抱歉，分析過程中遇到問題：{analysis_result['message']}\n\n如果是緊急情況，建議您：\n🚫 暫時不要點擊任何連結\n📞 撥打165反詐騙專線諮詢\n👨‍👩‍👧‍👦 請家人朋友幫忙確認"
                
                if should_send_wait:
                    line_bot_api.push_message(user_id, TextSendMessage(text=error_message))
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
            
            return

        # 檢查是否詢問功能
        if any(keyword in cleaned_message for keyword in function_inquiry_keywords):
            reply_text = f"嗨嗨 {display_name}！我是土豆 🥔 很開心你問我！\n\n" \
                        f"我是專業的防詐騙小助手，經過全面測試，已經準備好用四項超強服務保護你：\n\n" \
                        f"🔍 **網站安全檢查**\n" \
                        f"    ✨ 把可疑網址丟給我，我立刻幫你檢查安全性\n" \
                        f"    ✨ 自動抓出假冒購物網站、釣魚網站等壞蛋\n\n" \
                        f"🎯 **防詐騙知識測驗**\n" \
                        f"    ✨ 跟我玩問答遊戲，提升你的防詐騙能力\n" \
                        f"    ✨ 學會識破31種常見詐騙手法\n\n" \
                        f"📚 **詐騙案例查詢**\n" \
                        f"    ✨ 真實詐騙案例分析，讓你看清騙子手法\n" \
                        f"    ✨ 涵蓋9大類詐騙類型完整說明\n\n" \
                        f"☁️ **天氣預報查詢**\n" \
                        f"    ✨ 台灣各縣市即時天氣，想知道哪裡都可以\n" \
                        f"    ✨ 溫度、降雨機率通通有\n\n" \
                        f"💡 **超簡單使用**：直接點下面的按鈕，或是直接跟我說你想要什麼服務！"
            
            # 統一QuickReply按鈕（個人和群組完全一樣）
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="🔍 檢查網站安全", text=f"{bot_trigger_keyword} 請幫我分析這則訊息：")),
                QuickReplyButton(action=MessageAction(label="🎯 防詐騙測驗", text=f"{bot_trigger_keyword} 防詐騙測試")),
                QuickReplyButton(action=MessageAction(label="📚 詐騙案例", text=f"{bot_trigger_keyword} 詐騙類型列表")),
                QuickReplyButton(action=MessageAction(label="☁️ 查詢天氣", text=f"{bot_trigger_keyword} 今天天氣"))
            ])
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
            
            # 統一發送彩色的Flex Message按鈕（群組和個人聊天都一樣）
            try:
                import time
                time.sleep(1)  # 稍等一下再發送按鈕
                
                # 創建統一的彩色Flex Message按鈕
                unified_flex = FlexSendMessage(
                    alt_text="土豆的服務選單",
                    contents=BubbleContainer(
                        size="kilo",
                        header=BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(
                                    text="🥔 土豆的服務選單",
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
                                ),
                                ButtonComponent(
                                    style="primary",
                                    color="#96CEB4",
                                    action=MessageAction(
                                        label="☁️ 查詢天氣", 
                                        text=f"{bot_trigger_keyword} 今天天氣"
                                    )
                                )
                            ]
                        )
                    )
                )
                
                # 統一發送到正確的目標
                if is_group_message:
                    line_bot_api.push_message(event.source.group_id, unified_flex)
                else:
                    line_bot_api.push_message(user_id, unified_flex)
                logger.info("已發送統一的彩色Flex Message按鈕")
                
            except Exception as e:
                logger.error(f"發送統一按鈕時發生錯誤: {e}")
            
            return

        # 處理詐騙類型列表查詢
        if any(keyword in cleaned_message for keyword in ["詐騙類型列表", "詐騙類型", "詐騙手法", "詐騙種類", "常見詐騙"]):
            logger.info(f"檢測到詐騙類型查詢: {cleaned_message}")
            
            try:
                from fraud_knowledge import load_fraud_tactics
                fraud_tactics = load_fraud_tactics()
                
                if fraud_tactics:
                    # 創建詐騙類型列表Flex訊息
                    fraud_types_flex = create_fraud_types_flex_message(fraud_tactics, display_name)
                    line_bot_api.reply_message(reply_token, fraud_types_flex)
                else:
                    error_text = "抱歉，詐騙類型資料載入失敗。\\n\\n💡 您可以：\\n• 直接傳送可疑訊息給我分析\\n• 說「防詐騙測試」進行知識測驗"
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
            except Exception as e:
                logger.error(f"處理詐騙類型查詢時發生錯誤: {e}")
                error_text = "抱歉，詐騙類型查詢功能暫時無法使用。\\n\\n💡 您可以：\\n• 直接傳送可疑訊息給我分析\\n• 說「防詐騙測試」進行知識測驗"
                line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
            return

        # 處理天氣查詢
        if is_weather_related(cleaned_message):
            logger.info(f"檢測到天氣查詢: {cleaned_message}")
            weather_result = handle_weather_query(cleaned_message)
            
            if weather_result["success"]:
                # 創建天氣Flex訊息
                weather_flex = create_weather_flex_message(weather_result["data"])
                line_bot_api.reply_message(reply_token, weather_flex)
            else:
                # 發送錯誤訊息
                error_text = f"抱歉，{weather_result['message']}\\n\\n💡 您可以試著這樣問：\\n• 今天天氣如何\\n• 台北天氣\\n• 明天會下雨嗎"
                line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
            return

        # 一般聊天回應
        logger.info(f"進入一般聊天模式: {cleaned_message}")
        try:
            chat_response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                 {"role": "system", "content": "你是一位名為「土豆」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。你的說話風格要：\\n1. 非常簡單易懂，像鄰居朋友在聊天\\n2. 用溫暖親切的語氣，不要太正式\\n3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號\\n4. 避免複雜的專業術語，用日常生活的話來解釋\\n5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議\\n6. 回應要簡短，不要太長篇大論"},
                 {"role": "user", "content": cleaned_message}
                ],
                temperature=CHAT_TEMPERATURE,
                max_tokens=CHAT_MAX_TOKENS
            )
            
            if chat_response and chat_response.choices:
                chat_reply = chat_response.choices[0].message.content.strip()
                
                # 隨機添加防詐小知識
                if random.random() < CHAT_TIP_PROBABILITY:
                    tips = get_anti_fraud_tips()
                    if tips:
                        random_tip = random.choice(tips)
                        chat_reply += f"\\n\\n💡 小提醒：{random_tip}"
                
                # 確保回覆不會太長
                if len(chat_reply) > LINE_MESSAGE_SAFE_LENGTH:
                    chat_reply = chat_reply[:LINE_MESSAGE_SAFE_LENGTH] + "..."
                
                introduction = f"\\n\\n💫 我是您的專業防詐騙助手！經過全面測試，我能為您提供：\\n🔍 網站安全檢查\\n🎯 防詐騙知識測驗\\n📚 詐騙案例查詢\\n☁️ 天氣預報查詢\\n\\n有任何可疑訊息都歡迎直接傳給我分析喔！"
                
                # 如果是首次聊天，添加自我介紹
                if user_id not in first_time_chatters:
                    first_time_chatters.add(user_id)
                    if len(chat_reply + introduction) <= LINE_MESSAGE_SAFE_LENGTH:
                        chat_reply += introduction
                
                line_bot_api.reply_message(reply_token, TextSendMessage(text=chat_reply))
            else:
                fallback_message = "我現在有點忙，不過如果您有可疑訊息需要分析，我隨時可以幫忙喔！ 😊"
                line_bot_api.reply_message(reply_token, TextSendMessage(text=fallback_message))
                
        except Exception as e:
            logger.exception(f"生成聊天回應時發生錯誤: {e}")
            fallback_message = "不好意思，我現在有點狀況，不過如果您有可疑訊息需要分析，我隨時可以幫忙！ 😊"
            line_bot_api.reply_message(reply_token, TextSendMessage(text=fallback_message))

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
            # 解析postback數據
            if postback_data.startswith('action='):
                parts = postback_data.split('&')
                action_part = parts[0]
                action = action_part.split('=')[1]
                
                # 提取其他參數
                params = {}
                for part in parts[1:]:
                    if '=' in part:
                        key, value = part.split('=', 1)
                        params[key] = value
                
                logger.info(f"解析的動作: {action}, 參數: {params}")
                
                if action == 'start_potato_game':
                    # 開始防詐騙測試
                    flex_message, error_message = start_potato_game(user_id)
                    
                    if flex_message:
                        line_bot_api.reply_message(reply_token, flex_message)
                    else:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
                        
                elif action == 'potato_game_answer':
                    # 处理防詐騙測試答案 - 修复action名称不匹配问题
                    answer_index = int(params.get('answer', 0))
                    is_correct, result_flex = handle_potato_game_answer(user_id, answer_index)
                    line_bot_api.reply_message(reply_token, result_flex)
                    
                elif action == 'fraud_stats':
                    # 顯示詐騙統計（未來功能）
                    stats_message = "📊 詐騙統計功能開發中，敬請期待！\\n\\n目前可用功能：\\n🔍 詐騙訊息分析\\n🎯 防詐騙測試\\n📚 詐騙類型查詢"
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=stats_message))
                    
                else:
                    logger.warning(f"未知的postback動作: {action}")
                    line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，我不太明白您想要做什麼，請重新嘗試！"))
            else:
                logger.warning(f"無法解析的postback數據: {postback_data}")
                line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，我不太明白您想要做什麼，請重新嘗試！"))
                
        except Exception as e:
            logger.exception(f"處理postback事件時發生錯誤: {e}")
            line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，處理您的請求時發生錯誤，請稍後再試！"))

else:
    logger.warning("LINE Bot handler 未初始化，無法處理訊息事件")

def should_perform_fraud_analysis(message: str, user_id: str = None) -> bool:
    """判斷是否應該進行詐騙分析"""
    message_lower = message.lower().strip()
    
    # 如果訊息太短，可能不需要分析
    if len(message_lower) < 3:
        return False
    
    # 排除明確的問候語
    greetings = ["你好", "哈囉", "嗨", "hi", "hello", "早安", "午安", "晚安", "再見", "謝謝", "感謝"]
    if any(greeting in message_lower for greeting in greetings) and len(message_lower) < 10:
        return False
    
    # 排除功能查詢
    if any(keyword in message_lower for keyword in function_inquiry_keywords):
        return False
    
    # 排除詐騙類型查詢
    if any(keyword in message_lower for keyword in ["詐騙類型", "詐騙手法", "詐騙種類", "常見詐騙"]):
        return False
    
    # 排除防詐騙測試觸發
    if is_game_trigger(message):
        return False
    
    # 排除天氣查詢
    if is_weather_related(message):
        return False
    
    # 排除純粹的分析請求（沒有具體內容要分析）
    analysis_request_keywords = ["請幫我分析這則訊息", "幫我分析訊息", "請分析這則訊息", "請幫我分析", "分析這則訊息"]
    if any(keyword in message and len(message) < 20 for keyword in analysis_request_keywords):
        return False
    
    # 排除一般遊戲討論（而非真正的遊戲觸發）
    game_chat_patterns = ["遊戲推薦", "遊戲好玩", "什麼遊戲", "遊戲有趣"]
    if any(pattern in message_lower for pattern in game_chat_patterns):
        return False
    
    # 檢查URL存在（最高優先級）
    import re
    url_pattern = re.compile(r'https?://[^\\s]+|www\\.[^\\s]+|[a-zA-Z0-9][a-zA-Z0-9-]*\\.[a-zA-Z]{2,}(?:\\.[a-zA-Z]{2,})?')
    if url_pattern.search(message):
        logger.info("檢測到URL，觸發詐騙分析")
        return True
    
    # 檢查明確的分析請求（但要有具體內容）
    explicit_analysis_requests = [
        "這是詐騙嗎", "這可靠嗎", "這是真的嗎", 
        "這安全嗎", "可以相信嗎", "有問題嗎", "是騙人的嗎"
    ]
    if any(request in message_lower for request in explicit_analysis_requests):
        logger.info("檢測到明確分析請求")
        return True
    
    # 檢查分析關鍵詞+疑問詞的組合
    analysis_keywords = ["分析", "詐騙", "安全", "可疑", "風險", "網站", "連結", "投資", "賺錢"]
    question_words = ["嗎", "呢", "吧", "?", "？"]
    
    has_analysis_keyword = any(keyword in message_lower for keyword in analysis_keywords)
    has_question_word = any(word in message_lower for word in question_words)
    
    if has_analysis_keyword and has_question_word:
        logger.info("檢測到分析關鍵詞+疑問詞組合")
        return True
    
    # 檢查多個詐騙關鍵詞
    fraud_keywords = ["詐騙", "被騙", "轉帳", "匯款", "投資", "賺錢", "兼職", "工作", "銀行", "帳號", "密碼", "個資", "中獎", "免費", "限時", "急"]
    fraud_count = sum(1 for keyword in fraud_keywords if keyword in message_lower)
    
    if fraud_count >= 2:
        logger.info(f"檢測到 {fraud_count} 個詐騙關鍵詞")
        return True
    
    return False

# 修正self引用問題
def _is_legitimate_subdomain(subdomain_part):
    """檢查子網域部分是否合法"""
    # 合法的子網域特徵
    if not subdomain_part or len(subdomain_part) > 20:  # 太長的子網域可疑
        return False
    
    # 常見的合法子網域前綴
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
        'en', 'english', 'zh', 'chinese'
    ]
    
    # 檢查是否為已知的合法前綴
    if subdomain_part.lower() in legitimate_prefixes:
        return True
    
    # 檢查是否包含可疑字元或模式
    suspicious_patterns = [
        '-tw-', '-official-', '-secure-', '-login-', '-bank-',
        'phishing', 'fake', 'scam', 'fraud', 'malware'
    ]
    
    for pattern in suspicious_patterns:
        if pattern in subdomain_part.lower():
            return False
    
    # 檢查是否只包含字母、數字和連字符
    import re
    if not re.match(r'^[a-zA-Z0-9-]+$', subdomain_part):
        return False
    
    # 不能以連字符開始或結束
    if subdomain_part.startswith('-') or subdomain_part.endswith('-'):
        return False
    
    return True


if __name__ == '__main__':
    # 檢查環境變數
    validate_environment()
    
    # 取得端口號（Render 會提供 PORT 環境變數）
    port = int(os.environ.get('PORT', 5000))
    
    # 啟動 Flask 應用
    logger.info(f"啟動防詐騙機器人服務，端口: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
