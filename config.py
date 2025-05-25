#!/usr/bin/env python3
"""
防詐騙機器人配置模組
包含所有常數、配置和環境變數
"""

import os

# ===== LINE Bot 配置 =====
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')

# ===== OpenAI 配置 =====
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini')

# ===== 機器人行為配置 =====
BOT_TRIGGER_KEYWORD = "土豆"  # 群組中觸發機器人服務的關鍵詞
CHAT_TIP_PROBABILITY = 0.3  # 閒聊時回覆防詐小知識的機率
DONATION_SHOW_PROBABILITY = 0.15  # 顯示贊助信息的機率

# ===== 關鍵詞和模式 =====
FUNCTION_INQUIRY_KEYWORDS = [
    "功能", "幫助", "會什麼", "能做什麼", "使用說明", "你是誰",
    "你好", "哈囉", "嗨", "hi", "hello", "早安", "午安", "晚安"
]

FOLLOW_UP_PATTERNS = [
    "被騙", "詐騙", "可疑", "不確定", "幫我看看", 
    "這是詐騙嗎", "這是真的嗎"
]

FRAUD_PREVENTION_GAME_TRIGGER_KEYWORDS = [
    "防詐騙測試", "防詐騙測驗", "詐騙識別測試", "防詐測試", 
    "反詐測試", "測試防詐能力", "詐騙檢測測試", "開始測試"
]

ANALYSIS_PROMPTS = [
    "請幫我分析這則訊息：", "幫我分析這則訊息", "分析這則訊息", 
    "幫我分析訊息", "請幫我分析詐騙網站", "幫我分析詐騙網站"
]

# ===== 短網址域名列表 =====
SHORT_URL_DOMAINS = [
    'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly', 
    'is.gd', 'buff.ly', 'adf.ly', 'short.link', 'tiny.cc',
    'rebrand.ly', 'clickmeter.com', 'smarturl.it', 'linktr.ee',
    'reurl.cc', 'pse.is', '0rz.tw', 'tinyurl.tw'
]

# ===== 詢問機器人工作原理的關鍵詞 =====
META_QUESTION_KEYWORDS = [
    "什麼", "如何", "怎麼", "為什麼", "原理", "邏輯", 
    "機制", "方式", "方法", "運作"
]

# ===== OpenAI 系統提示詞 =====
FRAUD_ANALYSIS_SYSTEM_PROMPT = """你是一位名為「防詐騙助手」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。

請分析以下訊息並提供結構化回覆，格式如下：
風險等級：[高風險/中風險/低風險]
詐騙類型：[具體類型，如投資詐騙、購物詐騙等]
說明：（請用非常口語化、親切的語氣說明判斷依據，避免使用專業術語，就像在跟鄰居朋友聊天一樣。例如不要說「此網站使用混淆技術規避檢測」，而是說「這個網站看起來怪怪的，網址跟正常的不一樣，可能是假冒的」。語言要簡單直白，不要太長篇大論）
建議：（給出具體可行的防範建議，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號。語言要像鄰居朋友在關心提醒一樣親切簡單。）
新興手法：[是/否]"""

CHAT_SYSTEM_PROMPT = """你是一位名為「防詐騙助手」的AI聊天機器人，專門幫助50-60歲的長輩防範詐騙。你的說話風格要：
1. 非常簡單易懂，像鄰居朋友在聊天
2. 用溫暖親切的語氣，不要太正式
3. 當給建議時，一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號
4. 避免複雜的專業術語，用日常生活的話來解釋
5. 當用戶提到投資、轉帳、可疑訊息時，要特別關心並給出簡單明確的建議
6. 回應要簡短，不要太長篇大論"""

# ===== 檔案路徑配置 =====
SAFE_DOMAINS_FILE = 'safe_domains.json'
FRAUD_PREVENTION_GAME_QUESTIONS_FILE = 'fraud_detection_questions.json'
FRAUD_TACTICS_FILE = 'fraud_tactics.json'

# ===== API 配置 =====
FRAUD_ANALYSIS_MAX_TOKENS = 1000
CHAT_MAX_TOKENS = 500
FRAUD_ANALYSIS_TEMPERATURE = 0.2
CHAT_TEMPERATURE = 0.7

# ===== LINE 訊息限制 =====
LINE_MESSAGE_MAX_LENGTH = 5000
LINE_MESSAGE_SAFE_LENGTH = 4900  # 留一些緩衝空間

# ===== 日誌配置 =====
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 訊息處理配置
MAX_MESSAGE_LENGTH = 5000  # LINE 訊息最大長度限制

# 天氣查詢關鍵詞
WEATHER_KEYWORDS = [
    "天氣", "氣溫", "溫度", "下雨", "晴天", "陰天", "多雲", 
    "颱風", "降雨", "濕度", "風速", "預報", "太陽", "寒流", "梅雨"
]

# 遊戲觸發關鍵詞
GAME_TRIGGER_KEYWORDS = [
    "防詐騙測試", "防詐騙測驗", "詐騙識別測試", "防詐測試", "反詐測試",
    "開始防詐遊戲", "詐騙遊戲", "防詐測驗", "防詐小遊戲", "測試防詐能力",
    "詐騙檢測測試", "開始測試", "防詐問答", "詐騙題目", "反詐遊戲"
]

# 檢查必要的環境變數
def validate_environment():
    """檢查必要的環境變數是否設定"""
    missing_vars = []
    
    if not LINE_CHANNEL_ACCESS_TOKEN:
        missing_vars.append('LINE_CHANNEL_ACCESS_TOKEN')
    if not LINE_CHANNEL_SECRET:
        missing_vars.append('LINE_CHANNEL_SECRET')
    if not OPENAI_API_KEY:
        missing_vars.append('OPENAI_API_KEY')
    
    if missing_vars:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"缺少環境變數: {', '.join(missing_vars)}")
        logger.warning("機器人將以測試模式運行，部分功能可能無法正常使用")
    
    return len(missing_vars) == 0

# 在模組載入時檢查環境變數
_env_valid = validate_environment() 