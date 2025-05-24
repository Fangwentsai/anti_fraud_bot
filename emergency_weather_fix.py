#!/usr/bin/env python3
"""
天氣查詢功能緊急修復腳本
直接替換有問題的處理函數
"""

import os
import logging
import sys

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 完整的修復函數
WEATHER_HANDLER_FUNCTION = '''
        # 處理天氣查詢
        if is_weather_related(cleaned_message):
            logger.info(f"檢測到天氣查詢: {cleaned_message}")
            
            try:
                # 先嘗試使用結構化數據創建Flex Message
                weather_data = handle_weather_query_data(cleaned_message)
                
                if weather_data.get("success"):
                    # 創建天氣Flex Message
                    weather_flex = create_weather_flex_message(weather_data.get("data", {}), display_name)
                    line_bot_api.reply_message(reply_token, weather_flex)
                else:
                    # 如果結構化數據獲取失敗，退回到文字格式
                    weather_text = handle_weather_query(cleaned_message, display_name)
                    if weather_text:
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=weather_text))
                    else:
                        # 發送錯誤訊息
                        error_text = f"抱歉，無法處理您的天氣查詢。\\n\\n💡 您可以試著這樣問：\\n• 今天天氣如何\\n• 台北天氣\\n• 明天會下雨嗎"
                        line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
            except Exception as e:
                logger.error(f"處理天氣查詢時發生錯誤: {e}")
                # 使用文字格式作為備用方案
                weather_text = handle_weather_query(cleaned_message, display_name)
                if weather_text:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=weather_text))
                else:
                    # 發送錯誤訊息
                    error_text = f"抱歉，無法處理您的天氣查詢。\\n\\n💡 您可以試著這樣問：\\n• 今天天氣如何\\n• 台北天氣\\n• 明天會下雨嗎"
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=error_text))
            
            return
'''

def apply_emergency_fix():
    """應用緊急修復"""
    try:
        # 設定文件路徑
        target_file = "anti_fraud_clean_app.py"
        backup_file = "anti_fraud_clean_app_emergency_backup.py"
        
        # 檢查文件是否存在
        if not os.path.exists(target_file):
            logger.error(f"目標文件不存在: {target_file}")
            return False
        
        # 創建備份
        import shutil
        shutil.copy2(target_file, backup_file)
        logger.info(f"已創建備份文件: {backup_file}")
        
        # 讀取文件內容
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尋找需要替換的部分
        # 使用更寬鬆的匹配模式，確保能找到天氣處理部分
        weather_section_pattern = r'# 處理天氣查詢\s+if is_weather_related\(.*?\n\s+return\n'
        import re
        
        # 搜索匹配模式
        match = re.search(weather_section_pattern, content, re.DOTALL)
        
        if match:
            # 找到匹配部分，進行替換
            start, end = match.span()
            line_count = content[:start].count('\n') + 1
            logger.info(f"找到天氣處理部分: 第 {line_count} 行開始")
            
            # 構建新內容
            new_content = content[:start] + WEATHER_HANDLER_FUNCTION + content[end:]
            
            # 寫入文件
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info("成功替換天氣處理函數")
            return True
        else:
            # 嘗試更精確的定位，找到天氣相關部分並手動插入
            weather_related_check = 'if is_weather_related(cleaned_message):'
            pos = content.find(weather_related_check)
            
            if pos >= 0:
                line_count = content[:pos].count('\n') + 1
                logger.info(f"找到天氣相關檢查: 第 {line_count} 行")
                
                # 找到匹配的行
                lines = content.split('\n')
                target_line = -1
                
                for i, line in enumerate(lines):
                    if weather_related_check in line:
                        target_line = i
                        break
                
                if target_line >= 0:
                    # 尋找整個天氣處理塊的結束位置
                    end_line = target_line
                    indent = len(lines[target_line]) - len(lines[target_line].lstrip())
                    
                    for i in range(target_line + 1, len(lines)):
                        line_indent = len(lines[i]) - len(lines[i].lstrip()) if lines[i].strip() else indent
                        if line_indent <= indent and lines[i].strip():
                            end_line = i - 1
                            break
                    
                    # 構建新內容
                    new_lines = lines[:target_line] + WEATHER_HANDLER_FUNCTION.split('\n') + lines[end_line+1:]
                    new_content = '\n'.join(new_lines)
                    
                    # 寫入文件
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    logger.info(f"成功替換天氣處理塊 (從第 {target_line+1} 行到第 {end_line+1} 行)")
                    return True
            
            logger.error("無法找到天氣處理部分")
            return False
    
    except Exception as e:
        logger.error(f"修復過程中發生錯誤: {e}")
        return False

def main():
    """主函數"""
    logger.info("開始應用天氣查詢緊急修復...")
    
    if apply_emergency_fix():
        logger.info("緊急修復成功應用！請重新啟動服務以使更改生效")
        logger.info("提示: 使用 'touch tmp/restart.txt' 或重新啟動 Web 服務")
    else:
        logger.error("緊急修復失敗！請手動檢查並修復問題")
        sys.exit(1)

if __name__ == "__main__":
    main() 