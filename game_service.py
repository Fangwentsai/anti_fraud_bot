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
        """載入遊戲問題"""
        try:
            with open('fraud_detection_questions.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 檢查是否為詐騙問題格式
                if isinstance(data, dict) and 'questions' in data:
                    questions = data['questions']
                    # 檢查第一個問題的格式
                    if questions and isinstance(questions[0].get('options'), list):
                        first_option = questions[0]['options'][0]
                        # 如果選項是字典格式（詐騙問題），直接使用
                        if isinstance(first_option, dict) and 'id' in first_option:
                            logger.info("載入詐騙檢測問題")
                            return questions
                        else:
                            return questions
                elif isinstance(data, list):
                    # 檢查是否為土豆遊戲格式
                    if data and 'question' in data[0] and isinstance(data[0].get('options'), list):
                        logger.info("載入土豆遊戲問題")
                        return data
                    else:
                        logger.info("問題格式不符合，使用預設問題")
                        return self.get_default_game_questions()
                else:
                    logger.warning("遊戲問題格式不正確，使用預設問題")
                    return self.get_default_game_questions()
        except FileNotFoundError:
            logger.info("fraud_detection_questions.json 檔案不存在，使用預設問題")
            return self.get_default_game_questions()
        except Exception as e:
            logger.error(f"載入遊戲問題時發生錯誤: {e}，使用預設問題")
            return self.get_default_game_questions()
    
    def get_default_game_questions(self) -> List[Dict]:
        """取得預設的遊戲問題（已移除土豆知識問題，現在使用詐騙檢測問題）"""
        # 不再提供土豆知識問題，只使用詐騙檢測問題
        return []
    
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
        
        # 檢查問題格式並適配
        if "question" in question_data:
            # 詐騙問題格式
            question = question_data.get("question", "")
            game_type = f"🎯 防詐騙測試"
            question_prompt = question
            options = question_data.get("options", [])
        else:
            # 詐騙問題格式
            question = question_data.get("fraud_message", "")
            game_type = f"🎯 {question_data.get('fraud_type', '詐騙檢測')}"
            question_prompt = "以下哪一個是詐騙訊息？"
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
                text=game_type,
                weight='bold',
                size='lg',
                color='#1DB446'
            ),
            SeparatorComponent(margin='md'),
            TextComponent(
                text=question_prompt,
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
        
        # 根據問題類型設置標題
        header_title = "🎮 防詐騙測試"
        header_subtitle = "測試你的防詐騙知識！"
        
        bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color='#FF6B6B',
                contents=[
                    TextComponent(
                        text=header_title,
                        weight='bold',
                        color='#ffffff',
                        size='xl'
                    ),
                    TextComponent(
                        text=header_subtitle,
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
        
        return FlexSendMessage(alt_text=header_title, contents=bubble)
    
    def handle_game_answer(self, user_id: str, answer_index: int) -> Tuple[bool, str, Optional[str]]:
        """處理遊戲答案"""
        
        if user_id not in self.user_game_state:
            return False, "遊戲狀態不存在，請重新開始遊戲！", None
        
        game_state = self.user_game_state[user_id]
        
        if game_state.get("answered", False):
            return False, "你已經回答過這個問題了！", None
        
        question_data = game_state["question"]
        options = question_data.get("options", [])
        
        # 檢查問題格式並獲取正確答案
        if "question" in question_data:
            # 詐騙問題格式
            correct_answer_index = question_data.get("correct_answer", 0)
            explanation = question_data.get("explanation", "")
            fraud_tip = question_data.get("fraud_tip", "")
        else:
            # 詐騙問題格式
            correct_option_letter = question_data.get("correct_option", "A")
            correct_answer_index = ord(correct_option_letter) - ord('A')
            explanation = question_data.get("explanation", "")
            fraud_tip = question_data.get("fraud_tip", "")
        
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
            "防詐騙測試", "防詐騙測驗", "詐騙識別測試", "防詐測試", 
            "反詐測試", "測試防詐能力", "詐騙檢測測試", "開始測試",
            "防詐騙遊戲", "詐騙檢測", "反詐遊戲", "識別詐騙"
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
    
    # 如果result_message是字符串（錯誤訊息），創建錯誤的FlexMessage
    if isinstance(result_message, str) and not is_correct and ("遊戲狀態不存在" in result_message or "已經回答過" in result_message):
        # 創建錯誤訊息的FlexMessage
        error_bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color='#FF6B6B',
                contents=[
                    TextComponent(
                        text="⚠️ 遊戲錯誤",
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
                            label='🎮 重新開始',
                            data=f'action=start_potato_game&user_id={user_id}'
                        )
                    )
                ]
            )
        )
        flex_message = FlexSendMessage(alt_text="遊戲錯誤", contents=error_bubble)
    else:
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