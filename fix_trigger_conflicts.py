#!/usr/bin/env python3
"""
修復觸發關鍵詞衝突問題
優化網頁分析和遊戲功能的觸發邏輯，避免互相干擾
"""

import re
from typing import List, Tuple

def contains_url(text: str) -> bool:
    """檢查文本是否包含URL（高優先級）"""
    if not text:
        return False
    
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        r'|(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|'
        r'(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}'
    )
    return bool(url_pattern.search(text))

def is_explicit_analysis_request(text: str) -> bool:
    """檢查是否為明確的分析請求"""
    if not text:
        return False
    
    text_lower = text.lower()
    explicit_requests = [
        "幫我分析", "幫忙看看", "這是不是詐騙", "這是真的嗎", 
        "這可靠嗎", "分析一下", "這樣是詐騙嗎", "請幫我分析",
        "幫我看看", "這安全嗎", "這個安全嗎"
    ]
    
    return any(req in text_lower for req in explicit_requests)

def is_game_trigger_improved(text: str) -> bool:
    """改進版遊戲觸發檢測 - 更精確的匹配"""
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    # 明確的遊戲請求關鍵詞
    explicit_game_keywords = [
        "選哪顆土豆",
        "玩土豆遊戲", 
        "土豆小遊戲",
        "防詐騙測驗",
        "防詐騙小遊戲"
    ]
    
    # 檢查明確的遊戲請求
    for keyword in explicit_game_keywords:
        if keyword in text_lower:
            return True
    
    # 檢查較寬泛的關鍵詞，但需要排除分析請求
    broad_game_keywords = [
        "土豆遊戲", "玩土豆", "選土豆", "開始遊戲", "玩遊戲"
    ]
    
    # 分析相關的排除詞
    analysis_indicators = [
        "是詐騙嗎", "安全嗎", "可靠嗎", "這是真的嗎", 
        "分析", "檢查", "看看", "幫我"
    ]
    
    for keyword in broad_game_keywords:
        if keyword in text_lower:
            # 如果包含分析指示詞，則不觸發遊戲
            if any(indicator in text_lower for indicator in analysis_indicators):
                return False
            return True
    
    # 防詐騙遊戲相關（需要更精確匹配）
    fraud_game_keywords = [
        "防詐騙遊戲", "詐騙檢測遊戲", "反詐遊戲"
    ]
    
    for keyword in fraud_game_keywords:
        if keyword in text_lower:
            return True
    
    return False

