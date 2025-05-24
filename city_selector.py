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
        "北部": "#2196F3",  # 藍色
        "中部": "#4CAF50",  # 綠色
        "南部": "#FF9800",  # 橙色
        "東部": "#9C27B0",  # 紫色
        "離島": "#009688"   # 青色
    }
    
    # 創建標題和說明
    body_contents = [
        TextComponent(
            text="想查詢哪個縣市的天氣？",
            weight="bold",
            size="md",
            color="#555555",
            align="center"
        ),
        SeparatorComponent(margin="md")
    ]
    
    # 為每個區域創建按鈕組
    for region, cities in city_groups.items():
        # 添加區域標題
        body_contents.append(
            TextComponent(
                text=f"{region}",
                weight="bold",
                size="sm",
                margin="md",
                color=region_colors[region]
            )
        )
        
        # 為每個城市創建按鈕
        city_buttons = []
        
        # 創建每行的按鈕容器 (每行4個按鈕)
        for i in range(0, len(cities), 4):
            row_cities = cities[i:i+4]
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
                        margin="xs",
                        color="#f5f5f5",
                        flex=1
                    )
                )
            
            # 將這一行的按鈕添加到按鈕容器
            city_buttons.append(
                BoxComponent(
                    layout="horizontal",
                    margin="xs",
                    spacing="xs",
                    contents=row_buttons
                )
            )
        
        # 將所有按鈕容器添加到主內容
        body_contents.extend(city_buttons)
    
    # 創建Flex Message
    bubble = BubbleContainer(
        size="mega",  # 使用更合適的尺寸
        header=BoxComponent(
            layout="vertical",
            background_color="#2196F3",
            paddingAll="10px",  # 縮小padding
            height="50px",  # 設定較小的高度
            contents=[
                TextComponent(
                    text="天氣查詢",
                    weight="bold",
                    color="#ffffff",
                    size="md",
                    align="center"
                )
            ]
        ),
        body=BoxComponent(
            layout="vertical",
            paddingAll="10px",  # 縮小padding
            contents=body_contents
        ),
        footer=BoxComponent(
            layout="vertical",
            paddingAll="10px",  # 縮小padding
            height="40px",  # 設定較小的高度
            contents=[
                TextComponent(
                    text="點選縣市或直接輸入「OO天氣」",
                    size="xs",
                    color="#aaaaaa",
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