#!/usr/bin/env python3
"""
Flex Message 服務模組
提供各種 Flex Message 的創建和管理功能
"""

import json
import logging
import random
from typing import Dict, List, Optional, Any
from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, 
    SeparatorComponent, ButtonComponent, URIAction, PostbackAction, MessageAction
)

logger = logging.getLogger(__name__)

class FlexMessageService:
    """Flex Message 服務類"""
    
    def __init__(self):
        self.colors = {
            "primary": "#1DB446",
            "secondary": "#464F69", 
            "accent": "#FF6B6B",
            "warning": "#FFA726",
            "danger": "#F44336",
            "success": "#4CAF50",
            "info": "#2196F3"
        }

    def create_analysis_flex_message(self, analysis_data: Dict, display_name: str, 
                                   message_to_analyze: str, user_id: Optional[str] = None) -> FlexSendMessage:
        """創建詐騙分析結果的 Flex Message"""
        
        risk_level = analysis_data.get("risk_level", "不確定")
        fraud_type = analysis_data.get("fraud_type", "未知")
        explanation = analysis_data.get("explanation", "無法分析")
        suggestions = analysis_data.get("suggestions", "請保持警覺")
        
        # 根據風險等級選擇顏色
        risk_color = self._get_risk_color(risk_level)
        risk_emoji = self._get_risk_emoji(risk_level)
        
        # 創建 Flex Message 內容
        bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color=risk_color,
                spacing='md',
                contents=[
                    TextComponent(
                        text=f"{risk_emoji} 詐騙風險分析",
                        weight='bold',
                        color='#ffffff',
                        size='xl'
                    ),
                    TextComponent(
                        text=f"風險等級：{risk_level}",
                        color='#ffffff',
                        size='md'
                    )
                ]
            ),
            body=BoxComponent(
                layout='vertical',
                padding_all='20px',
                spacing='md',
                contents=[
                    TextComponent(
                        text=f"@{display_name}",
                        weight='bold',
                        size='lg',
                        color=self.colors["primary"]
                    ),
                    SeparatorComponent(margin='md'),
                    TextComponent(
                        text=f"詐騙類型：{fraud_type}",
                        size='md',
                        weight='bold',
                        margin='md'
                    ),
                    TextComponent(
                        text=explanation,
                        size='sm',
                        color=self.colors["secondary"],
                        wrap=True,
                        margin='md'
                    ),
                    SeparatorComponent(margin='md'),
                    TextComponent(
                        text="🛡️ 防範建議",
                        weight='bold',
                        size='md',
                        margin='md'
                    ),
                    TextComponent(
                        text=suggestions,
                        size='sm',
                        color=self.colors["secondary"],
                        wrap=True,
                        margin='sm'
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
                        action=URIAction(
                            label='📞 撥打165反詐騙專線',
                            uri='tel:165'
                        )
                    ),
                    ButtonComponent(
                        style='secondary',
                        height='sm',
                        action=PostbackAction(
                            label='🎮 玩土豆遊戲放鬆一下',
                            data=f'action=potato_game&user_id={user_id or "unknown"}'
                        )
                    )
                ]
            )
        )
        
        return FlexSendMessage(alt_text=f"詐騙風險分析：{risk_level}", contents=bubble)

    def create_domain_spoofing_flex_message(self, spoofing_result: Dict, display_name: str,
                                          message_to_analyze: str, user_id: Optional[str] = None) -> FlexSendMessage:
        """創建網域變形攻擊警告的 Flex Message"""
        
        suspicious_domain = spoofing_result.get("suspicious_domain", "未知網域")
        legitimate_domain = spoofing_result.get("legitimate_domain", "未知網域")
        attack_type = spoofing_result.get("attack_type", "未知攻擊")
        similarity_score = spoofing_result.get("similarity_score", 0)
        
        # 從safe_domains.json獲取正版網站的描述
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
            
            legitimate_description = flattened_safe_domains.get(legitimate_domain, "正版網站")
        except Exception as e:
            legitimate_description = "正版網站"
        
        # 生成可疑網域的說明
        suspicious_explanation = self._generate_suspicious_domain_explanation(
            suspicious_domain, legitimate_domain, attack_type
        )
        
        bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color=self.colors["danger"],
                spacing='md',
                contents=[
                    TextComponent(
                        text="🚨 網域變形攻擊警告",
                        weight='bold',
                        color='#ffffff',
                        size='xl'
                    ),
                    TextComponent(
                        text="檢測到可疑網域",
                        color='#ffffff',
                        size='md'
                    )
                ]
            ),
            body=BoxComponent(
                layout='vertical',
                padding_all='20px',
                spacing='md',
                contents=[
                    TextComponent(
                        text="⚠️ 詐騙集團可能假冒此網域騙取您的信用卡或銀行帳戶個資，請務必小心！",
                        weight='bold',
                        size='md',
                        color=self.colors["danger"],
                        wrap=True
                    ),
                    SeparatorComponent(margin='md'),
                    TextComponent(
                        text="⚠️ 網域對比分析",
                        weight='bold',
                        size='md',
                        margin='md'
                    ),
                    TextComponent(
                        text=f"可疑網域：{suspicious_domain}",
                        size='sm',
                        color=self.colors["danger"],
                        wrap=True,
                        margin='sm',
                        weight='bold'
                    ),
                    TextComponent(
                        text=suspicious_explanation,
                        size='xs',
                        color=self.colors["danger"],
                        wrap=True,
                        margin='xs'
                    ),
                    TextComponent(
                        text=f"正版網域：{legitimate_domain}",
                        size='sm',
                        color=self.colors["success"],
                        wrap=True,
                        margin='sm',
                        weight='bold'
                    ),
                    TextComponent(
                        text=legitimate_description,
                        size='xs',
                        color=self.colors["success"],
                        wrap=True,
                        margin='xs'
                    ),
                    TextComponent(
                        text=f"相似度：{similarity_score:.1%}",
                        size='xs',
                        color=self.colors["secondary"],
                        margin='sm'
                    ),
                    SeparatorComponent(margin='md'),
                    TextComponent(
                        text="🛡️ 緊急建議",
                        weight='bold',
                        size='md',
                        margin='md'
                    ),
                    TextComponent(
                        text="🚫 立即停止使用此網站\n🔍 確認網址拼寫是否正確\n🌐 直接搜尋正版網站名稱\n🛡️ 如已輸入資料請立即更改密碼\n💳 檢查信用卡及銀行帳戶異常",
                        size='sm',
                        color=self.colors["secondary"],
                        wrap=True,
                        margin='sm'
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
                        action=URIAction(
                            label='📞 立即撥打165專線',
                            uri='tel:165'
                        )
                    ),
                    ButtonComponent(
                        style='secondary',
                        height='sm',
                        action=PostbackAction(
                            label='🎮 玩土豆遊戲放鬆一下',
                            data=f'action=potato_game&user_id={user_id or "unknown"}'
                        )
                    )
                ]
            )
        )
        
        return FlexSendMessage(alt_text=f"網域變形攻擊警告：{suspicious_domain}", contents=bubble)

    def _generate_suspicious_domain_explanation(self, suspicious_domain: str, legitimate_domain: str, attack_type: str) -> str:
        """生成可疑網域的說明文字"""
        explanations = {
            "字元替換攻擊": f"將正版網域中的字元替換（如 o→0, l→1）",
            "插入額外字元": f"在正版網域中插入額外字元（如加入 -tw, -official 等）",
            "網域後綴變形": f"修改網域後綴來混淆視聽",
            "相似字元攻擊": f"使用外觀相似的字元（如希臘字母、俄文字母）"
        }
        
        base_explanation = explanations.get(attack_type, "模仿正版網域的變形攻擊")
        
        # 分析具體的變形方式
        if "-tw" in suspicious_domain and "-tw" not in legitimate_domain:
            return f"{base_explanation}，在網域中加入了 '-tw' 來偽裝成台灣官方網站"
        elif "-official" in suspicious_domain:
            return f"{base_explanation}，加入了 '-official' 來偽裝成官方網站"
        elif len(suspicious_domain) > len(legitimate_domain):
            return f"{base_explanation}，在正版網域基礎上添加了額外字元"
        else:
            return base_explanation

    def create_donation_flex_message(self) -> FlexSendMessage:
        """創建贊助彩蛋的 Flex Message"""
        
        bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color=self.colors["accent"],
                spacing='md',
                contents=[
                    TextComponent(
                        text="🎉 恭喜你，這是我們的小彩蛋",
                        weight='bold',
                        color='#ffffff',
                        size='xl',
                        wrap=True
                    ),
                    TextComponent(
                        text="感謝你發現了我們的贊助連結！",
                        color='#ffffff',
                        size='md',
                        wrap=True
                    )
                ]
            ),
            body=BoxComponent(
                layout='vertical',
                padding_all='20px',
                spacing='md',
                contents=[
                    TextComponent(
                        text="❤️ 感謝訊息",
                        weight='bold',
                        size='lg',
                        color=self.colors["primary"]
                    ),
                    SeparatorComponent(margin='md'),
                    TextComponent(
                        text="謝謝你對土豆防詐騙機器人的支持！你的每一份贊助都能幫助我們：",
                        size='md',
                        color=self.colors["secondary"],
                        wrap=True,
                        margin='md'
                    ),
                    TextComponent(
                        text="☕ 維持伺服器運作\n🔄 持續更新詐騙資料庫\n🛡️ 保護更多人免受詐騙\n💡 開發新功能",
                        size='sm',
                        color=self.colors["secondary"],
                        wrap=True,
                        margin='md'
                    ),
                    SeparatorComponent(margin='md'),
                    TextComponent(
                        text="🎁 特別感謝",
                        weight='bold',
                        size='md',
                        margin='md'
                    ),
                    TextComponent(
                        text="每一位贊助者都是我們的英雄，讓我們能夠繼續守護大家的財產安全！",
                        size='sm',
                        color=self.colors["secondary"],
                        wrap=True,
                        margin='sm'
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
                        action=URIAction(
                            label='☕ 贊助土豆',
                            uri='https://buymeacoffee.com/todao_antifraud'
                        )
                    ),
                    ButtonComponent(
                        style='secondary',
                        height='sm',
                        action=PostbackAction(
                            label='🎮 玩土豆遊戲',
                            data='action=potato_game'
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
        
        return FlexSendMessage(alt_text="感謝你的支持！這是我們的小彩蛋", contents=bubble)

    def create_weather_flex_message(self, weather_data: Dict, user_name: str = "朋友") -> FlexSendMessage:
        """創建天氣預報的 Flex Message"""
        
        city = weather_data.get("city", "未知城市")
        forecast = weather_data.get("forecast", [])
        source = weather_data.get("source", "中央氣象署")
        
        if not forecast:
            # 錯誤情況的簡單 Flex Message
            bubble = BubbleContainer(
                direction='ltr',
                body=BoxComponent(
                    layout='vertical',
                    contents=[
                        TextComponent(
                            text=f"@{user_name} ❌ 無法取得{city}的天氣資訊",
                            wrap=True
                        )
                    ]
                )
            )
            return FlexSendMessage(alt_text="天氣資訊錯誤", contents=bubble)
        
        # 創建天氣預報內容
        body_contents = [
            TextComponent(
                text=f"@{user_name}",
                weight='bold',
                size='lg',
                color=self.colors["primary"]
            ),
            SeparatorComponent(margin='md')
        ]
        
        for i, day_data in enumerate(forecast[:3]):  # 最多顯示3天
            date = day_data.get("date", "")
            weekday = day_data.get("weekday", "")
            weather = day_data.get("weather", "")
            temp = day_data.get("temperature", {})
            rain_prob = day_data.get("rain_probability", "")
            
            weather_emoji = self._get_weather_emoji(weather)
            
            if i > 0:
                body_contents.append(SeparatorComponent(margin='md'))
            
            body_contents.extend([
                TextComponent(
                    text=f"{weather_emoji} {date} {weekday}",
                    weight='bold',
                    size='md',
                    margin='md'
                ),
                TextComponent(
                    text=f"天氣：{weather}",
                    size='sm',
                    color=self.colors["secondary"],
                    margin='sm'
                ),
                TextComponent(
                    text=f"溫度：{temp.get('low', '')}°C - {temp.get('high', '')}°C",
                    size='sm',
                    color=self.colors["secondary"],
                    margin='xs'
                ),
                TextComponent(
                    text=f"降雨機率：{rain_prob}",
                    size='sm',
                    color=self.colors["secondary"],
                    margin='xs'
                )
            ])
        
        # 添加資料來源
        body_contents.extend([
            SeparatorComponent(margin='md'),
            TextComponent(
                text=f"📡 資料來源：{source}",
                size='xs',
                color=self.colors["secondary"],
                margin='md'
            )
        ])
        
        bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color=self.colors["info"],
                contents=[
                    TextComponent(
                        text=f"🌤️ {city} 天氣預報",
                        weight='bold',
                        color='#ffffff',
                        size='xl'
                    )
                ]
            ),
            body=BoxComponent(
                layout='vertical',
                padding_all='20px',
                spacing='sm',
                contents=body_contents
            ),
            footer=BoxComponent(
                layout='vertical',
                spacing='sm',
                contents=[
                    ButtonComponent(
                        style='secondary',
                        height='sm',
                        action=URIAction(
                            label='🌐 中央氣象署',
                            uri='https://www.cwb.gov.tw/'
                        )
                    )
                ]
            )
        )
        
        return FlexSendMessage(alt_text=f"{city}天氣預報", contents=bubble)

    def _get_risk_color(self, risk_level: str) -> str:
        """根據風險等級取得對應顏色"""
        color_map = {
            "極高": self.colors["danger"],
            "高": self.colors["warning"],
            "中高": self.colors["warning"],
            "中": "#FFA726",
            "低": self.colors["success"],
            "極低": self.colors["success"],
            "無風險": self.colors["success"]
        }
        return color_map.get(risk_level, self.colors["warning"])

    def _get_risk_emoji(self, risk_level: str) -> str:
        """根據風險等級取得對應emoji"""
        emoji_map = {
            "極高": "🚨",
            "高": "⚠️",
            "中高": "⚠️",
            "中": "⚡",
            "低": "✅",
            "極低": "✅",
            "無風險": "✅"
        }
        return emoji_map.get(risk_level, "⚡")

    def _get_weather_emoji(self, weather: str) -> str:
        """根據天氣狀況取得對應emoji"""
        if "晴" in weather:
            return "☀️"
        elif "雨" in weather:
            return "🌧️"
        elif "雷" in weather:
            return "⛈️"
        elif "雲" in weather or "多雲" in weather:
            return "☁️"
        elif "陰" in weather:
            return "🌫️"
        else:
            return "🌤️"


# 創建全域服務實例
flex_message_service = FlexMessageService()

# 提供便捷的函數接口
def create_analysis_flex_message(analysis_data: Dict, display_name: str, 
                                message_to_analyze: str, user_id: Optional[str] = None) -> FlexSendMessage:
    """創建詐騙分析結果的 Flex Message"""
    return flex_message_service.create_analysis_flex_message(analysis_data, display_name, message_to_analyze, user_id)

def create_domain_spoofing_flex_message(spoofing_result: Dict, display_name: str,
                                      message_to_analyze: str, user_id: Optional[str] = None) -> FlexSendMessage:
    """創建網域變形攻擊警告的 Flex Message"""
    return flex_message_service.create_domain_spoofing_flex_message(spoofing_result, display_name, message_to_analyze, user_id)

def create_donation_flex_message() -> FlexSendMessage:
    """創建贊助彩蛋的 Flex Message"""
    return flex_message_service.create_donation_flex_message()

def create_weather_flex_message(weather_data: Dict, user_name: str = "朋友") -> FlexSendMessage:
    """創建天氣預報的 Flex Message"""
    return flex_message_service.create_weather_flex_message(weather_data, user_name)


if __name__ == "__main__":
    # 測試功能
    print("=== Flex Message 服務測試 ===")
    
    # 測試詐騙分析 Flex Message
    test_analysis_data = {
        "risk_level": "高",
        "fraud_type": "假交友投資詐騙",
        "explanation": "這是一個典型的假交友投資詐騙案例",
        "suggestions": "🚫 不要相信網路投資\n🔍 查證投資平台合法性"
    }
    
    analysis_flex = create_analysis_flex_message(test_analysis_data, "測試用戶", "測試訊息")
    print("✅ 詐騙分析 Flex Message 創建成功")
    
    # 測試贊助彩蛋 Flex Message
    donation_flex = create_donation_flex_message()
    print("✅ 贊助彩蛋 Flex Message 創建成功")
    
    print("🎉 所有測試通過！") 