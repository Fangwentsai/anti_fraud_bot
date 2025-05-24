#!/usr/bin/env python3
"""
修復 Flex Message 空文字問題
"""

import json
import logging
from typing import Dict, Optional
from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent,
    SeparatorComponent, ButtonComponent, URIAction, PostbackAction
)

def safe_text_component(text: str, **kwargs) -> TextComponent:
    """創建安全的文字組件，確保文字不為空"""
    # 確保文字不為空或僅包含空白字符
    safe_text = str(text).strip() if text is not None else ""
    if not safe_text:
        safe_text = "無內容"  # 預設文字
    
    return TextComponent(text=safe_text, **kwargs)

def create_safe_analysis_flex_message(analysis_data: Dict, display_name: str, 
                                    message_to_analyze: str, user_id: Optional[str] = None) -> FlexSendMessage:
    """創建安全的詐騙分析結果 Flex Message，確保沒有空文字"""
    
    # 安全地獲取數據，並提供預設值
    risk_level = str(analysis_data.get("risk_level", "不確定")).strip() or "不確定"
    fraud_type = str(analysis_data.get("fraud_type", "未知")).strip() or "未知"
    explanation = str(analysis_data.get("explanation", "分析結果不完整")).strip() or "分析結果不完整"
    suggestions = str(analysis_data.get("suggestions", "請保持警覺")).strip() or "請保持警覺"
    display_name = str(display_name).strip() or "用戶"
    
    # 確保用戶ID有值
    safe_user_id = user_id if user_id else "unknown"
    
    # 根據風險等級選擇顏色
    colors = {
        "primary": "#1DB446",
        "secondary": "#464F69", 
        "danger": "#F44336",
        "warning": "#FFA726",
        "success": "#4CAF50"
    }
    
    if risk_level in ["高", "高風險"]:
        risk_color = colors["danger"]
        risk_emoji = "⚠️"
    elif risk_level in ["中", "中風險"]:
        risk_color = colors["warning"]
        risk_emoji = "⚠️"
    elif risk_level in ["低", "低風險"]:
        risk_color = colors["success"]
        risk_emoji = "✅"
    else:
        risk_color = colors["primary"]
        risk_emoji = "❓"
    
    # 構建 Flex Message，使用安全的文字組件
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
                    f"@{display_name}",
                    weight='bold',
                    size='lg',
                    color=colors["primary"]
                ),
                SeparatorComponent(margin='md'),
                safe_text_component(
                    f"詐騙類型：{fraud_type}",
                    size='md',
                    weight='bold',
                    margin='md'
                ),
                safe_text_component(
                    explanation,
                    size='sm',
                    color=colors["secondary"],
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
                    suggestions,
                    size='sm',
                    color=colors["secondary"],
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
                        data=f'action=potato_game&user_id={safe_user_id}'
                    )
                )
            ]
        )
    )
    
    return FlexSendMessage(alt_text=f"詐騙風險分析：{risk_level}", contents=bubble)

def test_flex_message_safety():
    """測試Flex Message的安全性"""
    print("🧪 測試 Flex Message 安全性...")
    
    # 測試正常數據
    normal_data = {
        "risk_level": "高風險",
        "fraud_type": "假網購詐騙",
        "explanation": "這是一個可疑的網購網站",
        "suggestions": "請勿購買，立即離開網站"
    }
    
    try:
        flex_msg = create_safe_analysis_flex_message(normal_data, "測試用戶", "測試訊息", "test123")
        flex_dict = flex_msg.as_json_dict()
        print("✅ 正常數據測試通過")
        
        # 檢查是否有空文字
        def check_empty_text(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "text" and (not value or str(value).strip() == ""):
                        print(f"❌ 發現空文字在 {path}.{key}")
                        return False
                    if not check_empty_text(value, f"{path}.{key}"):
                        return False
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if not check_empty_text(item, f"{path}[{i}]"):
                        return False
            return True
        
        if check_empty_text(flex_dict):
            print("✅ 沒有發現空文字")
        
    except Exception as e:
        print(f"❌ 正常數據測試失敗: {e}")
        return False
    
    # 測試異常數據（空值、None等）
    abnormal_data = {
        "risk_level": "",
        "fraud_type": None,
        "explanation": "   ",
        "suggestions": ""
    }
    
    try:
        flex_msg = create_safe_analysis_flex_message(abnormal_data, "", "測試訊息", None)
        flex_dict = flex_msg.as_json_dict()
        print("✅ 異常數據測試通過")
        
        # 檢查JSON大小
        json_str = json.dumps(flex_dict, ensure_ascii=False)
        json_size = len(json_str.encode('utf-8'))
        print(f"   JSON大小: {json_size} bytes")
        
        if json_size > 50000:
            print("⚠️ JSON可能過大")
        else:
            print("✅ JSON大小正常")
            
    except Exception as e:
        print(f"❌ 異常數據測試失敗: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if test_flex_message_safety():
        print("\n🎉 所有測試通過！Flex Message 安全性修復完成。")
    else:
        print("\n❌ 測試失敗") 