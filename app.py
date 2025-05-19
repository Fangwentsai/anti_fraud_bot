import os
import random
import logging
import json
import re

# 載入詐騙題庫
POTATO_GAME_QUESTIONS_DB = "potato_game_questions.json"
potato_game_questions = []

load_fraud_tactics()
# load_potato_game_questions()  # 移至主函數中，避免重複加載

logger = logging.getLogger(__name__)

# 定義關鍵詞和模式
function_inquiry_keywords = ["功能", "幫助", "會什麼", "能做什麼", "使用說明", "你是誰"]
follow_up_patterns = ["被騙", "詐騙", "可疑", "不確定", "幫我看看", "這是詐騙嗎", "這是真的嗎"]
potato_game_trigger_keywords = ["選哪顆土豆", "玩遊戲", "土豆遊戲", "選土豆遊戲", "開始遊戲"]
url_analysis_keywords = ["分析這個網站", "網址分析", "連結分析", "網站分析", "判斷網站", "判斷網址"]

# 檢查訊息是否不包含任何已知指令的關鍵字，以判斷是否為一般閒聊
general_chat_keywords = [
    "詐騙類型列表", "詐騙類型", 
    "選哪顆土豆", "玩遊戲",
    "什麼是", "查詢", "我想了解", "我想知道", # 這些是類型查詢的前綴
    "你好", "嗨", "哈囉", "嘿", "hi", "hello", "hey" # 添加基本問候詞，保證這些簡單問候不會被當作詐騙分析
]

# URL正則表達式模式
url_pattern = re.compile(r'https?://\S+')

def handle_message(event):
    """
    處理用戶發送的消息
    """
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    
    # 檢查是否為URL分析請求
    if any(keyword in user_message for keyword in url_analysis_keywords):
        # 提取URL
        url_match = url_pattern.search(user_message)
        if url_match:
            url = url_match.group(0)
            # 進行URL風險分析
            analysis_result = analyze_url(url)
            # 顯示分析結果
            response_message = display_url_analysis_result(analysis_result)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_message))
            return
    
    # 其他消息處理邏輯
    # ... 現有代碼 ...

def analyze_url(url):
    """
    分析URL的風險等級
    
    參數:
    url - 需要分析的URL
    
    返回:
    包含分析結果的字典
    """
    # 這裡應該調用您的URL分析服務或API
    # 為了示例，我們返回一個模擬的分析結果
    
    # 檢查是否為政府網站
    if '.gov.' in url:
        return {
            "risk_level": "低",
            "fraud_type": "非詐騙相關",
            "explanation": "該網址屬於政府官方網站，通常具有較高的可信度。政府網站通常以.gov域名結尾，代表這是由政府機構運營的官方網站。",
            "suggestions": "雖然該網址看起來是官方網站，但仍建議用戶從官方管道訪問此網站，例如從搜索引擎搜索相關政府部門，而不是直接點擊分享的連結。"
        }
    
    # 檢查是否為知名網站
    elif any(domain in url for domain in ['.google.', '.facebook.', '.youtube.', '.line.', '.instagram.', '.twitter.']):
        return {
            "risk_level": "低",
            "fraud_type": "非詐騙相關",
            "explanation": "該網址屬於知名大型網站，通常具有較高的可信度。但請注意，詐騙者可能會使用相似但略有不同的網址（如拼寫錯誤）來冒充這些網站。",
            "suggestions": "請仔細檢查網址拼寫是否正確，避免點擊來源不明的連結。最安全的做法是直接在瀏覽器中輸入官方網址或使用官方應用程式。"
        }
        
    # 檢查是否含有可疑關鍵詞
    elif any(keyword in url for keyword in ['free', 'prize', 'winner', 'lottery', 'gift', 'lucky']):
        return {
            "risk_level": "高",
            "fraud_type": "釣魚網站",
            "explanation": "該網址包含與獎品、免費禮物或中獎相關的關鍵詞，這是典型的釣魚網站特徵。詐騙者常利用此類網站騙取個人資料或金錢。",
            "suggestions": "建議不要點擊該連結，不要提供任何個人資料或金融信息。沒有不勞而獲的好事，請對此類「免費」或「中獎」訊息保持高度警覺。"
        }
    
    # 其他情況，返回中等風險
    else:
        return {
            "risk_level": "中",
            "fraud_type": "未知",
            "explanation": "該網址不屬於已知的可信官方網站，但也沒有明顯的詐騙特徵。未知來源的網站可能存在資安風險或私隱問題。",
            "suggestions": "建議不要輕易在此類網站提供個人資料、金融信息或下載檔案。如需訪問，請使用具備安全防護功能的瀏覽器，並確保您的設備已安裝最新的安全更新和防毒軟體。"
        }

