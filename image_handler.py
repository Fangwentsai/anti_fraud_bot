#!/usr/bin/env python3
"""
圖片處理模組
處理LINE用戶上傳的圖片並進行詐騙風險分析
"""

import os
import logging
import requests
from io import BytesIO
from typing import Dict, Any, Tuple, Optional, List
from linebot import LineBotApi
from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, 
    SeparatorComponent, ButtonComponent, URIAction, PostbackAction, MessageAction
)

from image_analysis_service import (
    analyze_image, analyze_image_from_url, 
    detect_qr_code, extract_text_from_image, 
    ANALYSIS_TYPES
)

# 導入統一的 Flex Message 服務
from flex_message_service import create_analysis_flex_message

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 圖片處理類
class ImageHandler:
    """處理LINE圖片訊息並進行詐騙分析"""
    
    def __init__(self, line_bot_api: LineBotApi = None):
        """初始化圖片處理器"""
        self.line_bot_api = line_bot_api
    
    def handle_image_message(self, message_id: str, user_id: str, display_name: str, 
                            context_message: str = "", analysis_type: str = "GENERAL") -> Tuple[FlexSendMessage, str]:
        """
        處理LINE圖片訊息
        
        Args:
            message_id: LINE訊息ID
            user_id: 用戶ID
            display_name: 用戶顯示名稱
            context_message: 用戶提供的上下文信息
            analysis_type: 分析類型
            
        Returns:
            Tuple[FlexSendMessage, str]: Flex訊息和原始分析結果
        """
        try:
            # 獲取圖片內容
            if not self.line_bot_api:
                logger.error("LINE Bot API未初始化，無法獲取圖片內容")
                return self._create_error_flex_message("系統無法處理圖片", display_name), ""
            
            # 從LINE獲取圖片內容
            message_content = self.line_bot_api.get_message_content(message_id)
            image_content = b''
            for chunk in message_content.iter_content():
                image_content += chunk
            
            # 分析圖片
            result = self._analyze_image_content(image_content, context_message, analysis_type)
            
            # 使用統一的 Flex Message 創建方法
            flex_message = create_analysis_flex_message(result, display_name, "圖片分析", user_id)
            
            return flex_message, result.get("raw_result", "")
            
        except Exception as e:
            logger.exception(f"處理圖片訊息時發生錯誤: {e}")
            return self._create_error_flex_message(f"處理圖片時發生錯誤: {str(e)}", display_name), ""
    
    def handle_image_url(self, image_url: str, user_id: str, display_name: str,
                        context_message: str = "", analysis_type: str = "GENERAL") -> Tuple[FlexSendMessage, str]:
        """
        處理圖片URL
        
        Args:
            image_url: 圖片URL
            user_id: 用戶ID
            display_name: 用戶顯示名稱
            context_message: 用戶提供的上下文信息
            analysis_type: 分析類型
            
        Returns:
            Tuple[FlexSendMessage, str]: Flex訊息和原始分析結果
        """
        try:
            # 分析圖片URL
            result = analyze_image_from_url(image_url, analysis_type, context_message)
            
            # 使用統一的 Flex Message 創建方法
            flex_message = create_analysis_flex_message(result, display_name, "圖片分析", user_id)
            
            return flex_message, result.get("raw_result", "")
            
        except Exception as e:
            logger.exception(f"處理圖片URL時發生錯誤: {e}")
            return self._create_error_flex_message(f"處理圖片URL時發生錯誤: {str(e)}", display_name), ""
    
    def _analyze_image_content(self, image_content: bytes, context_message: str, analysis_type: str) -> Dict:
        """
        分析圖片內容
        
        Args:
            image_content: 圖片二進制內容
            context_message: 用戶提供的上下文信息
            analysis_type: 分析類型
            
        Returns:
            Dict: 分析結果
        """
        # 首先提取文字以判斷是否需要特殊分析
        extracted_text = extract_text_from_image(image_content)
        
        # 檢查文字內容，選擇最合適的分析類型
        if analysis_type == "GENERAL":
            # 如果用戶沒有指定分析類型，根據圖片內容自動選擇
            if self._contains_banking_keywords(extracted_text):
                analysis_type = "PHISHING"
                logger.info("檢測到銀行相關關鍵詞，使用釣魚網站分析")
            elif self._contains_document_keywords(extracted_text):
                analysis_type = "DOCUMENT"
                logger.info("檢測到文件相關關鍵詞，使用文件分析")
            elif self._contains_social_media_keywords(extracted_text):
                analysis_type = "SOCIAL_MEDIA"
                logger.info("檢測到社交媒體相關關鍵詞，使用社交媒體分析")
        
        # 檢查是否包含QR碼
        qr_result = detect_qr_code(image_content)
        
        # 進行一般詐騙分析
        analysis_result = analyze_image(image_content, analysis_type, context_message)
        
        # 如果發現QR碼且風險等級高，更新分析結果
        if qr_result.get("success", False) and qr_result.get("contains_qr_code", False):
            if qr_result.get("risk_level") == "高":
                analysis_result["risk_level"] = "高風險"
                analysis_result["fraud_type"] = "可疑QR碼詐騙"
                analysis_result["explanation"] = f"{analysis_result.get('explanation', '')}\n\n此外，圖片中包含高風險QR碼，可能導向惡意網站或詐騙內容。"
                analysis_result["suggestions"] = f"{analysis_result.get('suggestions', '')}\n🚫 請勿掃描圖片中的QR碼\n🔍 不要點擊來路不明的QR碼鏈接"
            else:
                analysis_result["explanation"] = f"{analysis_result.get('explanation', '')}\n\n此外，圖片中包含QR碼，但風險評估為{qr_result.get('risk_level', '未知')}。"
        
        # 添加提取的文字到分析結果中
        analysis_result["extracted_text"] = extracted_text
        
        return analysis_result
    
    def _contains_banking_keywords(self, text: str) -> bool:
        """檢查文字是否包含銀行或支付相關關鍵詞"""
        banking_keywords = [
            "銀行", "信用卡", "提款", "轉帳", "密碼", "帳號", "登入", "驗證", "安全碼",
            "匯款", "ATM", "網路銀行", "手機銀行", "網銀", "支付", "付款", "結帳", "錢包"
        ]
        return any(keyword in text for keyword in banking_keywords)
    
    def _contains_document_keywords(self, text: str) -> bool:
        """檢查文字是否包含文件相關關鍵詞"""
        document_keywords = [
            "合約", "協議", "證明", "文件", "發票", "收據", "契約", "通知", "公告",
            "帳單", "訂單", "報告", "聲明", "政府", "機關", "公文", "法院", "稅務"
        ]
        return any(keyword in text for keyword in document_keywords)
    
    def _contains_social_media_keywords(self, text: str) -> bool:
        """檢查文字是否包含社交媒體相關關鍵詞"""
        social_keywords = [
            "FB", "Facebook", "臉書", "IG", "Instagram", "推特", "Twitter", "TikTok", "抖音",
            "YouTube", "頻道", "訂閱", "追蹤", "按讚", "分享", "留言", "直播", "私訊", "限時動態"
        ]
        return any(keyword in text for keyword in social_keywords)
    
    def _create_error_flex_message(self, error_message: str, display_name: str) -> FlexSendMessage:
        """
        創建錯誤訊息的Flex訊息
        
        Args:
            error_message: 錯誤訊息
            display_name: 用戶顯示名稱
            
        Returns:
            FlexSendMessage: 格式化的Flex訊息
        """
        bubble = BubbleContainer(
            direction="ltr",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="❌ 圖片分析錯誤",
                        weight="bold",
                        color="#ffffff",
                        size="xl"
                    )
                ],
                background_color="#E74C3C",
                padding_all="20px"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text=error_message,
                        wrap=True,
                        size="md",
                        color="#555555"
                    ),
                    SeparatorComponent(margin="md"),
                    TextComponent(
                        text="💡 您可以嘗試：",
                        weight="bold",
                        size="md",
                        margin="md"
                    ),
                    TextComponent(
                        text="• 確保圖片格式正確\n• 上傳較小的圖片\n• 稍後再試",
                        size="sm",
                        color="#555555",
                        wrap=True,
                        margin="sm"
                    )
                ],
                padding_all="20px"
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        style="primary",
                        action=MessageAction(
                            label="🔄 重新上傳",
                            text="土豆 請幫我分析圖片"
                        ),
                        color="#3498DB"
                    )
                ],
                padding_all="20px"
            )
        )
        
        return FlexSendMessage(alt_text="圖片分析錯誤", contents=bubble)


