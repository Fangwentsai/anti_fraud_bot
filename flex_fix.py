#!/usr/bin/env python3
"""
Flex Message Service 修復腳本
修復 flex_message_service.py 中的縮排和結構問題
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_flex_message_service(file_path):
    """
    修復 flex_message_service.py 中的問題
    """
    # 備份原始文件
    backup_path = file_path + '.flex_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復1: 移除 create_weather_flex_message 中的詐騙相關邏輯
    # 找到 create_weather_flex_message 函數的開始和結束
    weather_func_start = content.find('def create_weather_flex_message(self, weather_data: Dict, user_name: str = "朋友") -> FlexSendMessage:')
    if weather_func_start != -1:
        # 找到下一個函數的開始
        next_func_start = content.find('def _get_risk_color(self, risk_level: str) -> str:', weather_func_start)
        if next_func_start != -1:
            # 提取天氣函數的內容
            weather_func_content = content[weather_func_start:next_func_start]
            
            # 創建正確的天氣函數內容
            correct_weather_func = '''def create_weather_flex_message(self, weather_data: Dict, user_name: str = "朋友") -> FlexSendMessage:
        """創建天氣預報的 Flex Message"""
        
        city = weather_data.get("city", "未知城市")
        forecast = weather_data.get("forecast", [])
        source = weather_data.get("source", "中央氣象署")
        
        if not forecast:
            # 錯誤情況的簡單 Flex Message
            bubble = BubbleContainer(
                size="kilo",
                direction='ltr',
                body=BoxComponent(
                    layout='vertical',
                    contents=[
                        TextComponent(
                            text=f"❌ 無法取得{city}的天氣資訊",
                            wrap=True,
                            weight="bold",
                            color="#DD2C00"
                        )
                    ]
                )
            )
            return FlexSendMessage(alt_text="天氣資訊錯誤", contents=bubble)
        
        # 只取第一天的資料，簡化顯示
        day_data = forecast[0] if forecast else {}
        date = day_data.get("date", "")
        weekday = day_data.get("weekday", "")
        weather = day_data.get("weather", "")
        temp = day_data.get("temperature", {})
        rain_prob = day_data.get("rain_probability", "")
        
        weather_emoji = self._get_weather_emoji(weather)
        
        # 創建更簡潔的天氣預報內容
        body_contents = [
            BoxComponent(
                layout="horizontal",
                margin="md",
                contents=[
                    TextComponent(
                        text=weather_emoji,
                        size="3xl",
                        align="center",
                        gravity="center",
                        flex=1
                    ),
                    BoxComponent(
                        layout="vertical",
                        flex=2,
                        spacing="sm",
                        contents=[
                            TextComponent(
                                text=f"{temp.get('low', '')}°C - {temp.get('high', '')}°C",
                                size="xl",
                                weight="bold",
                                color="#555555"
                            ),
                            TextComponent(
                                text=weather,
                                size="md",
                                color="#888888"
                            ),
                            TextComponent(
                                text=f"降雨機率：{rain_prob}",
                                size="sm",
                                color="#aaaaaa"
                            )
                        ]
                    )
                ]
            ),
            SeparatorComponent(margin="lg"),
            BoxComponent(
                layout="horizontal",
                margin="md",
                contents=[
                    TextComponent(
                        text=f"{date} {weekday}",
                        size="xs",
                        color="#aaaaaa",
                        flex=1
                    ),
                    TextComponent(
                        text=f"資料來源：{source}",
                        size="xs",
                        color="#aaaaaa",
                        align="end",
                        flex=1
                    )
                ]
            )
        ]
        
        bubble = BubbleContainer(
            size="kilo",  # 使用較小的尺寸
            direction='ltr',
            header=BoxComponent(
                layout='vertical',
                background_color="#1E88E5",
                height="65px",  # 降低高度
                paddingAll="15px",
                contents=[
                    TextComponent(
                        text=f"{city}天氣",
                        weight='bold',
                        color='#ffffff',
                        size='lg',
                        align="center"
                    )
                ]
            ),
            body=BoxComponent(
                layout='vertical',
                paddingAll="15px",
                contents=body_contents
            ),
            footer=BoxComponent(
                layout='vertical',
                height="40px",  # 降低高度
                paddingAll="10px",
                contents=[
                    TextComponent(
                        text="點此查看更多天氣資訊",
                        size="xs",
                        align="center",
                        color="#1E88E5",
                        action=URIAction(
                            uri='https://www.cwb.gov.tw/'
                        )
                    )
                ]
            )
        )
        
        return FlexSendMessage(alt_text=f"{city}天氣預報", contents=bubble)

    '''
            
            # 替換天氣函數
            content = content[:weather_func_start] + correct_weather_func + content[next_func_start:]
            logger.info("已修復 create_weather_flex_message 函數")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("Flex Message Service 修復完成")
    return True

def main():
    """主函數"""
    # 檢查參數
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = 'flex_message_service.py'  # 默認檔案名
    
    # 檢查文件是否存在
    if not os.path.isfile(file_path):
        logger.error(f"文件不存在: {file_path}")
        return 1
    
    # 修復文件
    success = fix_flex_message_service(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.flex_fix.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 