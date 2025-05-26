#!/usr/bin/env python3
"""
簡單的備用方案修復腳本
當 v3 API 失敗時直接使用舊版 API
"""

import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_simple_fallback(file_path):
    """
    簡單的備用方案修復
    當 v3 API 失敗時直接使用舊版 API
    """
    # 備份原始文件
    backup_path = file_path + '.simple_fallback.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到圖片處理的 try-except 區塊，簡化為直接使用舊版 API
    old_pattern = '''            # 回覆分析結果
            if flex_message:
                # 使用新版 API 回覆
                try:
                    if v3_messaging_api:
                        from linebot.v3.messaging import ReplyMessageRequest
                        from linebot.v3.messaging import FlexMessage as V3FlexMessage
                        
                        # 將 FlexSendMessage 轉換為 v3 格式
                        if hasattr(flex_message, 'contents') and hasattr(flex_message, 'alt_text'):
                            # 檢查 contents 是否為 BubbleContainer 或其他 Flex 容器
                            if hasattr(flex_message.contents, 'as_json_dict'):
                                # 如果是 LINE SDK 對象，轉換為字典
                                contents_dict = flex_message.contents.as_json_dict()
                            else:
                                # 如果已經是字典，直接使用
                                contents_dict = flex_message.contents
                            
                            v3_flex_message = V3FlexMessage(
                                alt_text=flex_message.alt_text,
                                contents=contents_dict
                            )
                        else:
                            # 如果已經是 v3 格式，直接使用
                            v3_flex_message = flex_message
                        
                        v3_messaging_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=reply_token,
                                messages=[v3_flex_message]
                           )
                        )
                        logger.info(f"使用v3 API回覆圖片分析成功: {user_id}")
                    else:
                        # 舊版 API 作為備用
                        line_bot_api.reply_message(reply_token, flex_message)
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆圖片分析時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        # 如果是無效的回覆令牌，嘗試使用push_message作為備用
                        try:
                            if v3_messaging_api:
                                from linebot.v3.messaging import PushMessageRequest
                                from linebot.v3.messaging import FlexMessage as V3FlexMessage
                                
                                # 將 FlexSendMessage 轉換為 v3 格式
                                if hasattr(flex_message, 'contents') and hasattr(flex_message, 'alt_text'):
                                    # 檢查 contents 是否為 BubbleContainer 或其他 Flex 容器
                                    if hasattr(flex_message.contents, 'as_json_dict'):
                                        # 如果是 LINE SDK 對象，轉換為字典
                                        contents_dict = flex_message.contents.as_json_dict()
                                    else:
                                        # 如果已經是字典，直接使用
                                        contents_dict = flex_message.contents
                                    
                                    v3_flex_message = V3FlexMessage(
                                        alt_text=flex_message.alt_text,
                                        contents=contents_dict
                                    )
                                else:
                                    # 如果已經是 v3 格式，直接使用
                                    v3_flex_message = flex_message
                                
                                v3_messaging_api.push_message(
                                    PushMessageRequest(
                                        to=user_id,
                                        messages=[v3_flex_message]
                                   )
                                )
                            else:
                                line_bot_api.push_message(user_id, flex_message)
                            logger.info(f"圖片分析回覆令牌無效，改用push_message成功: {user_id}")
                        except Exception as push_error:
                            logger.error(f"圖片分析使用push_message也失敗: {push_error}")'''
    
    new_pattern = '''            # 回覆分析結果
            if flex_message:
                # 直接使用舊版 API，避免 v3 轉換問題
                try:
                    line_bot_api.reply_message(reply_token, flex_message)
                    logger.info(f"使用舊版API回覆圖片分析成功: {user_id}")
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆圖片分析時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        # 如果是無效的回覆令牌，嘗試使用push_message作為備用
                        try:
                            line_bot_api.push_message(user_id, flex_message)
                            logger.info(f"圖片分析回覆令牌無效，改用push_message成功: {user_id}")
                        except Exception as push_error:
                            logger.error(f"圖片分析使用push_message也失敗: {push_error}")'''
    
    # 替換內容
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        logger.info("已替換圖片分析回覆邏輯為舊版API")
    else:
        logger.warning("未找到預期的圖片分析回覆邏輯，嘗試部分替換")
        # 嘗試部分替換
        content = content.replace(
            "# 使用新版 API 回覆",
            "# 直接使用舊版 API，避免 v3 轉換問題"
        )
        content = content.replace(
            "v3_messaging_api.reply_message(",
            "# v3_messaging_api.reply_message("
        )
        content = content.replace(
            "logger.info(f\"使用v3 API回覆圖片分析成功: {user_id}\")",
            "# logger.info(f\"使用v3 API回覆圖片分析成功: {user_id}\")"
        )
    
    # 同樣處理錯誤訊息回覆
    old_error_pattern = '''                # 使用新版 API 回覆
                try:
                    if v3_messaging_api:
                        from linebot.v3.messaging import TextMessage as V3TextMessage
                        from linebot.v3.messaging import ReplyMessageRequest
                        v3_messaging_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=reply_token,
                                messages=[V3TextMessage(text=error_message)]
                           )
                        )
                    else:
                        # 舊版 API 作為備用
                        line_bot_api.reply_message(
                            reply_token,
                            TextSendMessage(text=error_message)
                        )
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆圖片錯誤訊息時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        # 如果是無效的回覆令牌，嘗試使用push_message作為備用
                        try:
                            if v3_messaging_api:
                                from linebot.v3.messaging import TextMessage as V3TextMessage
                                from linebot.v3.messaging import PushMessageRequest
                                
                                v3_messaging_api.push_message(
                                    PushMessageRequest(
                                        to=user_id,
                                        messages=[V3TextMessage(text=error_message)]
                                   )
                                )
                            else:
                                line_bot_api.push_message(user_id, TextSendMessage(text=error_message))
                            logger.info(f"圖片錯誤訊息回覆令牌無效，改用push_message成功: {user_id}")
                        except Exception as push_error:
                            logger.error(f"圖片錯誤訊息使用push_message也失敗: {push_error}")'''
    
    new_error_pattern = '''                # 直接使用舊版 API
                try:
                    line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text=error_message)
                    )
                except LineBotApiError as e:
                    logger.error(f"使用LINE API回覆圖片錯誤訊息時發生錯誤: {e}")
                    if "Invalid reply token" in str(e):
                        # 如果是無效的回覆令牌，嘗試使用push_message作為備用
                        try:
                            line_bot_api.push_message(user_id, TextSendMessage(text=error_message))
                            logger.info(f"圖片錯誤訊息回覆令牌無效，改用push_message成功: {user_id}")
                        except Exception as push_error:
                            logger.error(f"圖片錯誤訊息使用push_message也失敗: {push_error}")'''
    
    if old_error_pattern in content:
        content = content.replace(old_error_pattern, new_error_pattern)
        logger.info("已替換圖片錯誤訊息回覆邏輯為舊版API")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("簡單備用方案修復完成")
    return True

def main():
    """主函數"""
    # 檢查參數
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = 'anti_fraud_clean_app.py'  # 默認檔案名
    
    # 檢查文件是否存在
    if not os.path.isfile(file_path):
        logger.error(f"文件不存在: {file_path}")
        return 1
    
    # 修復文件
    success = fix_simple_fallback(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.simple_fallback.bak")
        logger.info("現在圖片分析將直接使用舊版 LINE API，避免 v3 轉換問題")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 