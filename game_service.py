#!/usr/bin/env python3
"""
遊戲服務模組
處理土豆遊戲和其他互動遊戲功能
"""

import json
import logging
import random
import os
from typing import Dict, List, Optional, Tuple
from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent,
    SeparatorComponent, ButtonComponent, PostbackAction, QuickReply,
    QuickReplyButton, MessageAction
)

logger = logging.getLogger(__name__)

class GameService:
    """遊戲服務類"""
    
    def __init__(self):
        self.user_game_state = {}  # 用戶遊戲狀態
        self.game_questions = self.load_potato_game_questions()
        
    def load_potato_game_questions(self) -> List[Dict]:
        """載入土豆遊戲問題"""
        try:
            with open('potato_game_questions.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 檢查是否為詐騙問題格式（不適用於土豆遊戲）
                if isinstance(data, dict) and 'questions' in data:
                    questions = data['questions']
                    # 檢查第一個問題的格式
                    if questions and isinstance(questions[0].get('options'), list):
                        first_option = questions[0]['options'][0]
                        # 如果選項是字典格式（詐騙問題），則使用預設土豆問題
                        if isinstance(first_option, dict) and 'id' in first_option:
                            logger.info("檢測到詐騙問題格式，使用預設土豆問題")
                            return self.get_default_game_questions()
                        else:
                            return questions
                elif isinstance(data, list):
                    # 檢查是否為土豆遊戲格式
                    if data and 'question' in data[0] and isinstance(data[0].get('options'), list):
                        return data
                    else:
                        logger.info("問題格式不符合土豆遊戲，使用預設問題")
                        return self.get_default_game_questions()
                else:
                    logger.warning("遊戲問題格式不正確，使用預設問題")
                    return self.get_default_game_questions()
        except FileNotFoundError:
            logger.info("potato_game_questions.json 檔案不存在，使用預設土豆問題")
            return self.get_default_game_questions()
        except Exception as e:
            logger.error(f"載入遊戲問題時發生錯誤: {e}，使用預設土豆問題")
            return self.get_default_game_questions()
    
    def get_default_game_questions(self) -> List[Dict]:
        """取得預設的遊戲問題"""
        return [
            {
                "question": "你覺得哪顆土豆最適合做薯條？",
                "options": ["🥔 圓滾滾土豆", "🥔 長條形土豆", "🥔 小巧土豆", "🥔 紫色土豆"],
                "correct_answer": 1,
                "explanation": "長條形土豆澱粉含量適中，最適合做薯條！",
                "fraud_tip": "💡 就像選土豆一樣，投資也要選對標的！記住，天下沒有穩賺不賠的投資。"
            },
            {
                "question": "土豆最怕什麼？",
                "options": ["☀️ 陽光", "💧 水分", "🌡️ 高溫", "🌱 發芽"],
                "correct_answer": 0,
                "explanation": "土豆最怕陽光直射，會變綠產生毒素！",
                "fraud_tip": "💡 就像土豆怕陽光一樣，我們也要避開詐騙的「陽光」- 那些太好的投資機會！"
            },
            {
                "question": "哪種土豆料理最健康？",
                "options": ["🍟 炸薯條", "🥔 烤土豆", "🍲 土豆泥", "🥘 土豆燉肉"],
                "correct_answer": 1,
                "explanation": "烤土豆保留最多營養，而且不用額外油脂！",
                "fraud_tip": "💡 選擇健康的土豆料理就像選擇安全的投資管道，要避開那些「油膩膩」的詐騙陷阱！"
            },
            {
                "question": "土豆的原產地是哪裡？",
                "options": ["🇨🇳 中國", "🇺🇸 美國", "🇵🇪 秘魯", "🇮🇪 愛爾蘭"],
                "correct_answer": 2,
                "explanation": "土豆原產於南美洲的秘魯和玻利維亞一帶！",
                "fraud_tip": "💡 了解土豆的來源很重要，了解投資的來源更重要！投資前一定要查證平台是否合法。"
            },
            {
                "question": "土豆發芽了還能吃嗎？",
                "options": ["✅ 可以很營養", "❌ 不行有毒", "🤔 去掉芽就行", "🔥 煮熟沒事"],
                "correct_answer": 1,
                "explanation": "發芽的土豆含有龍葵鹼，有毒不能吃！",
                "fraud_tip": "💡 發芽的土豆不能吃，可疑的投資也不能碰！遇到要求先付錢的投資，就像發芽的土豆一樣危險。"
            }
        ]
    
    def start_potato_game(self, user_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """開始土豆遊戲"""
        if not self.game_questions:
            return None, "抱歉，遊戲問題載入失敗，請稍後再試！"
        
        # 隨機選擇一個問題
        question_data = random.choice(self.game_questions)
        
        # 記錄用戶遊戲狀態
        self.user_game_state[user_id] = {
            "question": question_data,
            "answered": False
        }
        
        return question_data, None
    
    def create_game_flex_message(self, question_data: Dict, user_id: str) -> FlexSendMessage:
        """創建遊戲問題的 Flex Message"""
        
        # 使用正確的JSON字段名
        question = question_data.get("fraud_message", "")  # 從JSON獲取詐騙訊息作為問題
        fraud_type = question_data.get("fraud_type", "詐騙檢測")  # 詐騙類型
        options = question_data.get("options", [])
        
        # 創建選項按鈕
        option_buttons = []
        for i, option in enumerate(options):
            # 正確處理選項數據結構
            if isinstance(option, dict):
                option_text = option.get("text", "")
                option_id = option.get("id", str(i))
            else:
                option_text = str(option)
                option_id = str(i)
            
            # 創建簡短的按鈕標籤（選項A、B、C等）
            button_label = f"選項 {chr(65 + i)}"  # A, B, C, D...
            
            option_buttons.append(
                ButtonComponent(
                    style='secondary',
                    height='sm',
                    action=PostbackAction(
                        label=button_label,
                        data=f'action=potato_game_answer&user_id={user_id}&answer={i}'
                    )
                )
            )
        
        # 在body中顯示完整的選項內容
        body_contents = [
            TextComponent(
                text=f"🎯 {fraud_type}",
                weight='bold',
                size='lg',
                color='#1DB446'
            ),
            SeparatorComponent(margin='md'),
            TextComponent(
                text="以下哪一個是詐騙訊息？",
                size='md',
                weight='bold',
                margin='md',
                color='#FF6B6B'
            ),
            SeparatorComponent(margin='md')
        ]
        
        # 添加選項內容到body
        for i, option in enumerate(options):
            if isinstance(option, dict):
                option_text = option.get("text", "")
            else:
                option_text = str(option)
            
            # 限制選項文字長度，避免過長
            if len(option_text) > 80:
                option_text = option_text[:77] + "..."
            
            body_contents.append(
                TextComponent(
                    text=f"{chr(65 + i)}. {option_text}",
                    size='sm',
                    wrap=True,
                    margin='sm',
                    color='#464F69'
                )
            )
        
        bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color='#FF6B6B',
                contents=[
                    TextComponent(
                        text="🎮 防詐騙小遊戲",
                        weight='bold',
                        color='#ffffff',
                        size='xl'
                    ),
                    TextComponent(
                        text="測試你的防詐騙知識！",
                        color='#ffffff',
                        size='md'
                    )
                ]
            ),
            body=BoxComponent(
                layout='vertical',
                padding_all='20px',
                spacing='md',
                contents=body_contents
            ),
            footer=BoxComponent(
                layout='vertical',
                spacing='sm',
                contents=option_buttons
            )
        )
        
        return FlexSendMessage(alt_text="防詐騙小遊戲", contents=bubble)
    
    def handle_game_answer(self, user_id: str, answer_index: int) -> Tuple[bool, str, Optional[str]]:
        """處理遊戲答案"""
        
        if user_id not in self.user_game_state:
            return False, "遊戲狀態不存在，請重新開始遊戲！", None
        
        game_state = self.user_game_state[user_id]
        
        if game_state.get("answered", False):
            return False, "你已經回答過這個問題了！", None
        
        question_data = game_state["question"]
        correct_option_letter = question_data.get("correct_option", "A")  # 從JSON獲取字母
        explanation = question_data.get("explanation", "")
        fraud_tip = question_data.get("fraud_tip", "")
        options = question_data.get("options", [])
        
        # 將字母轉換為索引 (A=0, B=1, C=2...)
        correct_answer_index = ord(correct_option_letter) - ord('A')
        
        # 標記為已回答
        self.user_game_state[user_id]["answered"] = True
        
        is_correct = answer_index == correct_answer_index
        
        # 獲取選項文字
        def get_option_text(option):
            if isinstance(option, dict):
                return option.get("text", "")
            return str(option)
        
        user_answer_text = get_option_text(options[answer_index]) if answer_index < len(options) else "未知選項"
        correct_answer_text = get_option_text(options[correct_answer_index]) if correct_answer_index < len(options) else "未知選項"
        
        # 限制文字長度以避免訊息過長
        if len(user_answer_text) > 50:
            user_answer_text = user_answer_text[:47] + "..."
        if len(correct_answer_text) > 50:
            correct_answer_text = correct_answer_text[:47] + "..."
        
        if is_correct:
            result_message = f"🎉 答對了！\n\n✅ 正確答案：{chr(65 + correct_answer_index)}. {correct_answer_text}\n\n💡 解釋：{explanation}"
        else:
            result_message = f"😅 答錯了！\n\n❌ 你的答案：{chr(65 + answer_index)}. {user_answer_text}\n✅ 正確答案：{chr(65 + correct_answer_index)}. {correct_answer_text}\n\n💡 解釋：{explanation}"
        
        if fraud_tip:
            result_message += f"\n\n💡 防詐提醒：{fraud_tip}"
        
        # 清除遊戲狀態
        del self.user_game_state[user_id]
        
        return is_correct, result_message, fraud_tip
    
    def create_game_result_flex_message(self, is_correct: bool, result_message: str, 
                                      user_id: str) -> FlexSendMessage:
        """創建遊戲結果的 Flex Message"""
        
        header_color = "#4CAF50" if is_correct else "#FF6B6B"
        header_text = "🎉 答對了！" if is_correct else "😅 答錯了！"
        
        bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color=header_color,
                contents=[
                    TextComponent(
                        text=header_text,
                        weight='bold',
                        color='#ffffff',
                        size='xl'
                    )
                ]
            ),
            body=BoxComponent(
                layout='vertical',
                padding_all='20px',
                spacing='md',
                contents=[
                    TextComponent(
                        text=result_message,
                        size='md',
                        wrap=True,
                        color='#464F69'
                    )
                ]
            ),
            footer=BoxComponent(
                layout='vertical',
                spacing='sm',
                contents=[
                    ButtonComponent(
                        style='primary',
                        height='sm',
                        action=PostbackAction(
                            label='🎮 再玩一次',
                            data=f'action=start_potato_game&user_id={user_id}'
                        )
                    ),
                    ButtonComponent(
                        style='secondary',
                        height='sm',
                        action=PostbackAction(
                            label='📊 查看防詐統計',
                            data='action=fraud_stats'
                        )
                    )
                ]
            )
        )
        
        return FlexSendMessage(alt_text=f"遊戲結果：{header_text}", contents=bubble)
    
    def get_game_statistics(self, user_id: str) -> Dict:
        """取得用戶遊戲統計（未來功能）"""
        # 這裡可以連接資料庫取得用戶的遊戲統計
        return {
            "total_games": 0,
            "correct_answers": 0,
            "accuracy": 0.0
        }
    
    def is_game_trigger(self, message: str) -> bool:
        """檢查訊息是否觸發遊戲"""
        message_lower = message.lower().strip()
        
        # 檢查是否包含遊戲觸發關鍵詞
        game_keywords = [
            "選哪顆土豆", "玩土豆", "選土豆", "土豆遊戲", 
            "玩遊戲", "選土豆遊戲", "開始遊戲"
        ]
        
        for keyword in game_keywords:
            if keyword in message_lower:
                return True
        
        return False


