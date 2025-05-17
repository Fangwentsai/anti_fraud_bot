import os
import random
import logging
import json

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