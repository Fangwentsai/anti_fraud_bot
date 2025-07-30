#!/usr/bin/env python3
"""
圖片分析流程修復腳本
修復 "土豆 請幫我分析圖片：" 的處理邏輯
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_image_analysis_flow(file_path):
    """
    修復圖片分析流程
    """
    # 備份原始文件
    backup_path = file_path + '.image_analysis_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復1: 在檢測到圖片分析請求時，直接回覆提示訊息而不進入一般聊天模式
    # 找到檢測分析請求的邏輯
    pattern = r'(logger\.info\(f"檢測到分析請求但沒有提供具體內容: {cleaned_message}"\)\s+)(.*?)(logger\.info\(f"進入一般聊天模式: {cleaned_message}"\))'
    
    replacement = r'''\1# 檢查是否是圖片分析請求
        if "分析圖片" in cleaned_message or "檢查圖片" in cleaned_message:
            # 直接回覆圖片分析提示訊息，不進入一般聊天模式
            image_analysis_prompt = f"📷 {display_name}，請上傳您想要分析的圖片！\\n\\n" \\
                                  f"我可以幫您分析：\\n" \\
                                  f"🔍 可疑網站截圖\\n" \\
                                  f"💬 詐騙對話截圖\\n" \\
                                  f"📱 可疑簡訊截圖\\n" \\
                                  f"📧 釣魚郵件截圖\\n" \\
                                  f"💰 投資廣告截圖\\n" \\
                                  f"🎯 其他可疑內容截圖\\n\\n" \\
                                  f"請直接上傳圖片，我會立即為您分析！"
            
            try:
                if v3_messaging_api:
                    from linebot.v3.messaging import TextMessage as V3TextMessage
                    from linebot.v3.messaging import ReplyMessageRequest
                    v3_messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[V3TextMessage(text=image_analysis_prompt)]
                       )
                    )
                    logger.info(f"已回覆圖片分析提示訊息: {user_id}")
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=image_analysis_prompt))
                    logger.info(f"已回覆圖片分析提示訊息 (舊版API): {user_id}")
            except LineBotApiError as e:
                logger.error(f"回覆圖片分析提示訊息時發生錯誤: {e}")
                if "Invalid reply token" in str(e):
                    try:
                        if v3_messaging_api:
                            from linebot.v3.messaging import TextMessage as V3TextMessage
                            from linebot.v3.messaging import PushMessageRequest
                            v3_messaging_api.push_message(
                                PushMessageRequest(
                                    to=user_id,
                                    messages=[V3TextMessage(text=image_analysis_prompt)]
                               )
                            )
                        else:
                            line_bot_api.push_message(user_id, TextSendMessage(text=image_analysis_prompt))
                        logger.info(f"圖片分析提示訊息使用push_message成功: {user_id}")
                    except Exception as push_error:
                        logger.error(f"圖片分析提示訊息使用push_message也失敗: {push_error}")
            return
        
        \3'''
    
    # 執行替換
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    logger.info("已修復圖片分析請求的處理邏輯")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("圖片分析流程修復完成")
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
    success = fix_image_analysis_flow(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.image_analysis_fix.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 