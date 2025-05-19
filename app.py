import sys
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
import datetime
import logging

# 添加anti-fraud-clean目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
anti_fraud_clean_dir = os.path.join(current_dir, "anti-fraud-clean")
sys.path.insert(0, anti_fraud_clean_dir)

# 指定 .env 文件的路徑
dotenv_path = os.path.join(current_dir, 'linebot-anti-fraud', '.env')
load_dotenv(dotenv_path=dotenv_path)

# 创建Flask应用
app = Flask(__name__, 
            template_folder=os.path.join(anti_fraud_clean_dir, "templates"),
            static_folder=os.path.join(anti_fraud_clean_dir, "static"))

# Line API 設定
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', ''))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET', ''))

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入子目录中的firebase_manager和其他所需模块
from firebase_manager import FirebaseManager
firebase_manager = FirebaseManager()

# 加载诈骗类型数据
fraud_tactics_path = os.path.join(anti_fraud_clean_dir, "fraud_tactics.json")
with open(fraud_tactics_path, 'r', encoding='utf-8') as f:
    fraud_tactics_data = json.load(f)

# 用戶遊戲狀態和聊天記錄
user_game_state = {}
user_last_chat_time = {}
first_time_chatters = set()

# 定義關鍵詞
function_inquiry_keywords = ["功能", "幫助", "會什麼", "能做什麼", "使用說明", "你是誰"]
follow_up_patterns = ["被騙", "詐騙", "可疑", "不確定", "幫我看看", "這是詐騙嗎", "這是真的嗎"]
potato_game_trigger_keywords = ["選哪顆土豆", "玩遊戲", "土豆遊戲", "選土豆", "選土豆遊戲", "開始遊戲"]

def get_user_profile(user_id):
    """獲取用戶的LINE個人資料"""
    try:
        return line_bot_api.get_profile(user_id)
    except Exception as e:
        logger.error(f"無法獲取用戶資料: {e}")
        return None

def create_analysis_flex_message(analysis_data, display_name, message_to_analyze):
    """創建詐騙分析結果的Flex Message格式"""
    risk_level = analysis_data.get("risk_level", "不確定")
    fraud_type = analysis_data.get("fraud_type", "未知")
    explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
    suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
    
    # 根據風險等級設置顏色
    if risk_level in ["高", "高風險"]:
        risk_color = "#FF0000"  # 紅色
        risk_emoji = "⚠️"
    elif risk_level in ["中", "中風險"]:
        risk_color = "#FFCC00"  # 黃色
        risk_emoji = "⚠️"
    elif risk_level in ["低", "低風險"]:
        risk_color = "#008000"  # 綠色
        risk_emoji = "✅"
    else:
        risk_color = "#808080"  # 灰色
        risk_emoji = "❓"
    
    # 構建Flex Message
    bubble = BubbleContainer(
        header=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(
                    text=f"風險分析結果 {risk_emoji}",
                    weight='bold',
                    size='xl',
                    color='#ffffff'
                )
            ],
            background_color=risk_color
        ),
        body=BoxComponent(
            layout='vertical',
            contents=[
                BoxComponent(
                    layout='vertical',
                    margin='xs',
                    spacing='sm',
                    contents=[
                        BoxComponent(
                            layout='baseline',
                            contents=[
                                TextComponent(
                                    text='風險等級：',
                                    color='#aaaaaa',
                                    size='sm',
                                    flex=2
                                ),
                                TextComponent(
                                    text=risk_level,
                                    wrap=True,
                                    color=risk_color,
                                    size='sm',
                                    flex=5,
                                    weight='bold'
                                )
                            ]
                        ),
                        BoxComponent(
                            layout='baseline',
                            contents=[
                                TextComponent(
                                    text='詐騙類型：',
                                    color='#aaaaaa',
                                    size='sm',
                                    flex=2
                                ),
                                TextComponent(
                                    text=fraud_type,
                                    wrap=True,
                                    color='#666666',
                                    size='sm',
                                    flex=5
                                )
                            ]
                        )
                    ]
                ),
                TextComponent(
                    text=f"分析內容：\n{message_to_analyze[:60] + '...' if len(message_to_analyze) > 60 else message_to_analyze}",
                    size='xs',
                    wrap=True,
                    margin='md',
                    color='#555555'
                ),
                SeparatorComponent(margin='lg'),
                BoxComponent(
                    layout='vertical',
                    margin='lg',
                    contents=[
                        TextComponent(
                            text='分析說明',
                            weight='bold',
                            size='md',
                            margin='none'
                        ),
                        TextComponent(
                            text=explanation,
                            size='sm',
                            wrap=True,
                            margin='md'
                        )
                    ]
                ),
                BoxComponent(
                    layout='vertical',
                    margin='lg',
                    contents=[
                        TextComponent(
                            text='建議',
                            weight='bold',
                            size='md',
                            margin='none'
                        ),
                        TextComponent(
                            text=suggestions,
                            size='sm',
                            wrap=True,
                            margin='md'
                        )
                    ]
                )
            ]
        ),
        footer=BoxComponent(
            layout='vertical',
            spacing='sm',
            contents=[
                TextComponent(
                    text='如有疑慮，請撥打165反詐騙專線',
                    size='xs',
                    wrap=True,
                    align='center',
                    color='#aaaaaa'
                ),
                TextComponent(
                    text='本風險分析僅作參考使用，請自行評估實際風險',
                    size='xs',
                    wrap=True,
                    align='center',
                    color='#aaaaaa',
                    margin='md'
                ),
                SeparatorComponent(margin='md'),
                ButtonComponent(
                    style='primary',
                    color='#1DB446',
                    action=MessageAction(label='再次分析', text='請幫我分析這則訊息：')
                )
            ]
        )
    )
    
    return FlexSendMessage(alt_text='詐騙風險分析結果', contents=bubble)

@app.route("/", methods=["GET"])
def index():
    # 传递fraud_types变量给模板
    return render_template("index.html", fraud_types=fraud_tactics_data)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
        
    return 'OK'

@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    profile = get_user_profile(user_id)
    display_name = profile.display_name if profile else "未知用戶"
    text_message = event.message.text
    reply_token = event.reply_token
    
    logger.info(f"Received message from {display_name} ({user_id}): {text_message}")
    
    # 簡單的回覆功能（演示用）
    if any(keyword in text_message.lower() for keyword in function_inquiry_keywords):
        reply_text = f"{display_name}您好！我是防詐騙小幫手，我的功能包括：\n\n" \
                    f"1️⃣ 詐騙風險分析：我可以分析您收到的可疑訊息，評估是否為詐騙\n\n" \
                    f"2️⃣ 詐騙類型查詢：您可以輸入「詐騙類型列表」查看各種常見詐騙\n\n" \
                    f"3️⃣ 「選哪顆土豆」小遊戲：通過遊戲學習辨識詐騙訊息\n\n" \
                    f"請選擇您想嘗試的功能："
        
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
            QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
        ])
        
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
        return
    
    # 默認回復
    reply_text = f"您好 {display_name}！如果您需要防詐騙幫助，請輸入「功能」查看我能做什麼！"
    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))

# 如果直接运行此文件
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000))) 