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

# 導入網域變形檢測
from domain_spoofing_detector import detect_domain_spoofing

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 圖片處理類
class ImageHandler:
    """處理LINE圖片訊息並進行詐騙分析"""
    
    def __init__(self, line_bot_api: LineBotApi = None):
        """初始化圖片處理器"""
        self.line_bot_api = line_bot_api
        # 載入安全網域列表
        self.safe_domains = self._load_safe_domains()
    
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
            
            return flex_message, result
            
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
            
            return flex_message, result
            
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
        
        # 優先檢查是否為郵件截圖
        if self._contains_email_keywords(extracted_text):
            logger.info("檢測到郵件相關關鍵詞，使用郵件分析")
            # 使用郵件分析邏輯
            from anti_fraud_clean_app import analyze_email_fraud
            try:
                email_analysis_result = analyze_email_fraud(extracted_text, None, "朋友")
                if email_analysis_result.get("success", False):
                    result = email_analysis_result.get("result", {})
                    # 添加提取的文字到分析結果中
                    result["extracted_text"] = extracted_text
                    result["analysis_source"] = "郵件分析"
                    # 確保包含raw_result欄位，用於Firebase記錄
                    result["raw_result"] = email_analysis_result.get("raw_result", "")
                    return result
            except Exception as e:
                logger.error(f"郵件分析失敗: {e}")
                # 如果郵件分析失敗，繼續使用一般分析
        
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
        
        # 檢查提取的文字中是否包含網址，進行網域變形檢測
        domain_spoofing_result = self._check_domain_spoofing_in_text(extracted_text)
        
        # 如果檢測到網域變形攻擊，但不是郵件內容，才直接返回高風險結果
        if domain_spoofing_result.get("is_spoofing", False) and not self._contains_email_keywords(extracted_text):
            logger.info(f"檢測到網域變形攻擊: {domain_spoofing_result.get('spoofed_domain', '')}")
            return {
                "success": True,
                "risk_level": "極高風險",
                "fraud_type": "網域名稱變形攻擊",
                "explanation": domain_spoofing_result.get("explanation", "檢測到可疑的假冒網域"),
                "suggestions": domain_spoofing_result.get("suggestions", "🚫 立即停止使用此網站\n🔍 確認官方網址\n🛡️ 如已輸入資料請立即更改密碼"),
                "extracted_text": extracted_text,
                "spoofing_details": domain_spoofing_result
            }
        
        # 檢查是否包含QR碼
        qr_result = detect_qr_code(image_content)
        
        # 進行一般詐騙分析
        analysis_result = analyze_image(image_content, analysis_type, context_message)
        
        # 如果檢測到網域變形攻擊且是郵件內容，將此信息添加到分析結果中
        if domain_spoofing_result.get("is_spoofing", False) and self._contains_email_keywords(extracted_text):
            spoofing_info = f"\n\n⚠️ 額外發現：此郵件包含可疑網域「{domain_spoofing_result.get('spoofed_domain', '')}」，" \
                          f"疑似假冒「{domain_spoofing_result.get('original_domain', '')}」的詐騙網站！"
            analysis_result["explanation"] = analysis_result.get("explanation", "") + spoofing_info
            analysis_result["spoofing_details"] = domain_spoofing_result
            # 提升風險等級
            if analysis_result.get("risk_level") in ["低風險", "中風險"]:
                analysis_result["risk_level"] = "高風險"
        
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
    
    def _contains_email_keywords(self, text: str) -> bool:
        """檢查文字是否包含郵件相關關鍵詞"""
        # 強郵件特徵關鍵詞（必須包含這些才認為是郵件）
        strong_email_keywords = [
            "寄件者", "發信者", "主旨", "收件者", "From:", "To:", "Subject:",
            "發送時間", "收信時間", "回覆", "轉寄", "附件", "信箱"
        ]
        
        # 弱郵件特徵關鍵詞（在非聊天環境中可能表示郵件）
        weak_email_keywords = ["郵件", "email"]
        
        # 檢查是否包含強郵件特徵
        has_strong_email_features = any(keyword in text for keyword in strong_email_keywords)
        
        # 檢查是否包含弱郵件特徵
        has_weak_email_features = any(keyword in text for keyword in weak_email_keywords)
        
        # 檢查郵件地址格式
        import re
        email_address_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        has_email_address = re.search(email_address_pattern, text)
        
        # 檢查郵件服務格式
        service_patterns = [
            r'[A-Z]+\.[A-Z]+-服務[A-Z]+\.[A-Z]+',  # RTK.UI-服務FETC.Service
            r'[A-Z]+-[^<]+<[^>]+@[^>]+>',  # YTA-未於期限理 <casinto@telenet.be>
        ]
        has_service_pattern = any(re.search(pattern, text) for pattern in service_patterns)
        
        # 檢查是否為 LINE 聊天截圖（排除條件）
        line_chat_indicators = [
            "< ", "> ",  # LINE 聊天中的用戶名稱格式
            "上午11:", "下午", "上午", "PM", "AM",  # 時間格式但沒有郵件上下文
            "https://www.youtube.com", "https://youtu.be",  # YouTube 連結
            "https://line.me", "https://lin.ee"  # LINE 相關連結
        ]
        
        # 如果包含 LINE 聊天指標，則需要更嚴格的郵件判斷
        has_line_chat_indicators = any(indicator in text for indicator in line_chat_indicators)
        
        if has_line_chat_indicators:
            # 如果是 LINE 聊天，只有在同時包含強郵件特徵和郵件地址時才認為是郵件
            # 但如果只是在聊天中提到郵件地址，不應該被認為是郵件
            if has_strong_email_features and has_email_address is not None:
                return True
            else:
                return False
        
        # 非 LINE 聊天的情況，包含強郵件特徵、弱郵件特徵、郵件地址或服務格式時，才認為是郵件
        return (has_strong_email_features or 
                has_weak_email_features or
                has_email_address is not None or 
                has_service_pattern)
    
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
    
    def _load_safe_domains(self) -> Dict:
        """載入安全網域列表"""
        try:
            import json
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            safe_domains_path = os.path.join(script_dir, 'safe_domains.json')
            
            with open(safe_domains_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 扁平化分類的安全網域字典
                flattened_safe_domains = {}
                for category, domains in data['safe_domains'].items():
                    if isinstance(domains, dict):
                        flattened_safe_domains.update(domains)
                
                return flattened_safe_domains
        except Exception as e:
            logger.error(f"載入安全網域列表失敗: {e}")
            return {}
    
    def _check_domain_spoofing_in_text(self, text: str) -> Dict:
        """
        檢查文字中是否包含可疑的網域變形攻擊
        
        Args:
            text: 提取的文字內容
            
        Returns:
            Dict: 網域變形檢測結果
        """
        import re
        
        # 使用正則表達式提取所有可能的網址
        url_patterns = [
            r'https?://[^\s<>"{}|\\^`\[\]]+',  # 標準 HTTP/HTTPS URL
            r'www\.[^\s<>"{}|\\^`\[\]]+',      # www 開頭的網址
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'  # 一般網域格式
        ]
        
        urls = []
        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.extend(matches)
        
        # 清理和去重
        cleaned_urls = []
        for url in urls:
            # 移除末尾的標點符號
            url = re.sub(r'[.,;:!?)\]}>]+$', '', url)
            if url and url not in cleaned_urls:
                cleaned_urls.append(url)
        
        logger.info(f"從圖片文字中提取到的網址: {cleaned_urls}")
        
        # 檢查每個網址是否為網域變形攻擊
        for url in cleaned_urls:
            # 提取網域部分
            domain = url
            if '://' in url:
                domain = url.split('://')[1].split('/')[0]
            elif url.startswith('www.'):
                domain = url.split('/')[0]
            else:
                # 如果不是完整URL，假設是網域
                domain = url.split('/')[0]
            
            # 進行網域變形檢測
            spoofing_result = detect_domain_spoofing(domain, self.safe_domains)
            
            if spoofing_result.get("is_spoofed", False):
                logger.info(f"檢測到網域變形攻擊: {domain} -> {spoofing_result}")
                
                # 生成詳細的說明
                spoofed_domain = spoofing_result.get("spoofed_domain", domain)
                original_domain = spoofing_result.get("original_domain", "未知")
                attack_type = spoofing_result.get("spoofing_type", "網域變形")
                risk_explanation = spoofing_result.get("risk_explanation", "")
                
                # 使用原有的風險說明，或生成新的
                if risk_explanation:
                    explanation = risk_explanation
                else:
                    explanation = f"這個網址「{spoofed_domain}」是假冒「{original_domain}」的詐騙網站！" \
                                f"詐騙集團故意把網址改得很像真的，想騙取您的個人資料或金錢。" \
                                f"攻擊類型：{attack_type}。"
                
                suggestions = f"🚫 立即停止使用此網站\n" \
                            f"🔍 正確網址應該是：{original_domain}\n" \
                            f"🛡️ 如已輸入資料請立即更改密碼\n" \
                            f"💳 檢查信用卡及銀行帳戶是否有異常"
                
                return {
                    "is_spoofing": True,
                    "spoofed_domain": spoofed_domain,
                    "original_domain": original_domain,
                    "spoofing_type": attack_type,
                    "explanation": explanation,
                    "suggestions": suggestions,
                    "detected_url": url
                }
        
        # 沒有檢測到網域變形攻擊
        return {
            "is_spoofing": False,
            "detected_urls": cleaned_urls
        }
    
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
def init_image_handler(line_bot_api: LineBotApi = None):
    """初始化圖片處理器"""
    global image_handler
    image_handler = ImageHandler(line_bot_api)
    logger.info("圖片處理器初始化成功")

# 自動初始化（用於測試環境）
if image_handler is None:
    try:
        image_handler = ImageHandler(None)
        logger.info("圖片處理器自動初始化（測試模式）")
    except Exception as e:
        logger.warning(f"圖片處理器自動初始化失敗: {e}")

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