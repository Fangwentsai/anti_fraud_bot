import os
import json
from flask import Flask, request, abort, render_template, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage,
    QuickReply, QuickReplyButton, MessageAction, PostbackEvent, PostbackAction,
    BubbleContainer, BoxComponent, ButtonComponent, TextComponent,
    CarouselContainer, URIAction, SeparatorComponent
)
from dotenv import load_dotenv

# 將create_mention_message函數修改為使用文本@方式
def create_mention_message(text, display_name, user_id, quick_reply=None):
    """創建帶有文本@功能的消息，兼容舊版本SDK"""
    text_with_mention = f"@{display_name} {text}"
    return TextSendMessage(text=text_with_mention, quick_reply=quick_reply)

# 創建一個全局字典來跟踪用戶狀態
user_conversation_state = {}  # 格式: {user_id: {"last_time": timestamp, "waiting_for_analysis": True/False}} 