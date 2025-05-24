#!/usr/bin/env python3
"""
縣市選擇器模組
提供縣市選擇的 Flex Message
"""

import logging
from typing import Dict, List, Optional

from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, 
    ButtonComponent, MessageAction, SeparatorComponent
)

logger = logging.getLogger(__name__)

def create_city_selector_flex_message(user_name: str = "朋友") -> FlexSendMessage:
    """
    創建縣市選擇器 Flex Message
    
    Args:
        user_name: 用戶顯示名稱
        
    Returns:
        FlexSendMessage: 縣市選擇器 Flex Message
    """
    # 縣市分組
    city_groups = {
        "北部": ["台北", "新北", "基隆", "桃園", "新竹"],
        "中部": ["苗栗", "台中", "彰化", "南投", "雲林"],
        "南部": ["嘉義", "台南", "高雄", "屏東"],
        "東部": ["宜蘭", "花蓮", "台東"],
        "離島": ["澎湖", "金門", "連江"]
    }
    
    # 創建按鈕顏色
    region_colors = {
        "北部": "#1976D2",  # 深藍色
        "中部": "#388E3C",  # 綠色
        "南部": "#F57C00",  # 橙色
        "東部": "#7B1FA2",  # 紫色
        "離島": "#00796B"   # 青色
    }
    
    # 創建標題
    body_contents = [
        TextComponent(
            text=f"@{user_name} 想查詢哪個縣市的天氣呢？",
            weight="bold",
            size="md",
            color="#555555",
            wrap=True
        ),
        SeparatorComponent(margin="md")
    ]
    
    # 為每個區域創建按鈕組
    for region, cities in city_groups.items():
        # 添加區域標題
        body_contents.append(
            TextComponent(
                text=f"📍 {region}",
                weight="bold",
                size="md",
                margin="lg",
                color=region_colors[region]
            )
        )
        
        # 為每個城市創建按鈕
        city_buttons = []
        
        # 創建每行的按鈕容器
        for i in range(0, len(cities), 3):  # 每行最多3個按鈕
            row_cities = cities[i:i+3]
            row_buttons = []
            
            for city in row_cities:
                row_buttons.append(
                    ButtonComponent(
                        style="secondary",
                        height="sm",
                        action=MessageAction(
                            label=f"{city}",
                            text=f"土豆 {city}天氣"
                        ),
                        margin="sm",
                        color="#f5f5f5"  # 淺灰色背景
                    )
                )
            
            # 將這一行的按鈕添加到按鈕容器
            city_buttons.append(
                BoxComponent(
                    layout="horizontal",
                    margin="md",
                    spacing="sm",
                    contents=row_buttons
                )
            )
        
        # 將所有按鈕容器添加到主內容
        body_contents.extend(city_buttons)
    
    # 創建Flex Message
    bubble = BubbleContainer(
        direction="ltr",
        header=BoxComponent(
            layout="vertical",
            background_color="#2196F3",  # 藍色
            padding_all="15px",
            contents=[
                TextComponent(
                    text="🌤️ 天氣查詢",
                    weight="bold",
                    color="#ffffff",
                    size="xl"
                )
            ]
        ),
        body=BoxComponent(
            layout="vertical",
            padding_all="15px",
            contents=body_contents
        ),
        footer=BoxComponent(
            layout="vertical",
            padding_all="15px",
            contents=[
                ButtonComponent(
                    style="primary",
                    color="#2196F3",
                    action=MessageAction(
                        label="台北天氣",
                        text="土豆 台北天氣"
                    )
                ),
                TextComponent(
                    text="🔍 點選任一縣市或直接輸入「OO天氣」",
                    size="xs",
                    color="#aaaaaa",
                    margin="md",
                    align="center"
                )
            ]
        )
    )
    
    return FlexSendMessage(alt_text="請選擇縣市", contents=bubble)

# 提供便捷的函數接口
def get_city_selector(user_name: str = "朋友") -> FlexSendMessage:
    """獲取縣市選擇器 Flex Message"""
    return create_city_selector_flex_message(user_name)

if __name__ == "__main__":
    # 測試函數
    flex_message = create_city_selector_flex_message("測試用戶")
    print("✅ 成功創建縣市選擇器 Flex Message")
    print(f"alt_text: {flex_message.alt_text}") 