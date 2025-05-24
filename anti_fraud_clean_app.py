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
from linebot.exceptions import InvalidSignatureError
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
    create_donation_flex_message, create_weather_flex_message
)
from game_service import (
    start_potato_game, handle_potato_game_answer, is_game_trigger, get_user_game_state
)

# 指定 .env 文件的路徑
# 假設 anti-fraud-clean 和 linebot-anti-fraud 是同級目錄
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'linebot-anti-fraud', '.env')
load_dotenv(dotenv_path=dotenv_path)

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
# - POTATO_GAME_TRIGGER_KEYWORDS (原 potato_game_trigger_keywords)  
# - BOT_TRIGGER_KEYWORD (原 bot_trigger_keyword)
# - ANALYSIS_PROMPTS (原 analysis_prompts)

# 為了向下兼容，保留舊的變數名稱
function_inquiry_keywords = FUNCTION_INQUIRY_KEYWORDS
follow_up_patterns = FOLLOW_UP_PATTERNS
potato_game_trigger_keywords = POTATO_GAME_TRIGGER_KEYWORDS
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
        
        url_pattern = re.compile(r'(https?://\S+|www\.\S+)')
        url_match = url_pattern.search(user_message)
        
        if url_match:
            original_url = url_match.group(0)
            # 確保URL開頭是http://或https://
            if not original_url.startswith(('http://', 'https://')):
                original_url = 'https://' + original_url
                
            # 展開可能的短網址
            original_url, expanded_url, is_short_url, url_expanded_successfully = expand_short_url(original_url)
            
            # 如果是短網址且成功展開，調整分析訊息
            if is_short_url and url_expanded_successfully:
                # 將原始訊息中的短網址替換為展開後的URL，以便於分析
                analysis_message = user_message.replace(original_url, f"{original_url} (展開後: {expanded_url})")
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
        # 提取URL進行精確匹配
        url_pattern = re.compile(r'https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}[^\s]*')
        urls = url_pattern.findall(analysis_message)
        
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
        for url in urls:
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
        你是一個詐騙風險評估專家，專門為50歲以上的中老年人提供易懂的風險分析。
        請分析以下信息是否包含詐騙相關內容，並按照以下格式輸出結果：
        
        風險等級：（低風險、中風險、高風險）
        詐騙類型：（如果有詐騙風險，請指出具體類型，例如：假網購、假交友、假投資、假貸款、假求職等；如果無風險，填"無"）
        說明：（請用非常口語化、親切的語氣說明判斷依據，避免使用專業術語，就像在跟鄰居阿姨聊天一樣。例如不要說「此網站使用混淆技術規避檢測」，而是說「這個網站看起來怪怪的，網址跟正常的不一樣，可能是假冒的」。語言要簡單直白，不要太長篇大論）
        建議：（針對潛在風險，用🚫🔍🌐🛡️💡⚠️等emoji符號代替數字編號，提供2-3點簡單易懂的建議，例如「🚫 不要點這個連結」「🔍 先問問家人這是什麼」「🛡️ 不要提供銀行帳號」等）
        新興手法：是/否
        
        {special_notes}
        
        以下是需要分析的信息：
        ---
        {analysis_message}
        ---
        
        請用繁體中文回答，避免直接使用問候語。直接開始分析。回答應簡潔直接，像是鄰居阿姨給出的貼心提醒。
        """
        
        # 調用OpenAI API (修正為新版API格式)
        if not openai_client:
            logger.error("OpenAI客戶端未初始化，無法進行分析")
            return {
                "success": False,
                "message": "AI分析服務暫時不可用，請稍後再試"
            }
        
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "你是一個詐騙風險評估專家，請以50歲以上的長輩能理解的口語化方式分析詐騙風險。避免使用「您」「我」等主觀用詞，而是使用更直接的表述。提供的建議應該具體實用且直接，並且一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號。語言要像鄰居阿姨在關心提醒一樣親切簡單。"},
                {"role": "user", "content": openai_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        if response and response.choices:
            analysis_result = response.choices[0].message.content.strip()
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
        
        # 檢查是否包含觸發關鍵詞 "土豆"或者用戶處於等待分析狀態
        waiting_for_analysis = current_state.get("waiting_for_analysis", False)
        
        # 如果是群組訊息，需要檢查是否包含觸發關鍵詞，或者用戶處於等待分析狀態
        if is_group_message and bot_trigger_keyword not in text_message and not waiting_for_analysis:
            logger.info(f"群組訊息不包含觸發關鍵詞 '{bot_trigger_keyword}'，也不在等待分析狀態，忽略此訊息")
            return

        # 如果是群組訊息且包含觸發關鍵詞，移除關鍵詞以處理實際命令
        if is_group_message and bot_trigger_keyword in text_message:
            text_message = text_message.replace(bot_trigger_keyword, "").strip()
            logger.info(f"移除觸發關鍵詞後的訊息: {text_message}")
        
        # 如果上一次的互動是請求分析，則設置等待分析狀態
        if any(text_message.strip() == prompt or text_message.strip() == prompt.rstrip("：") for prompt in analysis_prompts):
            current_state["waiting_for_analysis"] = True
            user_conversation_state[user_id] = current_state
            logger.info(f"用戶 {user_id} 進入等待分析狀態")
        elif any(pattern in text_message.lower() for pattern in follow_up_patterns):
            current_state["waiting_for_analysis"] = True
            user_conversation_state[user_id] = current_state
            logger.info(f"用戶 {user_id} 可能遇到詐騙，進入等待分析狀態")
        elif contains_url(text_message) and waiting_for_analysis:
            # 如果消息包含URL且用戶處於等待分析狀態，保持等待分析狀態
            current_state["waiting_for_analysis"] = True
            user_conversation_state[user_id] = current_state
            logger.info(f"用戶 {user_id} 提供了URL，保持等待分析狀態")
        elif waiting_for_analysis and should_perform_fraud_analysis(text_message):
            # 用戶處於等待分析狀態且這個消息看起來是需要分析的內容
            current_state["waiting_for_analysis"] = False  # 分析完後重置狀態
            user_conversation_state[user_id] = current_state
            logger.info(f"用戶 {user_id} 在等待分析狀態下發送了需要分析的內容")
            # 其他情況，重置等待分析狀態
            current_state["waiting_for_analysis"] = False
            user_conversation_state[user_id] = current_state
        
        # 如果移除關鍵詞後訊息為空，則發送功能說明
        if not text_message:
            reply_text = f"您好！我是防詐騙小幫手，我的功能包括：\n\n" \
                            f"1️⃣ 詐騙風險分析：我可以分析您收到的可疑訊息，評估是否為詐騙\n\n" \
                            f"2️⃣ 詐騙類型查詢：您可以輸入「詐騙類型列表」查看各種常見詐騙\n\n" \
                            f"3️⃣ 「選哪顆土豆」小遊戲：通過遊戲學習辨識詐騙訊息\n\n" \
                            f"請選擇您想嘗試的功能："
                
            # 如果在群組中，QuickReply按鈕需要包含觸發關鍵詞
            if is_group_message:
                quick_reply = QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="分析可疑訊息", text=f"{bot_trigger_keyword} 請幫我分析這則訊息：")),
                    QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆")),
                    QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text=f"{bot_trigger_keyword} 詐騙類型列表"))
                ])
                # 在群組中使用mention功能
                mention_message = create_mention_message(reply_text, display_name, user_id, quick_reply)
                line_bot_api.reply_message(reply_token, mention_message)
            else:
                quick_reply = QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
                    QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                    QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
                ])
                line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
            
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "回覆功能說明", is_fraud_related=False)
            return

        # 處理「選哪顆土豆」遊戲觸發
        if any(keyword in text_message.lower() for keyword in potato_game_trigger_keywords):
            logger.info(f"User {user_id} triggered potato game.")
            firebase_manager.save_user_interaction(
                user_id, display_name, text_message, 
                "啟動「選哪顆土豆」遊戲", is_fraud_related=False
            )
            
            # 使用新的模組化遊戲服務
            flex_message, error = start_potato_game(user_id)
            if flex_message:
                line_bot_api.reply_message(reply_token, flex_message)
            else:
                error_text = error or "遊戲啟動失敗，請稍後再試！"
                if is_group_message:
                    mention_message = create_mention_message(error_text, display_name, user_id)
                    line_bot_api.reply_message(reply_token, mention_message)
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
            return

        # 處理詐騙類型列表查詢
        if text_message.lower() == "詐騙類型列表" or text_message.lower() == "詐騙類型":
            logger.info(f"User {user_id} is querying fraud types list")
            types_text = "目前已收集的詐騙類型有：\n"
            for f_type, info in fraud_types.items():
                types_text += f"\n⚠️ {f_type}：\n{info['description']}\n"
            
            types_text += "\n想了解特定類型，可以問我「什麼是[詐騙類型]」喔！"

            quick_reply_items = []
            for f_type in list(fraud_types.keys())[:4]:  # 只取前4個詐騙類型作為快速回覆
                if is_group_message:
                    quick_reply_items.append(QuickReplyButton(action=MessageAction(label=f_type, text=f"{bot_trigger_keyword} 什麼是{f_type}")))
                else:
                    quick_reply_items.append(QuickReplyButton(action=MessageAction(label=f_type, text=f"什麼是{f_type}")))

            # 在群組中回覆時前綴用戶名稱
            if is_group_message:
                mention_message = create_mention_message(types_text, display_name, user_id, 
                    QuickReply(items=quick_reply_items) if quick_reply_items else None)
                line_bot_api.reply_message(reply_token, mention_message)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=types_text, 
                    quick_reply=QuickReply(items=quick_reply_items) if quick_reply_items else None))
            
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "Provided list of fraud types", is_fraud_related=False)
            return
            
        # 處理特定詐騙類型資訊查詢 (例如 "什麼是網路購物詐騙")
        specific_type_query_match = re.match(r"^(什麼是|查詢|我想了解|我想知道)(.+詐騙)$", text_message.strip())
        if specific_type_query_match:
            query_type = specific_type_query_match.group(2).strip()
            logger.info(f"User {user_id} is querying about specific fraud type: {query_type}")
            
            matched_fraud_type = None
            for f_type, info in fraud_types.items():
                if query_type in f_type or f_type in query_type:
                    matched_fraud_type = f_type
                    break
            
            if matched_fraud_type:
                info = fraud_types[matched_fraud_type]
                response_text = f"⚠️ {matched_fraud_type} ⚠️\n\n{info['description']}\n\n"
                
                if info.get('examples') and len(info['examples']) > 0:
                    response_text += "📋 案例：\n" + info['examples'][0] + "\n\n"
                
                if info.get('sop') and len(info['sop']) > 0:
                    response_text += "🛡️ 防範方法：\n" + "\n".join(info['sop'][:5]) + "\n"
                
                if is_group_message:
                    mention_message = create_mention_message(response_text, display_name, user_id, 
                        QuickReply(items=[
                            QuickReplyButton(action=MessageAction(label="查看其他詐騙類型", text=f"{bot_trigger_keyword} 詐騙類型列表")),
                            QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆")),
                            QuickReplyButton(action=MessageAction(label="分析可疑訊息", text=f"{bot_trigger_keyword} 請幫我分析這則訊息："))
                        ])
                    )
                    line_bot_api.reply_message(reply_token, mention_message)
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text, 
                        quick_reply=QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="查看其他詐騙類型", text="詐騙類型列表")),
                    QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                    QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息："))
                        ])))
                
                firebase_manager.save_user_interaction(user_id, display_name, text_message, f"Provided info about {matched_fraud_type}", is_fraud_related=False)
                return
            else:
                # 未找到匹配的詐騙類型，給出一般性回覆
                response_text = f"抱歉，我目前沒有關於「{query_type}」的詳細資訊。\n\n以下是我已收集的詐騙類型，您可以查詢這些："
                for f_type in fraud_types.keys():
                    response_text += f"\n- {f_type}"
                
                if is_group_message:
                    mention_message = create_mention_message(response_text, display_name, user_id, 
                        QuickReply(items=[
                            QuickReplyButton(action=MessageAction(label="查看詐騙類型列表", text=f"{bot_trigger_keyword} 詐騙類型列表")),
                            QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆"))
                        ])
                    )
                    line_bot_api.reply_message(reply_token, mention_message)
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text, 
                        quick_reply=QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="查看詐騙類型列表", text="詐騙類型列表")),
                    QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆"))
                        ])))
                
                firebase_manager.save_user_interaction(user_id, display_name, text_message, "Responded to unknown fraud type query", is_fraud_related=False)
                return

        # 檢查是否為請求分析的提示語
        if any(text_message.strip() == prompt or text_message.strip() == prompt.rstrip("：") for prompt in analysis_prompts):
            logger.info(f"User {user_id} requested message analysis but didn't provide message content")
            
            # 使用隨機回覆，讓機器人回應更加多樣化
            prompt_replies = [
                f"{display_name}，您好！請將可疑的訊息或網址貼給我，我會馬上分析是否有詐騙風險。可以是陌生人傳來的連結、可疑的購物網站，或任何讓您不安的訊息。",
                f"好的，{display_name}！想知道某個網址或訊息是否安全？請直接貼上來，我會立刻為您檢查風險。無論是社群媒體連結、購物網站還是奇怪的訊息都可以。",
                f"沒問題，{display_name}！要分析什麼訊息或網址呢？請完整複製貼上您想查證的內容，像是陌生來電要求的操作、可疑網址或社群媒體訊息都可以。",
                f"收到！{display_name}，請直接將您懷疑的訊息或網址複製給我，特別是含有連結、要求個人資料或提到錢的訊息，我會立刻幫您辨識風險。"
            ]
            
            selected_reply = random.choice(prompt_replies)
            
            if is_group_message:
                quick_reply = QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆")),
                    QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text=f"{bot_trigger_keyword} 詐騙類型列表"))
                ])
                # 在群組中使用mention功能
                mention_message = create_mention_message(selected_reply, display_name, user_id, quick_reply)
                line_bot_api.reply_message(reply_token, mention_message)
            else:
                quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
            ])
            line_bot_api.reply_message(reply_token, TextSendMessage(text=selected_reply, quick_reply=quick_reply))
            
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "Responded to analysis request prompt", is_fraud_related=False)
            return

        # 預設使用ChatGPT進行閒聊回應或詐騙分析
        logger.info(f"Message from {user_id}: {text_message} - Determining if fraud analysis is needed")
        
        # 初始化變量
        reply_text = ""
        is_fraud_related = False
        
        # 判斷是否需要進行詐騙分析
        if should_perform_fraud_analysis(text_message):
            logger.info(f"Performing fraud analysis for message from {user_id}: {text_message}")
            # 使用現有的詐騙分析邏輯，傳入user_id
            analysis_result = detect_fraud_with_chatgpt(text_message, display_name, user_id)
            
            if analysis_result and analysis_result.get("success", False):
                analysis_data = analysis_result.get("result", {})
                raw_result = analysis_result.get("raw_result", "")

                risk_level = analysis_data.get("risk_level", "不確定")
                fraud_type = analysis_data.get("fraud_type", "未知")
                explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
                suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
                is_emerging = analysis_data.get("is_emerging", False)

                # 檢查是否是網域變形攻擊，如果是則使用專門的Flex Message
                if analysis_data.get("is_domain_spoofing", False):
                    spoofing_result = analysis_data.get("spoofing_result", {})
                    flex_message = create_domain_spoofing_flex_message(spoofing_result, display_name, text_message, user_id)
                elif analysis_data.get("is_donation_easter_egg", False):
                    flex_message = create_analysis_flex_message(analysis_data, display_name, text_message, user_id)
                else:
                    # 一般的詐騙分析，使用標準的Flex Message
                    flex_message = create_analysis_flex_message(analysis_data, display_name, text_message, user_id)
                
                # 在群組中增加前綴提及用戶
                if is_group_message and flex_message and isinstance(flex_message, FlexSendMessage):
                    # 使用官方的mention功能發送前綴通知
                    mention_message = create_mention_message("以下是您要求的詐騙風險分析：", display_name, user_id)
                    line_bot_api.push_message(group_id if group_id else user_id, mention_message)
                    
                # 發送Flex消息
                if flex_message:
                    line_bot_api.reply_message(reply_token, flex_message)
                else:
                    # 如果Flex消息創建失敗，發送基本文本消息
                    text_response = f"風險等級：{risk_level}\n詐騙類型：{fraud_type}\n\n分析：{explanation}\n\n建議：{suggestions}"
                    if is_group_message:
                        mention_message = create_mention_message(text_response, display_name, user_id)
                        line_bot_api.reply_message(reply_token, mention_message)
                    else:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))

                if is_emerging and fraud_type != "非詐騙相關":
                    # 新增詐騙手法記錄通知改為單獨推送，避免混淆Flex Message
                    emerging_text = "⚠️ 這可能是一種新的詐騙手法，我已經記錄下來了，謝謝您的資訊！"
                    if is_group_message:
                        mention_message = create_mention_message(emerging_text, display_name, user_id)
                        line_bot_api.push_message(group_id if group_id else user_id, mention_message)
                    else:
                        line_bot_api.push_message(user_id, TextSendMessage(text=emerging_text))
                    firebase_manager.save_emerging_fraud_report(user_id, display_name, text_message, raw_result)
                    
                is_fraud_related = True if fraud_type != "非詐騙相關" and risk_level not in ["無風險", "低"] else False
                    
                # 保存互動記錄到Firebase
                firebase_manager.save_user_interaction(
                    user_id, display_name, text_message, raw_result,
                    is_fraud_related=is_fraud_related,
                    fraud_type=fraud_type if is_fraud_related else None,
                    risk_level=risk_level if is_fraud_related else None
                )
                    
                # 以15%的機率顯示贊助信息
                if random.random() < 0.15:
                    logger.info(f"隨機觸發贊助信息顯示給用戶 {user_id}")
                    try:
                        # 延遲1秒發送，避免訊息堆疊
                        time.sleep(1)
                        donation_message = create_donation_flex_message()
                        # 使用push_message而不是reply_message
                        line_bot_api.push_message(group_id if is_group_message else user_id, donation_message)
                    except Exception as e:
                        logger.error(f"發送贊助訊息時發生錯誤: {e}")
            else:
                # 分析失敗的情況，發送錯誤消息
                error_message = analysis_result.get("message", "分析失敗，請稍後再試") if analysis_result else "分析失敗，請稍後再試"
                if is_group_message:
                    mention_message = create_mention_message(error_message, display_name, user_id)
                    line_bot_api.reply_message(reply_token, mention_message)
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
                
            return
        else:
            # 使用ChatGPT進行閒聊回應
            logger.info(f"Using chat response for message from {user_id}: {text_message}")
            
            try:
                # 獲取用戶最近的對話歷史
                recent_history = firebase_manager.get_recent_interactions(user_id, limit=5)
                
                # 準備對話歷史消息列表
                chat_history = []
                
                # 系統提示消息
                system_message = {
                    "role": "system", 
                    "content": "你是一位名為「土豆」的AI聊天機器人，專門幫助50-60歲的阿姨叔叔防範詐騙。你的說話風格要：\n1. 非常簡單易懂，像鄰居阿姨在聊天\n2. 用溫暖親切的語氣，不要太正式\n3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號\n4. 避免複雜的專業術語，用日常生活的話來解釋\n5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議\n6. 回應要簡短，不要太長篇大論"
                }
                
                # 如果成功獲取到歷史對話，則使用它們
                if recent_history:
                    # 將歷史對話轉換為ChatGPT格式
                    for interaction in recent_history:
                        # 用戶消息
                        if 'message' in interaction and interaction['message']:
                            chat_history.append({
                                "role": "user",
                                "content": interaction['message']
                            })
                        
                        # 機器人回應
                        if 'response' in interaction and interaction['response']:
                            chat_history.append({
                                "role": "assistant",
                                "content": interaction['response']
                            })
                    
                    logger.info(f"成功使用用戶歷史對話: {len(chat_history)} 條消息")
                else:
                    # 如果沒有歷史對話或發生錯誤，使用空的歷史
                    logger.info("無法獲取用戶歷史對話，使用空歷史")
                
                # 添加當前用戶消息
                current_user_message = {
                    "role": "user",
                    "content": text_message
                }
                
                # 構建完整的消息列表
                messages = [system_message] + chat_history + [current_user_message]
                
                # 限制消息數量，避免超出API限制
                if len(messages) > 10:
                    # 保留系統消息和最近的對話
                    messages = [system_message] + messages[-9:]
                
                logger.info(f"使用記憶功能，總共提供 {len(messages)} 條消息給ChatGPT")
                
                # 檢查OpenAI客戶端是否可用
                if not openai_client:
                    logger.warning("OpenAI客戶端未初始化，使用預設回應")
                    raise Exception("OpenAI客戶端不可用")
                
                # 使用更新後的OpenAI API格式
                chat_response = openai_client.chat.completions.create(
                    model=os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'),
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                chat_reply = chat_response.choices[0].message.content.strip()
                
                # 只在首次聊天時添加功能介紹
                is_first_time = user_id not in first_time_chatters
                if is_first_time:
                    first_time_chatters.add(user_id)
                    introduction = f"\n\n我是防詐騙機器人「土豆」，能幫您：\n🔍 分析可疑訊息\n🎯 測試您的防詐騙能力\n📚 查詢各類詐騙手法"
                    reply_text = chat_reply + introduction
                else:
                    reply_text = chat_reply
                
            except Exception as e:
                logger.error(f"閒聊回應錯誤: {e}")
                # 如果閒聊回應失敗，使用簡單的問候
                greetings = ["您好！", "嗨！", "哈囉！", "很高興見到您！", "您好呀！"]
                
                # 只在首次聊天時添加功能介紹
                is_first_time = user_id not in first_time_chatters
                if is_first_time:
                    first_time_chatters.add(user_id)
                    reply_text = f"{random.choice(greetings)}有什麼我能幫您的嗎？您可以輸入「功能」來了解我能做什麼。"
                else:
                    reply_text = f"{random.choice(greetings)}有什麼我能幫您的嗎？"
            
            # 添加功能按鈕到閒聊回覆
            if is_group_message:
                quick_reply = QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="分析可疑訊息", text=f"{bot_trigger_keyword} 請幫我分析這則訊息：")),
                    QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆")),
                    QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text=f"{bot_trigger_keyword} 詐騙類型列表"))
                ])
                
                # 檢查回覆長度，LINE限制5000字元
                if len(reply_text) > 4900:  # 留一些緩衝空間
                    reply_text = reply_text[:4900] + "...\n\n(回覆內容過長，已截斷)"
                
                mention_message = create_mention_message(reply_text, display_name, user_id, quick_reply)
                line_bot_api.reply_message(reply_token, mention_message)
            else:
                quick_reply = QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
                    QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                    QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
                ])
                
                # 檢查回覆長度，LINE限制5000字元
                if len(reply_text) > 4900:  # 留一些緩衝空間
                    reply_text = reply_text[:4900] + "...\n\n(回覆內容過長，已截斷)"
                
                line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
            
            # 保存互動記錄到Firebase
            firebase_manager.save_user_interaction(
                user_id, display_name, text_message, reply_text,
                is_fraud_related=is_fraud_related,
                fraud_type=None,
                risk_level=None
            )
            return  # 添加return語句，防止繼續執行後續邏輯
            return  # 添加return語句，防止繼續執行後續邏輯
            return  # 添加return語句，防止繼續執行後續邏輯

    @handler.add(PostbackEvent)
    def handle_postback(event):
        """处理PostbackEvent（按钮点击等）"""
        try:
            data = event.postback.data
            reply_token = event.reply_token
            user_id = event.source.user_id
            
            # 获取用户显示名称
            user_profile = get_user_profile(user_id)
            display_name = user_profile.display_name if user_profile else '朋友'
        
            logger.info(f"接收到來自用戶 {user_id} 的 Postback: {data}")
        
            # 解析 data 参数
            data_parts = data.split('&')
            data_params = {}
            
            for part in data_parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    data_params[key] = value
            
            # 获取 action 参数
            action = data_params.get('action', '')
            
            # 根据 action 参数处理不同的按钮点击
            
            # 处理土豆游戏答案 - 修复action名称不匹配问题
            if action == 'potato_game_answer':
                try:
                    answer_index = int(data_params.get('answer', 0))
                    is_correct, result_flex = handle_potato_game_answer(user_id, answer_index)
                    
                    if result_flex:
                        line_bot_api.reply_message(reply_token, result_flex)
                    else:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text="遊戲處理失敗，請稍後再試！"))
                        
                except Exception as e:
                    logger.error(f"處理遊戲答案時發生錯誤: {e}")
                    line_bot_api.reply_message(reply_token, TextSendMessage(text="遊戲處理失敗，請稍後再試！"))
                return
            
            # 处理新游戏请求
            elif action == 'start_potato_game':
                # 使用新的模組化遊戲服務
                flex_message, error = start_potato_game(user_id)
                if flex_message:
                    line_bot_api.reply_message(reply_token, flex_message)
                else:
                    error_text = error or "遊戲啟動失敗，請稍後再試！"
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
                return
            
            # 处理观看广告（暫時停用）
            elif action == 'view_ad':
                # 已暫停廣告功能，直接給用戶次數
                firebase_manager.increase_user_analysis_credits(user_id, amount=5)
                current_credits = firebase_manager.get_user_analysis_credits(user_id)
                
                line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=f"感謝您的支持！系統已為您增加5次分析機會，目前全面開放免費無限使用。")
                )
                
                # 記錄互動
                firebase_manager.save_user_interaction(
                    user_id, display_name, "請求免費分析次數", 
                    "已給予5次分析次數，現已開放免費無限使用", 
                    is_fraud_related=False
            )
                return
        
            # 处理赞助
            elif action == 'donate':
                amount = data_params.get('amount', 'small')
                
                # 根据赞助金额增加用户分析次数
                credits_to_add = 0
                donation_amount = "未知"
                
                if amount == 'small':
                    credits_to_add = 10
                    donation_amount = "NT$50"
                elif amount == 'medium':
                    credits_to_add = 30
                    donation_amount = "NT$100"
                elif amount == 'large':
                    credits_to_add = 100
                    donation_amount = "NT$250"
                
                firebase_manager.increase_user_analysis_credits(user_id, amount=credits_to_add)
                
                # 获取用户当前分析次数
                current_credits = firebase_manager.get_user_analysis_credits(user_id)
                
                # 发送确认消息 (修改為感謝支持的消息)
                line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=f"感謝您的{donation_amount}贊助！您已獲得{credits_to_add}次分析機會。感謝支持，目前系統已開放免費無限使用。")
                )
                
                # 记录互动
                firebase_manager.save_user_interaction(
                    user_id, display_name, f"贊助:{amount}", 
                    f"用戶贊助{donation_amount}獲得{credits_to_add}次分析次數", 
                    is_fraud_related=False
                )
                return

        except Exception as e:
            logger.error(f"處理 Postback 事件時發生錯誤: {e}")
            line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，處理 Postback 事件時出現錯誤。請稍後再試一次。"))
else:
    logger.warning("LINE Bot handler 未初始化，跳過事件處理器註冊")

@app.route("/watch-ad/<user_id>", methods=['GET'])
def watch_ad(user_id):
    """显示Unity广告的页面"""
    return render_template('watch_ad.html', user_id=user_id)

@app.route("/watch-ad", methods=['GET'])
def watch_ad_without_id():
    """处理LIFF重定向请求"""
    # 从LIFF获取用户ID，如果没有则返回通用页面
    return render_template('watch_ad.html')

@app.route("/ad-completed", methods=['POST'])
def ad_completed():
    """处理广告观看完成的回调"""
    data = request.json
    user_id = data.get('user_id')
    ad_type = data.get('ad_type', 'unity')
    
    if not user_id:
        return jsonify({'success': False, 'message': '缺少用戶ID'}), 400
    
    # 记录广告观看
    firebase_manager.record_ad_view(user_id, ad_type)
    
    # 增加用户分析次数 (根據需求修改為固定值)
    firebase_manager.increase_user_analysis_credits(user_id, amount=5)  # 直接給5次
    
    # 获取用户当前分析次数
    current_credits = firebase_manager.get_user_analysis_credits(user_id)
    
    # 尝试发送LINE消息通知用户 (修改消息，現在是免費使用)
    try:
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"恭喜您獲得5次分析機會！感謝您的支持，目前已開放免費無限使用。")
        )
    except Exception as e:
        logger.error(f"無法發送LINE通知: {e}")
    
    return jsonify({
        'success': True, 
        'message': f'恭喜！您已獲得5次分析機會，目前免費無限使用',
        'credits': "無限"
    })

# 添加贊助訊息Flex Message函數
def create_donation_flex_message():
    """創建贊助訊息的Flex Message"""
    try:
        # 確保URL格式正確包含https://
        donation_url = "https://buymeacoffee.com/todao_antifruad"
        logger.info(f"創建贊助Flex Message，使用URL: {donation_url}")
        
        flex_message = FlexSendMessage(
            alt_text="幫助我們維持服務品質",
            contents={
                "type": "bubble",
                # 移除hero部分，不再顯示圖片
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "感謝您使用防詐騙小幫手",
                            "weight": "bold",
                            "size": "xl",
                            "color": "#FF8C00"
                        },
                        {
                            "type": "text",
                            "text": "叔叔阿姨，最近詐騙真的好多喔！幸好有這個小幫手可以幫忙檢查。它就像我們派在您身邊的小保鑣一樣！👮‍♂️",
                            "margin": "md",
                            "wrap": True,
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": "不過這個小保鑣也需要補充體力（系統維護費啦～）。如果叔叔阿姨覺得它做得不錯，願意請它吃個『乖乖』（讓系統乖乖運作），我們會超級感動的！一點點心意，就能讓它更有力氣保護大家喔！💪",
                            "margin": "md",
                            "wrap": True,
                            "size": "md"
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "我要贊助",
                                "uri": donation_url
                            },
                            "color": "#FF8C00"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "您的支持是我們持續改進的動力",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "align": "center"
                                }
                            ],
                            "margin": "md"
                        }
                    ],
                    "flex": 0
                }
            }
        )
        
        return flex_message
    except Exception as e:
        logger.error(f"創建贊助Flex Message時發生錯誤: {e}")
        # 返回一個簡單的文本消息作為備用
        return TextSendMessage(text="感謝您的使用！如果覺得服務有幫助，歡迎贊助支持我們：https://buymeacoffee.com/todao_antifruad")

# 升級為使用LINE官方Text message v2的Mention功能
def create_mention_message(text, display_name, user_id, quick_reply=None):
    """創建帶有官方mention功能的消息，使用LINE Text message v2格式"""
    try:
        # 構建mention文本，格式為 "@用戶名 訊息內容"
        mention_text = f"@{display_name} {text}"
        
        # 計算mention的位置
        mention_start = 0
        mention_end = len(display_name) + 1  # +1 是因為@符號
        
        # 創建自定義的TextSendMessage類來支持mention
        class MentionTextSendMessage(TextSendMessage):
            def __init__(self, text, mention=None, quick_reply=None, **kwargs):
                super().__init__(text=text, quick_reply=quick_reply, **kwargs)
                self.mention = mention
            
            def as_json_dict(self):
                json_dict = super().as_json_dict()
                if self.mention:
                    json_dict['mention'] = self.mention
                return json_dict
        
        # 創建mention數據
        mention_data = {
            "mentionees": [
                {
                    "index": mention_start,
                    "length": mention_end,
                    "type": "user",
                    "userId": user_id
                }
            ]
        }
        
        # 創建包含mention的消息
        mention_message = MentionTextSendMessage(
            text=mention_text,
            mention=mention_data,
            quick_reply=quick_reply
        )
        
        logger.info(f"創建mention消息成功: @{display_name} (用戶ID: {user_id})")
        return mention_message
        
    except Exception as e:
        logger.error(f"創建mention消息時發生錯誤: {e}")
        # 降級到傳統@格式
    text_with_mention = f"@{display_name} {text}"
    return TextSendMessage(text=text_with_mention, quick_reply=quick_reply)

# 創建一個專門用於@所有人的mention功能
def create_mention_all_message(text, quick_reply=None):
    """創建@所有人的mention消息"""
    try:
        # 構建mention文本
        mention_text = f"@所有人 {text}"
        
        # 創建自定義的TextSendMessage類來支持mention
        class MentionTextSendMessage(TextSendMessage):
            def __init__(self, text, mention=None, quick_reply=None, **kwargs):
                super().__init__(text=text, quick_reply=quick_reply, **kwargs)
                self.mention = mention
            
            def as_json_dict(self):
                json_dict = super().as_json_dict()
                if self.mention:
                    json_dict['mention'] = self.mention
                return json_dict
        
        # 創建@所有人的mention數據
        mention_data = {
            "mentionees": [
                {
                    "index": 0,
                    "length": 4,  # "@所有人" 的長度
                    "type": "all"
                }
            ]
        }
        
        # 創建包含mention的消息
        mention_message = MentionTextSendMessage(
            text=mention_text,
            mention=mention_data,
            quick_reply=quick_reply
        )
        
        logger.info("創建@所有人mention消息成功")
        return mention_message
        
    except Exception as e:
        logger.error(f"創建@所有人mention消息時發生錯誤: {e}")
        # 降級到傳統@格式
        text_with_mention = f"@所有人 {text}"
        return TextSendMessage(text=text_with_mention, quick_reply=quick_reply)

# 創建一個全局字典來跟踪用戶狀態
user_conversation_state = {}  # 格式: {user_id: {"last_time": timestamp, "waiting_for_analysis": True/False}} 

# 改進contains_url函數，使其更準確地識別URL
def contains_url(text):
    """更準確地檢查文本是否包含URL"""
    if not text:
        return False
    # 一個更完整的URL檢測正則表達式
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        r'|(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|'
        r'(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}'
    )
    return bool(url_pattern.search(text))

# 改進should_perform_fraud_analysis函數，更好地處理網址分析
def should_perform_fraud_analysis(text_message):
    """判斷是否需要對消息進行詐騙分析"""
    if not text_message:
        return False
        
    # 1. 先检查是否是次数查询，避免这类消息被分析
    if any(keyword in text_message.lower() for keyword in ["剩余次数", "剩餘次數", "查詢次數", "查询次数", "還有幾次", "还有几次", "剩下幾次", "剩下几次", "幾次機會", "几次机会", "幾次分析", "几次分析"]):
        return False
    
    # 2. 檢查是否是詢問機器人工作原理或功能的問題（新增）
    meta_questions = ["判斷.*邏輯", "如何.*分析", "怎麼.*判斷", "原理.*什麼", "怎麼.*運作", "如何.*運作", "工作.*原理", "分析.*方式", "檢測.*方法"]
    if any(re.search(pattern, text_message) for pattern in meta_questions):
        logger.info(f"訊息是詢問機器人工作原理，不進行詐騙分析")
        return False
        
    # 3. 直接檢查是否含有URL，如果有優先分析
    if contains_url(text_message):
        logger.info(f"訊息中含有URL，將進行詐騙分析")
        return True
        
    # 4. 檢查是否包含常見問候詞和簡短訊息
    common_greetings = ["你好", "嗨", "哈囉", "嘿", "hi", "hello", "hey", "早安", "午安", "晚安"]
    if text_message.lower() in common_greetings or (len(text_message) <= 5 and any(greeting in text_message.lower() for greeting in common_greetings)):
        return False
        
    # 5. 檢查是否含有明確的分析請求關鍵詞
    analysis_keywords = ["分析", "詐騙", "安全", "可疑", "風險", "網站"]
    if any(keyword in text_message.lower() for keyword in analysis_keywords) and "嗎" in text_message:
        # 如果同時包含分析關鍵詞和疑問詞，可能是請求分析
        logger.info(f"訊息包含分析請求關鍵詞和疑問詞，將進行詐騙分析")
        return True
        
    # 6. 檢查是否與已知的網域相關
    for domain in SHORT_URL_DOMAINS + list(SAFE_DOMAINS.keys()):  # 修復：將字典鍵轉換為列表
        if domain.lower() in text_message.lower():
            logger.info(f"訊息包含已知網域 {domain}，將進行詐騙分析")
            return True
    
    # 7. 檢查是否是功能相關指令
    if any(keyword in text_message.lower() for keyword in function_inquiry_keywords + potato_game_trigger_keywords) or "詐騙類型" in text_message:
        return False
        
    # 8. 檢查是否是跟踪模式的問句（修改邏輯，排除詢問機器人的問題）
    if any(pattern in text_message.lower() for pattern in follow_up_patterns):
        # 如果包含詢問詞（什麼、如何、怎麼等），可能是詢問而非需要分析的內容
        inquiry_words = ["什麼", "如何", "怎麼", "為什麼", "邏輯", "原理", "方式", "方法"]
        if any(word in text_message for word in inquiry_words):
            logger.info(f"訊息包含詢問詞，判斷為詢問而非需要分析的內容")
            return False
        return True
        
    # 9. 檢查是否是請求分析的明顯特徵
    analysis_indicators = ["幫我分析", "幫忙看看", "這是不是詐騙", "這是真的嗎", "這可靠嗎", "分析一下", "這樣是詐騙嗎"]
    if any(indicator in text_message for indicator in analysis_indicators):
        return True
        
    # 10. 檢查是否包含特定詐騙相關關鍵詞
    # 只有使用者明確表示需要分析，或者文本包含多個詐騙關鍵詞才進行分析
    fraud_related_keywords = ["詐騙", "被騙", "騙子", "可疑", "轉帳", "匯款", "銀行帳號", "個資", "身份證", "密碼", 
                            "通知", "中獎", "貸款", "投資", "急需", "幫我處理", "急用", "解除設定", "提款卡", 
                            "監管帳戶", "解凍", "安全帳戶", "簽證", "保證金", "違法", "洗錢", "警察", "檢察官"]
                            
    # 要求至少包含兩個詐騙相關關鍵詞
    keyword_count = sum(1 for keyword in fraud_related_keywords if keyword in text_message)
    if keyword_count >= 2:
        return True
        
    # 11. 預設不進行詐騙分析，將訊息作為一般閒聊處理
    return False

if __name__ == "__main__":
    # 驗證環境變數
    validate_environment()
    
    # 確保在服務啟動時重新加載資料
    load_fraud_tactics()
    
    # 檢查是否為生產環境
    flask_env = os.environ.get('FLASK_ENV', 'development')
    port = int(os.environ.get("PORT", 8080))
    
    if flask_env == 'production':
        # 生產環境：強制使用 Gunicorn
        logger.info("🚀 生產環境檢測到，強制啟動 Gunicorn...")
        
        import subprocess
        import sys
        import os
        
        # 構建 Gunicorn 命令
        gunicorn_cmd = [
            "gunicorn",
            "--bind", f"0.0.0.0:{port}",
            "--workers", "2",
            "--timeout", "30",
            "--access-logfile", "-",
            "--error-logfile", "-",
            "--log-level", "info",
            "anti_fraud_clean_app:app"
        ]
        
        logger.info(f"🎯 執行 Gunicorn 命令: {' '.join(gunicorn_cmd)}")
        
        try:
            # 使用 exec 替換當前進程
            os.execvp("gunicorn", gunicorn_cmd)
        except FileNotFoundError:
            logger.error("❌ 找不到 Gunicorn，嘗試使用 python -m gunicorn")
            try:
                gunicorn_cmd = [
                    sys.executable, "-m", "gunicorn",
                    "--bind", f"0.0.0.0:{port}",
                    "--workers", "2", 
                    "--timeout", "30",
                    "--access-logfile", "-",
                    "--error-logfile", "-",
                    "--log-level", "info",
                    "anti_fraud_clean_app:app"
                ]
                os.execv(sys.executable, gunicorn_cmd)
            except Exception as e:
                logger.error(f"❌ Gunicorn 啟動失敗: {e}")
                logger.error("⚠️ 降級使用 Flask 開發伺服器（不建議在生產環境使用）")
                app.run(host="0.0.0.0", port=port, debug=False)
    else:
        # 開發環境：使用 Flask 開發伺服器
        logger.info("開發環境：使用 Flask 開發伺服器")
        app.run(host="0.0.0.0", port=port, debug=True)