def send_potato_game_question(user_id, reply_token):
    """
    Sends a new "選哪顆土豆" game question to the user.
    """
    global user_game_state
    
    # 調試日誌：檢查題庫狀態
    logger.info(f"當前題庫狀態: potato_game_questions 包含 {len(potato_game_questions)} 道題目")
    
    # 優先從預設題庫選取題目
    if potato_game_questions:
        # 從題庫中隨機選取一道題目
        question = random.choice(potato_game_questions)
        
        # 詐騙訊息（假土豆）
        false_potato_text = question['fraud_message']
        fraud_type = question['fraud_type']
        explanation = question.get('explanation', '這是一則詐騙訊息，請保持警覺。')
        
        # 調試日誌：檢查題目選項
        has_options = 'options' in question and question['options'] and 'correct_option' in question
        logger.info(f"選擇題目ID: {question.get('id', '未知')}，是否有預設選項: {has_options}")
        
        # 檢查題目是否已有預設選項
        if 'options' in question and question['options'] and 'correct_option' in question:
            logger.info(f"使用題庫中的預設選項，題目ID: {question.get('id', '未知')}")
            # ... 現有代碼 ...

def display_url_analysis_result(analysis_result):
    """
    顯示URL分析結果，使用類似選土豆的界面
    
    參數:
    analysis_result - 包含分析結果的字典，必須包含 risk_level, fraud_type, explanation, suggestions
    
    返回:
    格式化後的分析結果字符串
    """
    # 風險等級對應的顏色表示
    risk_colors = {
        "低": "🟢 低風險",
        "中": "🟡 中度風險", 
        "高": "🔴 高風險",
        "不確定": "⚪ 風險不明"
    }
    
    # 從分析結果中獲取信息
    risk_level = analysis_result.get("risk_level", "不確定")
    fraud_type = analysis_result.get("fraud_type", "未知")
    explanation = analysis_result.get("explanation", "無法確定該網址的風險等級。")
    suggestions = analysis_result.get("suggestions", "請謹慎處理，有疑問可撥打165反詐騙專線。")
    
    # 構建回應訊息
    result_message = f"網址分析結果：\n\n{risk_colors.get(risk_level, '⚪ 風險不明')}\n\n"
    result_message += f"可能詐騙類型：{fraud_type}\n\n"
    result_message += f"分析：\n{explanation}\n\n"
    result_message += f"建議：\n{suggestions}"
    
    return result_message

def load_potato_game_questions():
    global potato_game_questions
    try:
        # 記錄載入前的路徑信息
        file_path = os.path.abspath(POTATO_GAME_QUESTIONS_DB)
        logger.info(f"嘗試從路徑讀取題庫文件: {file_path}")
        logger.info(f"當前工作目錄: {os.getcwd()}")
        
        # 檢查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            potato_game_questions = []
            return
            
        with open(POTATO_GAME_QUESTIONS_DB, 'r', encoding='utf-8') as f:
            data = json.load(f)
            potato_game_questions = data.get("questions", [])
            
        # 確認文件內容
        first_three_questions = []
        for i, q in enumerate(potato_game_questions[:3]):
            first_three_questions.append(f"題目ID: {q.get('id')}, 詐騙類型: {q.get('fraud_type')}")
            
        logger.info(f"成功從 {POTATO_GAME_QUESTIONS_DB} 加載詐騙題庫，共 {len(potato_game_questions)} 道題目")
        logger.info(f"前三個題目: {', '.join(first_three_questions)}")
        logger.info(f"題庫中選項信息: 有預設選項的題目數量: {sum(1 for q in potato_game_questions if 'options' in q and q['options'] and 'correct_option' in q)}")
    except FileNotFoundError:
        logger.warning(f"詐騙題庫文件 {POTATO_GAME_QUESTIONS_DB} 未找到。")
        potato_game_questions = []
    except json.JSONDecodeError:
        logger.error(f"解析詐騙題庫文件 {POTATO_GAME_QUESTIONS_DB} 失敗。")
        potato_game_questions = []
    except Exception as e:
        logger.error(f"加載詐騙題庫時發生未知錯誤: {e}")
        potato_game_questions = []

if __name__ == "__main__":
    # 確保在服務啟動時重新加載題庫
    load_fraud_tactics()
    load_potato_game_questions()
    
    # 打印題庫加載結果
    logger.info(f"服務啟動時載入題庫：potato_game_questions 包含 {len(potato_game_questions)} 道題目")
    logger.info(f"題庫中有選項的題目數量: {sum(1 for q in potato_game_questions if 'options' in q and q['options'] and 'correct_option' in q)}")
    if potato_game_questions:
        logger.info(f"題庫路徑: {os.path.abspath(POTATO_GAME_QUESTIONS_DB)}")
        logger.info(f"工作目錄: {os.getcwd()}")
        
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 