# 創建全域遊戲服務實例
game_service = GameService()

# 提供便捷的函數接口
def start_potato_game(user_id: str) -> Tuple[Optional[FlexSendMessage], Optional[str]]:
    """開始土豆遊戲的便捷函數"""
    question_data, error_message = game_service.start_potato_game(user_id)
    
    if error_message:
        return None, error_message
    
    flex_message = game_service.create_game_flex_message(question_data, user_id)
    return flex_message, None

def handle_potato_game_answer(user_id: str, answer_index: int) -> Tuple[bool, FlexSendMessage]:
    """處理土豆遊戲答案的便捷函數"""
    is_correct, result_message, fraud_tip = game_service.handle_game_answer(user_id, answer_index)
    flex_message = game_service.create_game_result_flex_message(is_correct, result_message, user_id)
    return is_correct, flex_message

def is_game_trigger(message: str) -> bool:
    """檢查是否為遊戲觸發關鍵詞的便捷函數"""
    return game_service.is_game_trigger(message)

def get_user_game_state(user_id: str) -> Optional[Dict]:
    """取得用戶遊戲狀態的便捷函數"""
    return game_service.user_game_state.get(user_id)


if __name__ == "__main__":
    # 測試功能
    print("=== 遊戲服務測試 ===")
    
    test_user_id = "test_user_123"
    
    # 測試開始遊戲
    flex_message, error = start_potato_game(test_user_id)
    if flex_message:
        print("✅ 遊戲開始成功")
    else:
        print(f"❌ 遊戲開始失敗：{error}")
    
    # 測試回答問題
    if test_user_id in game_service.user_game_state:
        is_correct, result_flex = handle_potato_game_answer(test_user_id, 0)
        print(f"✅ 答案處理成功，結果：{'正確' if is_correct else '錯誤'}")
    
    # 測試觸發關鍵詞
    test_messages = ["玩遊戲", "土豆遊戲", "選土豆", "今天天氣"]
    for msg in test_messages:
        is_trigger = is_game_trigger(msg)
        print(f"'{msg}' -> 遊戲觸發：{is_trigger}")
    
    print("🎉 所有測試完成！") 