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
    "功能", "幫助", "會什麼", "能做什麼", "使用說明", "你是誰"
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
FRAUD_ANALYSIS_SYSTEM_PROMPT = """你是一個詐騙風險評估專家，請以50歲以上的長輩能理解的口語化方式分析詐騙風險。避免使用「您」「我」等主觀用詞，而是使用更直接的表述。提供的建議應該具體實用且直接，並且一定要用emoji符號（🚫🔍🌐🛡️💡⚠️等）代替數字編號。語言要像鄰居阿姨在關心提醒一樣親切簡單。"""

CHAT_SYSTEM_PROMPT = """你是一位名為「防詐騙助手」的AI聊天機器人，專門幫助50-60歲的阿姨叔叔防範詐騙。你的說話風格要：
1. 非常簡單易懂，像鄰居阿姨在聊天
2. 用溫暖親切的語氣，不要太正式
3. 當給建議時，一定要用emoji符號（🚫🔍🌐��️💡⚠️等）代替數字編號
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
    "颱風", "降雨", "濕度", "風速", "預報", "今天", "明天", "後天"
]

# 遊戲觸發關鍵詞
GAME_TRIGGER_KEYWORDS = [
    "防詐騙測試", "防詐騙測驗", "詐騙識別測試", "防詐測試", "反詐測試"
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