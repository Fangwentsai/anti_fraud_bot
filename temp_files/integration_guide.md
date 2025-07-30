# 圖片分析功能整合指南

本文檔提供了將圖片分析功能整合到現有的`anti_fraud_clean_app.py`的步驟指南。

## 功能概述

新添加的圖片分析功能可以：
- 分析用戶上傳的圖片是否包含詐騙內容
- 檢測圖片中的QR碼並評估風險
- 從圖片中提取文字內容
- 根據內容自動選擇最適合的分析類型
- 生成詳細的分析報告

## 檔案結構

新增了兩個主要文件：
- `image_analysis_service.py`: 核心分析服務，處理圖片內容分析
- `image_handler.py`: 與LINE Bot整合的處理器，負責接收和回應圖片訊息

## 整合步驟

### 1. 導入新模組

在`anti_fraud_clean_app.py`的開頭添加以下導入語句：

```python
# 添加圖片分析功能
import image_handler
from image_analysis_service import ANALYSIS_TYPES
```

### 2. 初始化圖片處理器

在初始化LINE Bot API後，添加以下代碼初始化圖片處理器：

```python
# 在創建LINE Bot API後
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 初始化圖片處理器
image_handler.init_image_handler(line_bot_api)
```

### 3. 添加圖片處理路由

在`@handler.add`部分添加圖片訊息處理器：

```python
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    """處理圖片訊息"""
    try:
        # 獲取用戶資料
        user_id = event.source.user_id
        profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
        
        # 檢查上下文（用戶可能提供了分析需求）
        context_message = ""
        analysis_type = "GENERAL"
        
        # 檢查是否有上下文信息
        user_state = get_user_state(user_id)
        if user_state and "image_analysis_context" in user_state:
            context_message = user_state.get("image_analysis_context", "")
            analysis_type = user_state.get("image_analysis_type", "GENERAL")
            # 清除上下文
            user_state.pop("image_analysis_context", None)
            user_state.pop("image_analysis_type", None)
            update_user_state(user_id, user_state)
        
        # 處理圖片
        flex_message, raw_result = image_handler.handle_image_message(
            event.message.id, user_id, display_name, context_message, analysis_type
        )
        
        # 回覆分析結果
        if flex_message:
            line_bot_api.reply_message(event.reply_token, flex_message)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，無法分析此圖片，請稍後再試。")
            )
            
    except LineBotApiError as e:
        logger.error(f"處理圖片訊息時發生LINE API錯誤: {e}")
    except Exception as e:
        logger.exception(f"處理圖片訊息時發生錯誤: {e}")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="處理圖片時發生錯誤，請稍後再試。")
            )
        except:
            pass
```

### 4. 添加圖片分析命令處理

在文字訊息處理部分添加以下代碼，用於處理用戶請求分析圖片的命令：

```python
# 在處理土豆命令的地方添加
elif "分析圖片" in message_text or "檢查圖片" in message_text:
    # 設置用戶狀態，等待上傳圖片
    user_state = get_user_state(user_id) or {}
    
    # 檢查是否有上下文信息
    context_message = ""
    analysis_type = "GENERAL"
    
    # 嘗試提取上下文信息
    if "：" in message_text:
        context_part = message_text.split("：", 1)[1].strip()
        if context_part:
            context_message = context_part
    
    # 嘗試判斷分析類型
    if "釣魚" in message_text or "網站" in message_text:
        analysis_type = "PHISHING"
    elif "文件" in message_text or "合約" in message_text:
        analysis_type = "DOCUMENT"
    elif "社交" in message_text or "交友" in message_text:
        analysis_type = "SOCIAL_MEDIA"
    
    # 更新用戶狀態
    user_state["image_analysis_context"] = context_message
    user_state["image_analysis_type"] = analysis_type
    update_user_state(user_id, user_state)
    
    # 提示用戶上傳圖片
    reply_text = "請上傳您想要分析的圖片，我會檢查它是否含有詐騙內容。"
    if context_message:
        reply_text += f"\n\n我會根據您提供的上下文「{context_message}」進行分析。"
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )
    return
```

### 5. 添加圖片URL分析功能（可選）

如果您想支持直接分析圖片URL，可以添加以下代碼：

```python
elif message_text.startswith("分析圖片網址：") or message_text.startswith("分析圖片url："):
    # 提取圖片URL
    image_url = ""
    if "：" in message_text:
        image_url = message_text.split("：", 1)[1].strip()
    
    if not image_url:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請提供有效的圖片URL，格式：土豆 分析圖片網址：https://example.com/image.jpg")
        )
        return
    
    # 處理圖片URL
    flex_message, raw_result = image_handler.handle_image_url(
        image_url, user_id, display_name
    )
    
    # 回覆分析結果
    if flex_message:
        line_bot_api.reply_message(event.reply_token, flex_message)
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="抱歉，無法分析此圖片URL，請確保URL有效並指向一個圖片文件。")
        )
    return
```

### 6. 更新主選單（可選）

您可以在主選單中添加圖片分析功能：

```python
# 在創建主選單的地方添加圖片分析按鈕
if "reply_text" in locals() and "我是土豆" in reply_text:
    # 底部按鈕
    buttons = [
        # 現有按鈕...
        
        # 添加圖片分析按鈕
        QuickReplyButton(
            action=MessageAction(label="📷 圖片詐騙分析", text="土豆 請幫我分析圖片")
        ),
        
        # 其他按鈕...
    ]
    
    # 添加QuickReply
    reply_message = TextSendMessage(
        text=reply_text,
        quick_reply=QuickReply(items=buttons)
    )
```

### 7. 添加環境變量

確保在`.env`文件中添加OpenAI API金鑰：

```
OPENAI_API_KEY=your_openai_api_key_here
```

## 相關依賴

確保安裝以下依賴：
- OpenAI Python SDK: `pip install openai`
- Pillow (PIL): `pip install pillow`
- 現有的LINE Bot依賴項

## 測試功能

整合完成後，可以通過以下方式測試功能：

1. 發送命令：`土豆 請幫我分析圖片`
2. 上傳一張圖片
3. 查看分析結果

也可以直接上傳圖片，系統會自動識別並進行分析。

## 注意事項

1. 圖片分析功能使用OpenAI的GPT-4 Vision API，需要相應的API金鑰和額度
2. 大型圖片會自動調整大小以符合API限制
3. 分析過程可能需要幾秒鐘時間，請耐心等待
4. 部分複雜圖片可能無法準確分析 