# 創建圖片處理器實例
image_handler = None

# 初始化函數
def init_image_handler(line_bot_api: LineBotApi):
    """初始化圖片處理器"""
    global image_handler
    image_handler = ImageHandler(line_bot_api)
    logger.info("圖片處理器初始化成功")

# 提供便捷的函數接口
def handle_image_message(message_id: str, user_id: str, display_name: str, 
                        context_message: str = "", analysis_type: str = "GENERAL") -> Tuple[FlexSendMessage, str]:
    """處理LINE圖片訊息"""
    if not image_handler:
        logger.error("圖片處理器未初始化，無法處理圖片訊息")
        return None, ""
    
    return image_handler.handle_image_message(message_id, user_id, display_name, context_message, analysis_type)

def handle_image_url(image_url: str, user_id: str, display_name: str,
                    context_message: str = "", analysis_type: str = "GENERAL") -> Tuple[FlexSendMessage, str]:
    """處理圖片URL"""
    if not image_handler:
        logger.error("圖片處理器未初始化，無法處理圖片URL")
        return None, ""
    
    return image_handler.handle_image_url(image_url, user_id, display_name, context_message, analysis_type)


if __name__ == "__main__":
    # 測試功能
    print("=== 圖片處理器測試 ===")
    print("注意：此模組需要在LINE Bot環境中使用")
    print("🎉 測試完成！") 