def should_perform_fraud_analysis_improved(text: str) -> bool:
    """改進版詐騙分析觸發檢測"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    # 1. 最高優先級：包含URL
    if contains_url(text):
        print(f"🌐 觸發原因：包含URL")
        return True
    
    # 2. 高優先級：明確的分析請求
    if is_explicit_analysis_request(text):
        print(f"🔍 觸發原因：明確分析請求")
        return True
    
    # 3. 排除遊戲相關（在分析關鍵詞檢查之前）
    if is_game_trigger_improved(text):
        print(f"🎮 排除原因：遊戲觸發關鍵詞")
        return False
    
    # 4. 排除條件檢查（提前）
    exclude_conditions = [
        # 簡短問候語
        lambda t: len(t) <= 5 and any(greeting in t for greeting in ["你好", "嗨", "哈囉", "hey", "hi"]),
        # 功能查詢
        lambda t: any(keyword in t for keyword in ["功能", "幫助", "會什麼", "能做什麼", "使用說明", "你是誰"]),
        # 次數查詢
        lambda t: any(keyword in t for keyword in ["剩餘次數", "還有幾次", "剩下幾次", "查詢次數"]),
        # 詐騙類型查詢
        lambda t: "詐騙類型" in t,
        # 閒聊性質的遊戲討論
        lambda t: ("遊戲" in t and any(word in t for word in ["推薦", "好玩", "有趣", "喜歡", "討論"])),
    ]
    
    for condition in exclude_conditions:
        if condition(text_lower):
            print(f"❌ 排除原因：符合排除條件")
            return False
    
    # 5. 分析關鍵詞 + 疑問詞（但要排除一般性問題）
    analysis_keywords = ["分析", "詐騙", "安全", "可疑", "風險"]
    website_keywords = ["網站", "網址", "連結", "鏈接", "平台"]
    
    # 如果包含分析關鍵詞+疑問詞，且是關於網站/投資的具體問題
    if any(keyword in text_lower for keyword in analysis_keywords) and "嗎" in text:
        # 排除一般性的遊戲/網站推薦問題
        general_questions = ["推薦", "有沒有", "哪裡有", "介紹", "討論"]
        if not any(general in text_lower for general in general_questions):
            print(f"❓ 觸發原因：分析關鍵詞 + 疑問詞")
            return True
    
    # 6. 投資相關問題
    investment_keywords = ["投資", "理財", "賺錢", "股票", "基金", "虛擬貨幣", "比特幣"]
    if any(keyword in text_lower for keyword in investment_keywords) and "嗎" in text:
        print(f"💰 觸發原因：投資相關問題")
        return True
    
    # 7. 多個詐騙關鍵詞
    fraud_keywords = [
        "詐騙", "被騙", "騙子", "可疑", "轉帳", "匯款", "銀行帳號", 
        "個資", "身份證", "密碼", "通知", "中獎", "貸款", "投資", 
        "急需", "幫我處理", "急用", "解除設定", "提款卡", 
        "監管帳戶", "解凍", "安全帳戶", "簽證", "保證金", 
        "違法", "洗錢", "警察", "檢察官"
    ]
    
    keyword_count = sum(1 for keyword in fraud_keywords if keyword in text)
    if keyword_count >= 2:
        print(f"🚨 觸發原因：包含 {keyword_count} 個詐騙關鍵詞")
        return True
    
    # 8. 跟踪模式觸發（更嚴格的條件）
    follow_up_patterns = [
        "被騙", "可疑", "不確定", "幫我看看"
    ]
    
    # 特別處理「詐騙」關鍵詞 - 只有在特定情況下才觸發
    if "詐騙" in text_lower:
        # 如果是詢問類問題（包含疑問詞）且不是閒聊
        if any(question_word in text for question_word in ["嗎", "？", "?"]) and not any(chat_word in text_lower for chat_word in ["好玩", "有趣", "推薦"]):
            print(f"📍 觸發原因：詐騙相關問題")
            return True
        else:
            print(f"💭 排除原因：詐騙閒聊討論")
            return False
    
    if any(pattern in text_lower for pattern in follow_up_patterns):
        # 排除詢問機器人原理的問題
        inquiry_words = ["什麼", "如何", "怎麼", "為什麼", "邏輯", "原理", "方式", "方法"]
        if any(word in text for word in inquiry_words):
            print(f"💭 排除原因：詢問機器人原理")
            return False
        print(f"📍 觸發原因：跟踪模式關鍵詞")
        return True
    
    print(f"💬 結果：使用閒聊模式")
    return False

def classify_message_intent(text: str) -> Tuple[str, str]:
    """分類訊息意圖"""
    if not text or text.strip() == "":
        return "empty", "空訊息"
    
    # 1. URL優先檢查
    if contains_url(text):
        return "fraud_analysis", "包含URL，進行詐騙分析"
    
    # 2. 遊戲觸發檢查
    if is_game_trigger_improved(text):
        return "game", "觸發遊戲功能"
    
    # 3. 詐騙分析檢查
    if should_perform_fraud_analysis_improved(text):
        return "fraud_analysis", "需要詐騙分析"
    
    # 4. 功能查詢
    function_keywords = ["功能", "幫助", "會什麼", "能做什麼", "使用說明", "你是誰"]
    if any(keyword in text.lower() for keyword in function_keywords):
        return "function_inquiry", "功能查詢"
    
    # 5. 詐騙類型查詢
    if "詐騙類型" in text:
        return "fraud_types", "詐騙類型查詢"
    
    # 6. 預設為閒聊
    return "chat", "一般閒聊"

def test_message_classification():
    """測試訊息分類功能"""
    test_cases = [
        # URL相關（應該觸發詐騙分析）
        ("這個網站安全嗎？https://example.com", "fraud_analysis"),
        ("有人傳這個連結給我 bit.ly/abc123", "fraud_analysis"),
        
        # 明確分析請求（應該觸發詐騙分析）
        ("請幫我分析這則訊息", "fraud_analysis"),
        ("這是詐騙嗎？", "fraud_analysis"),
        ("這個投資可靠嗎？", "fraud_analysis"),
        
        # 遊戲觸發（應該觸發遊戲）
        ("選哪顆土豆", "game"),
        ("我想玩土豆遊戲", "game"),
        ("防詐騙測驗", "game"),
        
        # 潛在衝突案例
        ("我在玩投資遊戲，這是詐騙嗎？", "fraud_analysis"),  # 應該分析而非遊戲
        ("有遊戲網站推薦嗎？", "chat"),  # 應該閒聊
        ("詐騙遊戲很好玩", "chat"),  # 應該閒聊
        
        # 閒聊案例
        ("你好", "chat"),
        ("今天天氣不錯", "chat"),
        ("謝謝", "chat"),
        
        # 功能查詢
        ("你有什麼功能？", "function_inquiry"),
        ("能做什麼？", "function_inquiry"),
        
        # 詐騙類型查詢
        ("詐騙類型列表", "fraud_types"),
    ]
    
    print("🧪 測試訊息分類功能")
    print("=" * 60)
    
    correct_count = 0
    total_count = len(test_cases)
    
    for message, expected_intent in test_cases:
        actual_intent, reason = classify_message_intent(message)
        is_correct = actual_intent == expected_intent
        
        status = "✅" if is_correct else "❌"
        print(f"{status} 訊息: '{message}'")
        print(f"    預期: {expected_intent}")
        print(f"    實際: {actual_intent} ({reason})")
        
        if is_correct:
            correct_count += 1
        print()
    
    accuracy = (correct_count / total_count) * 100
    print(f"📊 測試結果: {correct_count}/{total_count} 正確 ({accuracy:.1f}%)")
    
    return accuracy >= 90

def generate_improved_logic_code():
    """生成改進後的邏輯代碼"""
    code = '''
# 改進後的訊息處理邏輯（建議整合到主程式）

def handle_message_improved(text_message, user_id, reply_token):
    """改進版訊息處理邏輯"""
    
    # 1. 檢查空訊息
    if not text_message or text_message.strip() == "":
        send_function_guide(reply_token)
        return
    
    # 2. URL優先檢查 - 最高優先級
    if contains_url(text_message):
        logger.info(f"🌐 用戶 {user_id} 發送URL，進行詐騙分析")
        perform_fraud_analysis(text_message, user_id, reply_token)
        return
    
    # 3. 遊戲觸發檢查
    if is_game_trigger_improved(text_message):
        logger.info(f"🎮 用戶 {user_id} 觸發遊戲")
        start_potato_game(user_id, reply_token)
        return
    
    # 4. 詐騙分析檢查
    if should_perform_fraud_analysis_improved(text_message):
        logger.info(f"🔍 用戶 {user_id} 請求詐騙分析")
        perform_fraud_analysis(text_message, user_id, reply_token)
        return
    
    # 5. 功能查詢
    if is_function_inquiry(text_message):
        send_function_guide(reply_token)
        return
    
    # 6. 詐騙類型查詢
    if "詐騙類型" in text_message:
        send_fraud_types_list(reply_token)
        return
    
    # 7. 一般閒聊
    logger.info(f"💬 用戶 {user_id} 一般閒聊")
    handle_chat_response(text_message, user_id, reply_token)
'''
    
    print("🔧 改進後的邏輯代碼：")
    print(code)

if __name__ == "__main__":
    print("🔍 觸發關鍵詞衝突修復測試")
    print("=" * 50)
    
    # 執行測試
    test_success = test_message_classification()
    
    if test_success:
        print("\n🎉 測試通過！邏輯改進成功！")
        print("\n建議應用以下改進：")
        print("1. 將URL檢查提到最高優先級")
        print("2. 使用更精確的遊戲觸發匹配")
        print("3. 在分析前排除遊戲關鍵詞")
        print("4. 加強複合訊息的處理邏輯")
        
        generate_improved_logic_code()
    else:
        print("\n❌ 測試失敗，需要進一步調整邏輯") 