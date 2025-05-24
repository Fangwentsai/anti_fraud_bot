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
    SeparatorComponent, ButtonComponent, URIAction, PostbackAction, MessageAction,
    MessageEvent, TextMessage, TextSendMessage, PostbackEvent, QuickReply, QuickReplyButton
)

logger = logging.getLogger(__name__)

def safe_text_component(text: str, **kwargs) -> TextComponent:
    """創建安全的文字組件，確保文字不為空"""
    # 確保文字不為空或僅包含空白字符
    safe_text = str(text).strip() if text is not None else ""
    if not safe_text:
        safe_text = "無內容"  # 預設文字
    
    return TextComponent(text=safe_text, **kwargs)

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
        
        # 安全地獲取數據，並提供預設值
        risk_level = str(analysis_data.get("risk_level", "不確定")).strip() or "不確定"
        fraud_type = str(analysis_data.get("fraud_type", "未知")).strip() or "未知"
        explanation = str(analysis_data.get("explanation", "分析結果不完整")).strip() or "分析結果不完整"
        suggestions = str(analysis_data.get("suggestions", "請保持警覺")).strip() or "請保持警覺"
        display_name = str(display_name).strip() or "用戶"
        
        # 確保用戶ID有值
        safe_user_id = user_id if user_id else "unknown"
        
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
                    safe_text_component(
                        f"{risk_emoji} 詐騙風險分析",
                        weight='bold',
                        color='#ffffff',
                        size='xl'
                    ),
                    safe_text_component(
                        f"風險等級：{risk_level}",
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
                    safe_text_component(
                        f"詐騙類型：{fraud_type}",
                        size='md',
                        weight='bold',
                        margin='md'
                    ),
                    safe_text_component(
                        explanation,
                        size='sm',
                        color=self.colors["secondary"],
                        wrap=True,
                        margin='md'
                    ),
                    SeparatorComponent(margin='md'),
                    safe_text_component(
                        "🛡️ 防範建議",
                        weight='bold',
                        size='md',
                        margin='md'
                    ),
                    safe_text_component(
                        suggestions if "\n" in suggestions else suggestions.replace("。", "。\n").replace("，", "，\n"),
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
                        action=MessageAction(
                            label='🔄 再測一次',
                            text='土豆 請幫我分析這則訊息：'
                        ),
                        color='#2E86C1'
                    ),
                    ButtonComponent(
                        style='primary',
                        height='sm',
                        action=PostbackAction(
                            label='🏠 回到首頁',
                            data=f'action=show_main_menu&user_id={safe_user_id}'
                        ),
                        color='#27AE60'
                    ),
                    ButtonComponent(
                        style='primary',
                        height='sm',
                        action=PostbackAction(
                            label='📝 回報註記',
                            data=f'action=report_feedback&user_id={safe_user_id}'
                        ),
                        color='#E67E22'
                    )
                ]
            )
        )
        
        return FlexSendMessage(alt_text=f"詐騙風險分析：{risk_level}", contents=bubble)

    def create_domain_spoofing_flex_message(self, spoofing_result: Dict, display_name: str,
                                          message_to_analyze: str, user_id: Optional[str] = None) -> FlexSendMessage:
        """創建網域變形攻擊警告的 Flex Message"""
        
        # 安全地獲取數據
        suspicious_domain = str(spoofing_result.get("spoofed_domain", "未知網域")).strip() or "未知網域"
        legitimate_domain = str(spoofing_result.get("original_domain", "未知網域")).strip() or "未知網域"
        attack_type = str(spoofing_result.get("spoofing_type", "未知攻擊")).strip() or "未知攻擊"
        safe_user_id = user_id if user_id else "unknown"
        
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
        
        # 確保描述不為空
        legitimate_description = str(legitimate_description).strip() or "正版網站"
        
        # 生成可疑網域的說明
        suspicious_explanation = self._generate_suspicious_domain_explanation(
            suspicious_domain, legitimate_domain, attack_type
        )
        
        # 確保說明不為空
        suspicious_explanation = str(suspicious_explanation).strip() or "這是一個可疑的假冒網域"
        
        bubble = BubbleContainer(
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                padding_all='20px',
                background_color=self.colors["danger"],
                spacing='md',
                contents=[
                    safe_text_component(
                        "🚨 網域偽裝攻擊警告",
                        weight='bold',
                        color='#ffffff',
                        size='xl'
                    ),
                    safe_text_component(
                        "檢測到可疑網域",
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
                    safe_text_component(
                        "⚠️ 詐騙集團可能假冒此網域騙取您的信用卡或銀行帳戶個資，請務必小心！",
                        weight='bold',
                        size='md',
                        color=self.colors["danger"],
                        wrap=True
                    ),
                    SeparatorComponent(margin='md'),
                    safe_text_component(
                        "⚠️ 網域對比分析",
                        weight='bold',
                        size='md',
                        margin='md'
                    ),
                    safe_text_component(
                        f"可疑網域：{suspicious_domain}",
                        size='sm',
                        color=self.colors["danger"],
                        wrap=True,
                        margin='sm',
                        weight='bold'
                    ),
                    safe_text_component(
                        suspicious_explanation,
                        size='xs',
                        color=self.colors["danger"],
                        wrap=True,
                        margin='xs'
                    ),
                    safe_text_component(
                        f"正版網域：{legitimate_domain}",
                        size='sm',
                        color=self.colors["success"],
                        wrap=True,
                        margin='sm',
                        weight='bold'
                    ),
                    safe_text_component(
                        legitimate_description,
                        size='xs',
                        color=self.colors["success"],
                        wrap=True,
                        margin='xs'
                    ),
                    SeparatorComponent(margin='md'),
                    safe_text_component(
                        "🛡️ 緊急建議",
                        weight='bold',
                        size='md',
                        margin='md'
                    ),
                    safe_text_component(
                        "🚫 立即停止使用此網站\n🔍 確認網址拼寫是否正確\n🌐 直接搜尋正版網站名稱\n🛡️ 如已輸入資料請立即更改密碼\n💳 檢查信用卡及銀行帳戶異常",
                        size='sm',
                        color=self.colors["secondary"],
                        wrap=True,
                        margin='sm'
                    )
                ]
            ),
            # footer=BoxComponent(
            #     layout='vertical',
            #     spacing='sm',
            #     contents=[
            #         ButtonComponent(
            #             style='primary',
            #             height='sm',
            #             action=URIAction(
            #                 label='📞 立即撥打165專線',
            #                 uri='tel:165'
            #             )
            #         ),
            #         ButtonComponent(
            #             style='secondary',
            #             height='sm',
            #             action=PostbackAction(
            #                 label='🎮 玩土豆遊戲放鬆一下',
            #                 data=f'action=potato_game&user_id={safe_user_id}'
            #             )
            #         )
            #     ]
            # )
        )
        
        return FlexSendMessage(alt_text=f"網域偽裝攻擊警告：{suspicious_domain}", contents=bubble)

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
                    # ButtonComponent(
                    #     style='secondary',
                    #     height='sm',
                    #     action=PostbackAction(
                    #         label='📊 查看防詐統計',
                    #         data='action=fraud_stats'
                    #     )
                    # )
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

    def create_fraud_detail_flex_message(self, fraud_type: str, fraud_info: Dict, display_name: str = "朋友", page: int = 1) -> FlexSendMessage:
        """創建詐騙類型詳細信息的Flex Message
        
        Args:
            fraud_type: 詐騙類型名稱
            fraud_info: 詐騙類型信息
            display_name: 用戶顯示名稱
            page: 當前頁碼，默認為第1頁
        """
        
        # 記錄收到的詐騙類型信息
        logger.info(f"創建詐騙類型詳情 Flex Message: {fraud_type}, 頁碼: {page}")
        logger.info(f"詐騙類型信息: {fraud_info}")
        
        # 處理嵌套的詐騙類型數據結構
        # 檢查是否存在子類型並提取第一個子類型的數據
        sub_type_data = None
        if not fraud_info.get("常見話術") and not fraud_info.get("詐騙流程"):
            # 如果頂層沒有常見話術和詐騙流程，嘗試提取第一個子類型的數據
            for sub_type, sub_data in fraud_info.items():
                if isinstance(sub_data, dict):
                    sub_type_data = sub_data
                    break
        
        # 如果找到子類型數據，使用它作為主要數據
        if sub_type_data:
            fraud_info = sub_type_data
        
        # 獲取詐騙類型信息
        description = fraud_info.get("description", "無相關說明")
        risk_level = fraud_info.get("risk_level", "中")
        sop_items = fraud_info.get("sop", [])
        
        # 獲取常見話術、詐騙流程和警示信號等信息
        common_tactics = fraud_info.get("常見話術", [])
        fraud_process = fraud_info.get("詐騙流程", [])
        warning_signals = fraud_info.get("警示信號", [])
        prevention_tips = fraud_info.get("防詐技巧", [])
        
        # 真實案例資訊
        real_case = fraud_info.get("真實案例", {})
        case_description = real_case.get("案例描述", "")
        loss_amount = real_case.get("損失金額", "")
        fraud_channels = real_case.get("詐騙管道", [])
        
        # 分頁邏輯 - 內容按頁分配
        # 計算總頁數（最少1頁，最多4頁）
        total_pages = 1
        
        # 根據內容量決定頁數
        if (common_tactics and len(common_tactics) > 0) or (fraud_process and len(fraud_process) > 0):
            total_pages += 1
        
        if case_description or (warning_signals and len(warning_signals) > 0):
            total_pages += 1
            
        if prevention_tips and len(prevention_tips) > 0:
            total_pages += 1
        
        # 確保頁碼合法
        page = max(1, min(page, total_pages))
        
        # 根據風險等級選擇顏色
        header_color = "#3498DB"  # 默認藍色
        if risk_level == "極高":
            header_color = "#E74C3C"  # 紅色
        elif risk_level == "高":
            header_color = "#F39C12"  # 橙色
        elif risk_level == "中":
            header_color = "#3498DB"  # 藍色
        elif risk_level == "低":
            header_color = "#2ECC71"  # 綠色
        
        # 創建詳情頁的內容
        body_contents = []
        
        # 創建頁碼指示器
        body_contents.append(
            TextComponent(
                text=f"第 {page} 頁 / 共 {total_pages} 頁",
                size="xs",
                color="#888888",
                align="center"
            )
        )
        
        body_contents.append(SeparatorComponent(margin="sm"))
        
        # 根據當前頁碼顯示不同內容
        if page == 1:
            # 第1頁：顯示詐騙類型基本介紹
            # 添加詐騙類型描述
            if description and description != "無相關說明":
                body_contents.append(
                    TextComponent(
                        text=description,
                        wrap=True,
                        size="md",
                        margin="md"
                    )
                )
            else:
                # 如果沒有描述，則顯示默認內容並加入風險等級說明
                body_contents.append(
                    TextComponent(
                        text=f"這是一種常見的{fraud_type}，風險等級為「{risk_level}」。請注意以下特徵和防範方法。",
                        wrap=True,
                        size="md",
                        margin="md"
                    )
                )
                
            # 添加風險等級指示
            body_contents.append(
                BoxComponent(
                    layout="vertical",
                    margin="lg",
                    contents=[
                        BoxComponent(
                            layout="baseline",
                            contents=[
                                TextComponent(
                                    text="風險等級:",
                                    weight="bold",
                                    size="md",
                                    color="#555555",
                                    flex=3
                                ),
                                TextComponent(
                                    text=risk_level,
                                    weight="bold",
                                    size="md",
                                    color=self._get_risk_color(risk_level),
                                    flex=5
                                )
                            ]
                        )
                    ]
                )
            )
            
            # 添加常見話術預覽（如果有）
            if common_tactics and len(common_tactics) > 0:
                body_contents.append(
                    TextComponent(
                        text="📝 常見話術預覽",
                        weight="bold",
                        size="md",
                        margin="lg",
                        color="#1f76de"
                    )
                )
                
                # 只顯示前3個話術作為預覽
                tactics_text = ""
                for i, tactic in enumerate(common_tactics[:3]):
                    tactics_text += f"• {tactic}\n"
                
                if len(common_tactics) > 3:
                    tactics_text += "...更多常見話術請見下一頁"
                
                body_contents.append(
                    TextComponent(
                        text=tactics_text.strip(),
                        wrap=True,
                        size="sm",
                        margin="md"
                    )
                )
            elif fraud_process and len(fraud_process) > 0:
                # 如果沒有常見話術但有詐騙流程，顯示詐騙流程預覽
                body_contents.append(
                    TextComponent(
                        text="🔄 詐騙流程預覽",
                        weight="bold",
                        size="md",
                        margin="lg",
                        color="#1f76de"
                    )
                )
                
                # 只顯示前3個流程步驟作為預覽
                process_text = ""
                for i, step in enumerate(fraud_process[:3]):
                    process_text += f"{i+1}. {step}\n"
                
                if len(fraud_process) > 3:
                    process_text += "...更多詐騙流程請見下一頁"
                
                body_contents.append(
                    TextComponent(
                        text=process_text.strip(),
                        wrap=True,
                        size="sm",
                        margin="md"
                    )
                )
        
        elif page == 2:
            # 第2頁：顯示常見話術和詐騙流程
            # 添加常見話術區塊
            if common_tactics and len(common_tactics) > 0:
                body_contents.append(
                    TextComponent(
                        text="📝 常見話術",
                        weight="bold",
                        size="md",
                        margin="lg",
                        color="#1f76de"
                    )
                )
                
                tactics_text = ""
                for i, tactic in enumerate(common_tactics):  # 顯示全部話術
                    tactics_text += f"• {tactic}\n"
                
                body_contents.append(
                    TextComponent(
                        text=tactics_text.strip(),
                        wrap=True,
                        size="sm",
                        margin="md"
                    )
                )
                
                body_contents.append(SeparatorComponent(margin="lg"))
            
            # 添加詐騙流程區塊
            if fraud_process and len(fraud_process) > 0:
                body_contents.append(
                    TextComponent(
                        text="🔄 詐騙流程",
                        weight="bold",
                        size="md",
                        margin="lg",
                        color="#1f76de"
                    )
                )
                
                process_text = ""
                for i, step in enumerate(fraud_process):
                    process_text += f"{i+1}. {step}\n"
                
                body_contents.append(
                    TextComponent(
                        text=process_text.strip(),
                        wrap=True,
                        size="sm",
                        margin="md"
                    )
                )
            
            # 如果沒有常見話術和詐騙流程，顯示警示信號或防詐技巧
            if not common_tactics and not fraud_process:
                if warning_signals and len(warning_signals) > 0:
                    body_contents.append(
                        TextComponent(
                            text="⚠️ 警示信號",
                            weight="bold",
                            size="md",
                            margin="lg",
                            color="#1f76de"
                        )
                    )
                    
                    signals_text = ""
                    for signal in warning_signals:
                        signals_text += f"• {signal}\n"
                    
                    body_contents.append(
                        TextComponent(
                            text=signals_text.strip(),
                            wrap=True,
                            size="sm",
                            margin="md"
                        )
                    )
                elif prevention_tips and len(prevention_tips) > 0:
                    body_contents.append(
                        TextComponent(
                            text="🛡️ 防詐技巧",
                            weight="bold",
                            size="md",
                            margin="lg",
                            color="#1f76de"
                        )
                    )
                    
                    tips_text = ""
                    for tip in prevention_tips:
                        tips_text += f"• {tip}\n"
                    
                    body_contents.append(
                        TextComponent(
                            text=tips_text.strip(),
                            wrap=True,
                            size="sm",
                            margin="md"
                        )
                    )
        
        elif page == 3:
            # 第3頁：顯示真實案例和警示信號
            # 添加真實案例區塊
            if case_description:
                body_contents.append(
                    TextComponent(
                        text="📰 真實案例",
                        weight="bold",
                        size="md",
                        margin="lg",
                        color="#1f76de"
                    )
                )
                
                body_contents.append(
                    TextComponent(
                        text=case_description,
                        wrap=True,
                        size="sm",
                        margin="md"
                    )
                )
                
                if loss_amount:
                    body_contents.append(
                        TextComponent(
                            text=f"損失金額: {loss_amount}",
                            size="sm",
                            color="#E74C3C",
                            weight="bold",
                            margin="sm"
                        )
                    )
                
                if fraud_channels and len(fraud_channels) > 0:
                    body_contents.append(
                        TextComponent(
                            text=f"詐騙管道: {', '.join(fraud_channels)}",
                            size="sm",
                            color="#555555",
                            margin="sm"
                        )
                    )
                
                body_contents.append(SeparatorComponent(margin="lg"))
            
            # 添加警示信號區塊
            if warning_signals and len(warning_signals) > 0:
                body_contents.append(
                    TextComponent(
                        text="⚠️ 警示信號",
                        weight="bold",
                        size="md",
                        margin="lg",
                        color="#1f76de"
                    )
                )
                
                signals_text = ""
                for signal in warning_signals:
                    signals_text += f"• {signal}\n"
                
                body_contents.append(
                    TextComponent(
                        text=signals_text.strip(),
                        wrap=True,
                        size="sm",
                        margin="md"
                    )
                )
            
            # 如果沒有真實案例和警示信號，顯示防詐技巧
            if not case_description and not warning_signals:
                if prevention_tips and len(prevention_tips) > 0:
                    body_contents.append(
                        TextComponent(
                            text="🛡️ 防詐技巧",
                            weight="bold",
                            size="md",
                            margin="lg",
                            color="#1f76de"
                        )
                    )
                    
                    tips_text = ""
                    for tip in prevention_tips:
                        tips_text += f"• {tip}\n"
                    
                    body_contents.append(
                        TextComponent(
                            text=tips_text.strip(),
                            wrap=True,
                            size="sm",
                            margin="md"
                        )
                    )
        
        elif page == 4:
            # 第4頁：顯示防詐技巧
            if prevention_tips and len(prevention_tips) > 0:
                body_contents.append(
                    TextComponent(
                        text="🛡️ 防詐技巧",
                        weight="bold",
                        size="md",
                        margin="lg",
                        color="#1f76de"
                    )
                )
                
                tips_text = ""
                for tip in prevention_tips:
                    tips_text += f"• {tip}\n"
                
                body_contents.append(
                    TextComponent(
                        text=tips_text.strip(),
                        wrap=True,
                        size="sm",
                        margin="md"
                    )
                )
            else:
                # 如果沒有防詐技巧，顯示其他可能缺失的資訊
                if not common_tactics and not fraud_process and not warning_signals and not case_description:
                    body_contents.append(
                        TextComponent(
                            text="⚠️ 重要提醒",
                            weight="bold",
                            size="md",
                            margin="lg",
                            color="#1f76de"
                        )
                    )
                    
                    body_contents.append(
                        TextComponent(
                            text=f"遇到{fraud_type}請立即停止與對方聯繫，並撥打165反詐騙專線尋求協助。",
                            wrap=True,
                            size="md",
                            margin="md"
                        )
                    )
                else:
                    # 顯示已有資訊的摘要
                    body_contents.append(
                        TextComponent(
                            text="📌 謹記要點",
                            weight="bold",
                            size="md",
                            margin="lg",
                            color="#1f76de"
                        )
                    )
                    
                    summary_text = f"• {fraud_type}風險等級：{risk_level}\n"
                    if common_tactics and len(common_tactics) > 0:
                        summary_text += f"• 常見話術：{len(common_tactics)}種\n"
                    if fraud_process and len(fraud_process) > 0:
                        summary_text += f"• 詐騙流程：{len(fraud_process)}步驟\n"
                    if warning_signals and len(warning_signals) > 0:
                        summary_text += f"• 警示信號：{len(warning_signals)}種\n"
                    
                    body_contents.append(
                        TextComponent(
                            text=summary_text.strip(),
                            wrap=True,
                            size="sm",
                            margin="md"
                        )
                    )
            
            # 添加最後提醒
            body_contents.append(
                TextComponent(
                    text="📞 如有任何疑問，請撥打165反詐騙專線",
                    size="sm",
                    color="#888888",
                    margin="lg",
                    align="center"
                )
            )
        
        # 如果頁面內容為空，顯示一些基本信息
        if len(body_contents) <= 2:  # 只有頁碼指示器和分隔線
            body_contents.append(
                TextComponent(
                    text=f"{fraud_type}相關資訊",
                    weight="bold",
                    size="md",
                    margin="lg",
                    color="#1f76de"
                )
            )
            
            body_contents.append(
                TextComponent(
                    text="此頁面資訊暫時無法顯示，請查看其他頁面了解更多詳情。",
                    wrap=True,
                    size="md",
                    margin="md"
                )
            )
        
        # 創建頁面導航按鈕
        footer_contents = []
        
        # 根據當前頁碼和總頁數設置導航按鈕
        if page > 1:
            # 不是第一頁，顯示「上一頁」按鈕
            footer_contents.append(
                ButtonComponent(
                    style="secondary",
                    action=MessageAction(
                        label="⬅️ 上一頁",
                        text=f"土豆 什麼是{fraud_type} 第{page-1}頁"
                    ),
                    color="#95a5a6",
                    height="sm"
                )
            )
        
        if page < total_pages:
            # 不是最後一頁，顯示「下一頁」按鈕
            footer_contents.append(
                ButtonComponent(
                    style="primary",
                    action=MessageAction(
                        label="下一頁 ➡️",
                        text=f"土豆 什麼是{fraud_type} 第{page+1}頁"
                    ),
                    color="#3498DB",
                    height="sm"
                )
            )
        
        # 如果是最後一頁，添加「看其他分類」和「回到首頁」按鈕
        if page == total_pages:
            footer_contents.extend([
                ButtonComponent(
                    style="primary",
                    action=MessageAction(
                        label="👀 看其他分類",
                        text="土豆 詐騙類型"
                    ),
                    color="#3498DB",
                    height="sm",
                    margin="md"
                ),
                ButtonComponent(
                    style="secondary",
                    action=MessageAction(
                        label="🏠 回到首頁",
                        text="土豆"
                    ),
                    color="#95a5a6",
                    height="sm",
                    margin="md"
                )
            ])
        
        # 創建詐騙詳情Flex Message
        bubble = BubbleContainer(
            size="mega",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text=f"{fraud_type}",
                        weight="bold",
                        size="xl",
                        color="#ffffff"
                    ),
                    TextComponent(
                        text="以下是此類詐騙的詳細說明與防範方法",
                        size="sm",
                        color="#ffffff",
                        margin="sm",
                        wrap=True
                    )
                ],
                background_color=header_color,
                padding_all="lg"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=body_contents,
                padding_all="lg"
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=footer_contents,
                padding_all="lg"
            )
        )
        
        return FlexSendMessage(alt_text=f"{fraud_type}詳細說明 第{page}頁", contents=bubble)

    def create_fraud_types_flex_message(self, fraud_tactics: Dict, display_name: str = "朋友") -> FlexSendMessage:
        """創建詐騙類型列表Flex Message"""
        
        # 記錄所有獲取的詐騙類型
        logger.info(f"詐騙類型列表包含: {', '.join(fraud_tactics.keys())}")
        
        # 創建詐騙類型按鈕列表
        type_contents = []
        
        # 添加標題
        type_contents.append(
            TextComponent(
                text="⚠️ 點選詐騙類型查看詳細說明與防範措施",
                size="sm",
                color="#666666",
                margin="md",
                wrap=True
            )
        )
        
        # 統一按鈕顏色
        button_color = "#E8F4FD"  # 統一使用淺藍色
        
        # 為所有詐騙類型創建按鈕
        for fraud_type in fraud_tactics.keys():
            # 添加該詐騙類型的按鈕
            type_contents.append(
                ButtonComponent(
                    style="secondary",
                    height="sm",
                    action=MessageAction(
                        label=f"{fraud_type}",
                        text=f"土豆 什麼是{fraud_type}"
                    ),
                    color=button_color,
                    margin="md"
                )
            )
        
        # 添加分隔線
        type_contents.append(
            SeparatorComponent(
                margin="xxl"
            )
        )
        
        bubble = BubbleContainer(
            size="mega",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="📚 常見詐騙類型一覽",
                        weight="bold",
                        size="xl",
                        color="#ffffff"
                    ),
                    TextComponent(
                        text="這些詐騙手法最常見，請特別小心！",
                        size="sm",
                        color="#ffffff",
                        margin="sm",
                        wrap=True
                    )
                ],
                background_color="#3498DB",
                padding_all="lg"
            ),
            body=BoxComponent(
                layout="vertical",
                spacing="md",
                padding_all="lg",
                contents=type_contents
            )
            # 移除footer部分
        )
        
        return FlexSendMessage(alt_text="詐騙類型列表", contents=bubble)


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

def create_fraud_detail_flex_message(fraud_type: str, fraud_info: Dict, display_name: str = "朋友", page: int = 1) -> FlexSendMessage:
    """創建詐騙類型詳細信息的Flex Message
    
    Args:
        fraud_type: 詐騙類型名稱
        fraud_info: 詐騙類型信息
        display_name: 用戶顯示名稱
        page: 當前頁碼，默認為第1頁
    """
    return flex_message_service.create_fraud_detail_flex_message(fraud_type, fraud_info, display_name, page)

def create_fraud_types_flex_message(fraud_tactics: Dict, display_name: str = "朋友") -> FlexSendMessage:
    """創建詐騙類型列表Flex Message"""
    return flex_message_service.create_fraud_types_flex_message(fraud_tactics, display_name)


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