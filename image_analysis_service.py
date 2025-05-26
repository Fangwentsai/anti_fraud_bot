#!/usr/bin/env python3
"""
圖片分析服務模組
提供詐騙圖片分析功能
"""

import os
import json
import logging
import re
import requests
from typing import Dict, List, Optional, Any, Tuple
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加載環境變量
load_dotenv()

# 圖片分析類型
ANALYSIS_TYPES = {
    "GENERAL": "一般詐騙分析",
    "PHISHING": "釣魚網站分析",
    "DOCUMENT": "可疑文件分析",
    "SOCIAL_MEDIA": "社交媒體詐騙分析"
}

class ImageAnalysisService:
    """圖片分析服務類"""
    
    def __init__(self):
        """初始化圖片分析服務"""
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.client = None
        
        if self.openai_api_key:
            try:
                self.client = OpenAI(
                    api_key=self.openai_api_key,
                    timeout=30.0,  # 設置超時
                    max_retries=3   # 設置重試次數
                )
                logger.info("OpenAI API 初始化成功")
            except Exception as e:
                logger.error(f"OpenAI API 初始化失敗: {e}")
                self.client = None
        else:
            logger.warning("OpenAI API 初始化失敗：缺少 API 金鑰")
    
    def analyze_image(self, image_content: bytes, analysis_type: str = "GENERAL", context_message: str = "") -> Dict:
        """
        分析圖片，檢測詐騙相關內容
        
        Args:
            image_content: 圖片二進制內容
            analysis_type: 分析類型，可選：GENERAL, PHISHING, DOCUMENT, SOCIAL_MEDIA
            context_message: 用戶提供的上下文信息
            
        Returns:
            Dict: 分析結果
        """
        if not self.client:
            return {
                "success": False,
                "message": "OpenAI API 未初始化，無法分析圖片",
                "risk_level": "無法判定",
                "fraud_type": "未知",
                "explanation": "系統無法分析圖片。請確保您的OpenAI API金鑰已正確設置。",
                "suggestions": "建議您手動檢查此圖片是否存在可疑內容。"
            }
        
        try:
            # 將圖片轉換為 base64 編碼
            image = Image.open(BytesIO(image_content))
            # 壓縮圖片以減少API請求大小
            image = self._resize_image_if_needed(image)
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # 根據分析類型選擇提示語
            prompt = self._get_analysis_prompt(analysis_type, context_message)
            
            # 調用 OpenAI API 進行圖片分析
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "請分析這張圖片是否含有詐騙內容？" + (f"\n用戶提供的上下文: {context_message}" if context_message else "")},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1200
            )
            
            result = response.choices[0].message.content
            logger.info(f"圖片分析結果 (部分): {result[:100]}...")
            
            # 解析分析結果
            parsed_result = self._parse_analysis_result(result)
            
            return {
                "success": True,
                "message": "圖片分析完成",
                "raw_result": result,
                **parsed_result
            }
            
        except Exception as e:
            logger.exception(f"分析圖片時發生錯誤: {e}")
            return {
                "success": False,
                "message": f"分析圖片時發生錯誤: {str(e)}",
                "risk_level": "無法判定",
                "fraud_type": "未知",
                "explanation": "處理圖片時發生技術錯誤。",
                "suggestions": "建議您手動檢查此圖片是否存在可疑內容。"
            }
    
    def analyze_image_from_url(self, image_url: str, analysis_type: str = "GENERAL", context_message: str = "") -> Dict:
        """
        從URL下載並分析圖片
        
        Args:
            image_url: 圖片URL
            analysis_type: 分析類型
            context_message: 用戶提供的上下文信息
            
        Returns:
            Dict: 分析結果
        """
        try:
            # 下載圖片
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                return {
                    "success": False,
                    "message": f"下載圖片失敗，狀態碼: {response.status_code}",
                    "risk_level": "無法判定",
                    "fraud_type": "未知",
                    "explanation": "無法下載圖片進行分析。",
                    "suggestions": "請確保圖片URL有效，或直接上傳圖片。"
                }
            
            # 分析圖片
            return self.analyze_image(response.content, analysis_type, context_message)
            
        except Exception as e:
            logger.exception(f"從URL下載並分析圖片時發生錯誤: {e}")
            return {
                "success": False,
                "message": f"從URL下載並分析圖片時發生錯誤: {str(e)}",
                "risk_level": "無法判定",
                "fraud_type": "未知",
                "explanation": "處理圖片URL時發生技術錯誤。",
                "suggestions": "建議直接上傳圖片，或確保URL是有效的圖片鏈接。"
            }
    
    def _resize_image_if_needed(self, image: Image.Image, max_size: int = 1024) -> Image.Image:
        """
        如果圖片太大，調整其大小以減少API請求大小
        
        Args:
            image: PIL圖片對象
            max_size: 最大寬度或高度
            
        Returns:
            Image.Image: 調整大小後的圖片
        """
        width, height = image.size
        
        if width <= max_size and height <= max_size:
            return image
        
        # 計算新尺寸，保持原始寬高比
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        # 調整圖片大小
        return image.resize((new_width, new_height), Image.LANCZOS)
    
    def _get_analysis_prompt(self, analysis_type: str, context_message: str) -> str:
        """
        根據分析類型獲取適當的提示語
        
        Args:
            analysis_type: 分析類型
            context_message: 用戶提供的上下文信息
            
        Returns:
            str: 適合該分析類型的提示語
        """
        base_prompt = """你是一位專門幫助用戶識別詐騙的AI助手，專注於分析圖片中可能的詐騙風險。

請按照以下固定格式回答：

風險等級：[極高/高/中高/中/低/極低/無風險]
詐騙類型：[具體的詐騙類型，如：釣魚網站、假交友詐騙、投資詐騙等]
說明：[用簡單易懂的話解釋為什麼有風險或沒有風險，像鄰居朋友在聊天的語氣，避免複雜術語]
建議：[用emoji符號（🚫🔍🌐🛡️💡⚠️等）開頭，給出簡單明確的防範建議]

重要提醒：
1. 請務必詳細觀察圖片中的所有元素，包括文字、標誌、界面設計等
2. 特別注意網址、聯繫方式、付款信息等敏感內容
3. 考慮這些元素是否與已知的詐騙手法相符
4. 請用中文回答
"""

        # 根據分析類型添加專門的提示
        if analysis_type == "PHISHING":
            base_prompt += """
針對釣魚網站截圖的特別注意事項：
- 檢查URL是否有拼寫錯誤或奇怪的域名
- 注意頁面佈局是否專業，或有明顯的設計缺陷
- 查看是否有不尋常的登錄請求或個人信息索取
- 關注網站是否有HTTPS連接
- 檢查logo、品牌元素是否與官方一致
"""
        elif analysis_type == "DOCUMENT":
            base_prompt += """
針對可疑文件截圖的特別注意事項：
- 檢查文件格式是否專業，是否有語法或拼寫錯誤
- 注意信頭、標誌和簽名是否看起來真實
- 關注聯繫信息是否與官方一致
- 查看是否有緊急性或威脅性語言
- 檢查付款要求或銀行信息是否存在
"""
        elif analysis_type == "SOCIAL_MEDIA":
            base_prompt += """
針對社交媒體詐騙截圖的特別注意事項：
- 檢查個人資料是否有可疑特徵（新帳號、少量朋友、不完整信息）
- 注意是否有不合理的優惠或贈品
- 關注是否有要求私下聯繫或轉向其他平台
- 查看評論和互動是否看起來真實
- 檢查是否使用名人或機構身份但無官方認證
"""
        
        return base_prompt
    
    def _parse_analysis_result(self, result: str) -> Dict:
        """
        解析OpenAI返回的詐騙分析結果
        
        Args:
            result: OpenAI返回的文本結果
            
        Returns:
            Dict: 結構化的分析結果
        """
        try:
            lines = result.strip().split('\n')
            parsed_result = {
                "risk_level": "中風險",  # 預設值
                "fraud_type": "未知",
                "explanation": "無法解析分析結果。",
                "suggestions": "建議謹慎處理。"
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith("風險等級：") or line.startswith("風險等級:"):
                    parsed_result["risk_level"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif line.startswith("詐騙類型：") or line.startswith("詐騙類型:"):
                    parsed_result["fraud_type"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif line.startswith("說明：") or line.startswith("說明:"):
                    parsed_result["explanation"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif line.startswith("建議：") or line.startswith("建議:"):
                    parsed_result["suggestions"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            
            # 如果說明為空，嘗試從整個回應中提取
            if not parsed_result["explanation"] or parsed_result["explanation"] == "無法解析分析結果。":
                # 移除標籤，取得剩餘內容作為說明
                clean_text = result
                for prefix in ["風險等級：", "風險等級:", "詐騙類型：", "詐騙類型:", "說明：", "說明:", "建議：", "建議:"]:
                    clean_text = clean_text.replace(prefix, "")
                
                # 清理並取得有意義的內容
                clean_lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
                if clean_lines:
                    parsed_result["explanation"] = clean_lines[0]
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"解析分析結果時發生錯誤: {e}")
            return {
                "risk_level": "中風險",
                "fraud_type": "解析錯誤",
                "explanation": "分析結果解析失敗，建議人工檢查。",
                "suggestions": "🔍 請仔細檢查圖片內容\n🛡️ 如有疑慮請諮詢專家"
            }
    
    def detect_qr_code(self, image_content: bytes) -> Dict:
        """
        檢測圖片中的QR碼並分析其風險
        
        Args:
            image_content: 圖片二進制內容
            
        Returns:
            Dict: 分析結果，包含是否發現QR碼、QR碼内容和風險評估
        """
        try:
            # 如果安裝了pyzbar庫，可以直接解析QR碼
            # 但由於環境限制，這裡使用OpenAI Vision API來協助檢測
            image = Image.open(BytesIO(image_content))
            image = self._resize_image_if_needed(image)
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            prompt = """請仔細檢查圖片中是否包含QR碼或條形碼。如果有，請告訴我：
1. 碼的類型（QR碼、條形碼等）
2. 碼在圖片中的位置
3. 如果你能看出，請告訴我這個碼可能連接到什麼（URL、付款等）
4. 從詐騙風險角度評估這個碼的可疑程度

請按以下格式回答：
包含碼：[是/否]
碼類型：[QR碼/條形碼/其他]
位置：[描述在圖片中的位置]
內容：[如果可見，描述內容]
風險評估：[高/中/低] - [簡短說明]"""
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位專門分析圖片中QR碼和條形碼的安全專家，請用中文回答。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=600
            )
            
            result = response.choices[0].message.content
            logger.info(f"QR碼分析結果: {result[:100]}...")
            
            # 解析QR碼結果
            contains_code = "是" in result.split("包含碼：")[-1].split("\n")[0]
            risk_level = "低"
            
            if "風險評估：" in result:
                risk_part = result.split("風險評估：")[-1].strip()
                if "高" in risk_part.split(" ")[0]:
                    risk_level = "高"
                elif "中" in risk_part.split(" ")[0]:
                    risk_level = "中"
            
            return {
                "success": True,
                "contains_qr_code": contains_code,
                "raw_result": result,
                "risk_level": risk_level,
                "explanation": result
            }
            
        except Exception as e:
            logger.exception(f"檢測QR碼時發生錯誤: {e}")
            return {
                "success": False,
                "contains_qr_code": False,
                "message": f"檢測QR碼時發生錯誤: {str(e)}",
                "risk_level": "無法判定",
                "explanation": "處理圖片時發生技術錯誤。"
            }
    
    def extract_text_from_image(self, image_content: bytes) -> str:
        """
        從圖片中提取文字
        
        Args:
            image_content: 圖片二進制內容
            
        Returns:
            str: 提取的文字
        """
        try:
            # 使用OpenAI Vision API提取文字
            image = Image.open(BytesIO(image_content))
            image = self._resize_image_if_needed(image)
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位專門從圖片中提取文字的助手。請僅返回圖片中的文字內容，不要添加任何評論或分析。如果圖片中沒有文字，請回答「圖片中沒有可辨識的文字」。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "請提取這張圖片中的所有文字內容，保持原始格式和排列。"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=600
            )
            
            result = response.choices[0].message.content
            logger.info(f"文字提取結果 (部分): {result[:100]}...")
            
            return result
            
        except Exception as e:
            logger.exception(f"從圖片提取文字時發生錯誤: {e}")
            return "無法從圖片中提取文字。"


# 創建服務實例
image_analysis_service = ImageAnalysisService()

# 提供便捷的函數接口
def analyze_image(image_content: bytes, analysis_type: str = "GENERAL", context_message: str = "") -> Dict:
    """分析圖片內容，檢測詐騙風險"""
    return image_analysis_service.analyze_image(image_content, analysis_type, context_message)

def analyze_image_from_url(image_url: str, analysis_type: str = "GENERAL", context_message: str = "") -> Dict:
    """從URL下載並分析圖片，檢測詐騙風險"""
    return image_analysis_service.analyze_image_from_url(image_url, analysis_type, context_message)

def detect_qr_code(image_content: bytes) -> Dict:
    """檢測圖片中的QR碼並分析其風險"""
    return image_analysis_service.detect_qr_code(image_content)

def extract_text_from_image(image_content: bytes) -> str:
    """從圖片中提取文字內容"""
    return image_analysis_service.extract_text_from_image(image_content)


if __name__ == "__main__":
    # 測試功能
    print("=== 圖片分析服務測試 ===")
    
    try:
        # 檢查是否設置了OpenAI API金鑰
        if not os.environ.get("OPENAI_API_KEY"):
            print("❌ 測試失敗：未設置OPENAI_API_KEY環境變量")
        else:
            print("✅ OpenAI API金鑰已設置")
            
            # 測試從文件加載圖片
            test_image_path = "test_image.jpg"  # 需要提前準備測試圖片
            if os.path.exists(test_image_path):
                with open(test_image_path, "rb") as f:
                    image_content = f.read()
                    
                # 測試圖片分析
                result = analyze_image(image_content, "GENERAL")
                print(f"✅ 圖片分析結果: {result.get('risk_level')} - {result.get('fraud_type')}")
                
                # 測試QR碼檢測
                qr_result = detect_qr_code(image_content)
                print(f"✅ QR碼檢測結果: 包含QR碼 = {qr_result.get('contains_qr_code')}")
                
                # 測試文字提取
                text_result = extract_text_from_image(image_content)
                print(f"✅ 文字提取結果 (部分): {text_result[:100]}...")
            else:
                print(f"❌ 測試失敗：找不到測試圖片 {test_image_path}")
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
    
    print("🎉 測試完成！") 