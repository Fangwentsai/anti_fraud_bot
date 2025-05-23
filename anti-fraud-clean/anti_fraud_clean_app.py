# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, request, abort, render_template, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage,
    QuickReply, QuickReplyButton, MessageAction, PostbackEvent, PostbackAction,
    BubbleContainer, BoxComponent, ButtonComponent, TextComponent,
    CarouselContainer, URIAction, SeparatorComponent, 
    ImageSendMessage, Sender, SendMessage
)
from dotenv import load_dotenv
import openai
import logging
from firebase_manager import FirebaseManager
import random
import datetime  # 導入datetime用於時間比較
import re
import time
import requests
from urllib.parse import urlparse

# 指定 .env 文件的路徑
# 假設 anti-fraud-clean 和 linebot-anti-fraud 是同級目錄
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'linebot-anti-fraud', '.env')
load_dotenv(dotenv_path=dotenv_path)

# 短網址服務的域名列表
SHORT_URL_DOMAINS = [
    'bit.ly', 'tinyurl.com', 'goo.gl', 'is.gd', 'buff.ly', 
    'ow.ly', 't.co', 'rebrand.ly', 'cutt.ly', 'shorturl.at',
    'urls.tw', 'ppt.cc', 'reurl.cc', 'lihi.vip', 'lihi1.com', 
    'lihi2.cc', 'lihi3.cc', 'tny.im', 'tinyurl.app'
]

# 台灣常用的可靠網站域名白名單
SAFE_DOMAINS = [
    'line.me', 'line.com', 'shopping.friday.tw', 'friday.tw', 'taipei.gov.tw', 
    'gov.tw', 'edu.tw', 'ntu.edu.tw', 'ntnu.edu.tw', 'ntust.edu.tw', 
    'taiwanmobile.com', 'fetnet.net', 'cht.com.tw', 'chunghua.com.tw', 
    'chunghwa.com.tw', 'hinet.net', 'famiport.com.tw', 'wemoscooter.com', 
    'youbike.com.tw', 'ubike.com.tw', 'ibon.com.tw', 'ezpay.com.tw', 
    'icstw.com.tw', 'lego.com', 'apple.com', 'microsoft.com', 'google.com', 
    'facebook.com', 'instagram.com', 'shopee.tw', 'momoshop.com.tw', 
    'ruten.com.tw', 'pcstore.com.tw', 'pchome.com.tw', 'books.com.tw', 
    'kingstone.com.tw', 'eslite.com', 'cathaylife.com.tw', 'skyscanner.com.tw', 
    'booking.com', 'agoda.com', 'klook.com', 'kkday.com', 'iaai.com.tw',
    'mcdonalds.com.tw', 'foodpanda.com.tw', 'ubereats.com', 'pizzahut.com.tw',
    'dominos.com.tw', 'post.gov.tw', 'ipost.com.tw', 'family.com.tw',
    'hilife.com.tw', 'okmart.com.tw', '7-11.com.tw', 'seveneleven.com.tw', 
    'buymeacoffee.com', 'bokail.com', 'documid.com'
]

app = Flask(__name__)

# Line API 設定
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', ''))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET', ''))

# OpenAI設定
openai.api_key = os.environ.get('OPENAI_API_KEY', '')

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化Firebase管理器
firebase_manager = FirebaseManager.get_instance()

# 用戶遊戲狀態
user_game_state = {}

# 用戶最後聊天時間記錄
user_last_chat_time = {}
user_pending_analysis = {} # 用於追蹤等待用戶澄清的分析請求
first_time_chatters = set()  # 追蹤首次聊天的用戶

CHAT_TIP_PROBABILITY = 0.3 # 閒聊時回覆防詐小知識的機率

# 定義關鍵詞和模式
function_inquiry_keywords = ["功能", "幫助", "會什麼", "能做什麼", "使用說明", "你是誰"]
follow_up_patterns = ["被騙", "詐騙", "可疑", "不確定", "幫我看看", "這是詐騙嗎", "這是真的嗎"]
potato_game_trigger_keywords = ["選哪顆土豆", "玩遊戲", "土豆遊戲", "選土豆", "選土豆遊戲", "開始遊戲"]
bot_trigger_keyword = "嗨土豆" # 群組中觸發機器人服務的關鍵詞

# 定義分析提示詞
analysis_prompts = ["請幫我分析這則訊息：", "幫我分析這則訊息", "分析這則訊息", "幫我分析訊息", "請幫我分析詐騙網站", "幫我分析詐騙網站"]

def expand_short_url(url):
    """
    嘗試展開短網址，返回原始URL和展開後的URL
    
    Args:
        url: 可能的短網址
    
    Returns:
        tuple: (原始URL, 展開後的URL, 是否為短網址, 是否成功展開)
    """
    # 檢查是否為短網址
    parsed_url = urlparse(url)
    is_short_url = False
    for domain in SHORT_URL_DOMAINS:
        if domain in parsed_url.netloc:
            is_short_url = True
            break
    
    if not is_short_url:
        return url, url, False, False
    
    # 嘗試展開短網址
    try:
        session = requests.Session()
        response = session.head(url, allow_redirects=True, timeout=5)
        expanded_url = response.url
        
        if expanded_url != url:
            logger.info(f"成功展開短網址: {url} -> {expanded_url}")
            return url, expanded_url, True, True
        else:
            logger.warning(f"URL可能不是短網址或無法展開: {url}")
            return url, url, True, False
    except Exception as e:
        logger.error(f"展開短網址時出錯: {e}")
        return url, url, True, False

# 定義防詐小知識
anti_fraud_tips = [
    "🔍 收到不明連結？先確認發信人身分，再三思而後行。點擊前問自己：這真的必要嗎？",
    "🔐 請定期更換密碼，並避免在不同平台使用相同的密碼組合。建議使用密碼管理工具！",
    "📱 接到自稱銀行、警方的電話？掛斷後，主動撥打官方電話確認，不要回撥對方提供的號碼。",
    "💰 投資報酬率高得不合理？記住：天下沒有白吃的午餐，高報酬必有高風險！",
    "🤝 網路交友要謹慎，短時間內就談及金錢往來的「好友」很可能是詐騙集團。",
    "🏦 真正的銀行絕不會請你操作ATM「解除設定」、「升級系統」或「確認身分」。",
    "🛒 網購只用正規平台，交易時留在平台內完成，切勿私下交易或提前付款。",
    "🎮 購買遊戲點數前，先確認用途，若是給陌生人或解凍帳戶使用，極可能是詐騙！"
]

# 詐騙類型分類
fraud_types = {
    "網路購物詐騙": {
        "description": "涉及假冒購物網站、虛假商品或不實廣告的詐騙",
        "examples": [
            "🛒 假買家騙賣家詐騙案例 🛒\n\n詐騙集團假扮買家接觸二手商品賣家，聲稱透過蝦皮等平台交易，引導賣家加入假冒客服LINE帳號，以「簽署保證書」、「銀行認證」等藉口誘導賣家進行網路銀行轉帳或LINE Pay付款，導致受害者財產損失。\n\n📊 資料來源：165打詐儀表板"
        ],
        "sop": [
            "⚠️ 防範網路購物詐騙注意事項 ⚠️",
            "1️⃣ 有網路交易問題，請洽交易平臺公告的官方客服聯繫方式，不要使用陌生人提供的聯繫方式",
            "2️⃣ 堅守平台內部交易，不要跳出蝦皮、露天或其他平台的對話系統",
            "3️⃣ 銀行及蝦皮等平台不會以私人LINE帳號聯繫客戶",
            "4️⃣ 遇到要求「簽署保證書」、「銀行認證」等操作時，請提高警覺",
            "5️⃣ 絕對不要依照他人指示操作網路銀行或進行轉帳",
            "6️⃣ 有任何疑問，請立即撥打165反詐騙專線諮詢"
        ]
    },
    "假交友投資詐騙": {
        "description": "透過網路交友平台或社群媒體，假扮有好感的異性建立感情連結，最終以各種理由騙取金錢",
        "examples": [
            "💔 網路交友詐騙案例 💔\n\n詐騙者假扮高社經地位人士（如醫生、軍官、機長等）與被害者在網路上認識並建立情感連結，長期噓寒問暖後，以生病需要醫藥費、寄送海外禮物需繳納關稅等各種理由，誘騙被害者轉帳或面交金錢。此類詐騙特別針對寡居或情感生活較為孤單的中老年人。\n\n📊 資料來源：165打詐儀表板"
        ],
        "sop": [
            "⚠️ 防範交友投資詐騙注意事項 ⚠️",
            "1️⃣ 網友見都沒見過卻談及金錢，高度可能是詐騙",
            "2️⃣ 對方自稱長期在國外工作（如軍醫、機長等）且無法見面，但很快發展感情關係，應提高警覺",
            "3️⃣ 拒絕任何以緊急醫療費、運費、稅金等名義要求的金錢往來",
            "4️⃣ 不要聽信需要協助開通外幣帳戶、借用帳戶的說法",
            "網友見都沒見過卻談及金錢，高度可能是詐騙",
            "對方自稱長期在國外工作（如軍醫、機長等）且無法見面，但很快發展感情關係，應提高警覺",
            "拒絕任何以緊急醫療費、運費、稅金等名義要求的金錢往來",
            "不要聽信需要協助開通外幣帳戶、借用帳戶的說法",
            "避免協助陌生網友申辦手機門號或提供SIM卡",
            "對於網友所提供的身份資訊，嘗試多方查證",
            "有任何疑問，請立即撥打165反詐騙專線諮詢",
            "多與家人朋友分享交友情況，避免單獨做出財務決定"
        ]
    },
    "假中獎通知詐騙": {
        "description": "冒充官方單位或知名企業，宣稱中獎但需繳納手續費等費用才能領獎的詐騙",
        "examples": [],
        "sop": []
    },
    "假借銀行貸款詐騙": {
        "description": "假冒金融機構人員，宣傳低利快速貸款，但要求先支付手續費或購買點數",
        "examples": [
            "一名急需資金償還家庭債務的民眾在Facebook看到名為「數位速e貸」的廣告，標榜貸款快速、利息低且手續簡單。於是加入了一個名為「台北富邦銀行信貸」的LINE帳號。在申請貸款30萬元並通過初審後，對方表示需要購買一份金融貸款保險，才能提高信用評分。受害者匯了1萬5千元到指定帳戶後，對方又要求購買點數卡以增加信貸評分。受害者多次購買點數卡並提供給對方。不久後，受害者發現網路銀行帳戶無法使用，聯繫對方也已失聯。向銀行客服查詢後，確認帳戶已被列入警示名單，且這根本不是台北富邦銀行的業務。"
        ],
        "sop": [
            "貸款請找合法的金融機構、保險公司辦理",
            "合法貸款機構不會要求事先支付手續費或保證金",
            "銀行辦理信貸，絕不會要求購買點數卡或預先匯款",
            "又是貸款、又是點數卡，絕對是詐騙",
            "直接前往銀行分行或透過官方網站申請貸款",
            "不要點擊不明來源的貸款廣告連結",
            "不要輕信「免聯徵、快速核貸」等宣傳",
            "保護個人資料，不輕易提供身分證影本",
            "有貸款需求應向合法金融機構諮詢",
            "對於要求先匯款才能貸款的服務要特別警覺",
            "確認貸款機構是否為金管會核准的合法機構",
            "若有疑慮，請撥打165反詐騙專線諮詢"
        ]
    },
    "假廣告詐騙": {
        "description": "透過網路平台發布虛假的廣告資訊，如租屋、票券代購、工作機會等，要求預付訂金後消失",
        "examples": [
            "一名大學三年級學生因為沒有抽中學校宿舍，在Facebook的租屋版社團看到房東「Joyce」發佈的租屋訊息。照片中房間屋況良好，周遭生活機能便利，租金合理且可申請租屋補助。學生加了房東的LINE，房東表示學生排在第5組看房，但前面已有客人打算預付訂金優先看屋。為了搶先看屋，學生立即匯了租金加訂金共3萬元。之後，房東聲稱其丈夫誤收了其他客人訂金，請學生先匯款給那位客人以保留優先權。學生提出退費要求後，房東消失無蹤。"
        ],
        "sop": [
            "網路租屋，若聽見看屋優先權，極可能是詐騙",
            "網路租屋應洽房屋仲介公司或正規租屋網站",
            "沒有看到房屋實體前，不要支付任何訂金或租金",
            "合法的租屋或票券交易不會要求預付款項",
            "對於急迫推銷「限時優惠」的廣告保持警惕",
            "查證廣告發布者的真實身份和評價",
            "使用有保障的第三方支付或交易平台",
            "利用Google圖片搜尋功能查證租屋照片是否為盜用",
            "請親友陪同看房，避免獨自決策",
            "若有疑慮，請撥打165反詐騙專線諮詢"
        ]
    },
    "色情應召詐財詐騙": {
        "description": "透過網路平台宣傳色情服務，要求支付「訂金」、「保證金」等費用，但實際上不提供任何服務",
        "examples": [
            "一名男性在社群媒體上看到某粉專提供外送茶服務的廣告，便私訊詢問。對方提供了多張女性照片供選擇，並說明價格和服務內容。該男性選定後，對方表示需先支付5,000元的訂金，才會安排女伴前往。匯款後，對方又表示因為是首次交易，為確保安全，需再支付5,000元「保證金」，承諾女伴抵達後可退還。男性再次匯款後，對方又以「車資」、「安全檢查費」等理由要求額外付款。此時男性意識到可能受騙，拒絕再付款並要求退款，但對方已將其封鎖，無法聯繫。"
        ],
        "sop": [
            "任何要求先匯款的色情服務廣告，幾乎都是詐騙",
            "不要相信網路上陌生人提供的色情服務",
            "避免在不明來源的網站或社群媒體上尋找此類服務",
            "保護個人資料，避免身份被盜用或遭勒索",
            "不要輕信不合理的收費方式或理由",
            "對於反覆要求「額外費用」的行為提高警覺",
            "色情交易在台灣是違法的，可能面臨法律風險",
            "若已遭詐騙，應保留所有通訊記錄作為證據",
            "若有疑慮，請撥打165反詐騙專線諮詢"
        ]
    },
    "虛擬遊戲詐騙": {
        "description": "透過遊戲內聊天或社群媒體接觸玩家，提供虛假的遊戲點數、外掛或服務，騙取金錢或帳號",
        "examples": [
            "一名高中生在某線上遊戲中認識一位「資深玩家」，對方表示可以幫忙代購遊戲點數，只需要市價的七折。高中生心動不已，先後匯了3,000元購買遊戲點數。交易順利後，「資深玩家」又推薦一個能提升角色能力的外掛程式，聲稱只要安裝就能獲得遊戲優勢。高中生下載安裝了該程式，不久後發現遊戲帳號被盜，所有虛擬物品被轉移，且該程式還竊取了他電腦中的個人資料，導致其父母的銀行帳戶遭盜刷。"
        ],
        "sop": [
            "只透過遊戲官方管道購買遊戲點數或物品",
            "不要下載來路不明的外掛或修改程式",
            "保護遊戲帳號密碼，不隨意提供給他人",
            "價格明顯低於市場的交易多為詐騙",
            "不要相信可以破解遊戲系統的說法",
            "遊戲內交友需謹慎，不輕易透露個人資訊",
            "使用雙重認證保護重要遊戲帳號",
            "定期更換密碼並檢查帳號安全設置",
            "不要使用與其他平台相同的密碼",
            "若有疑慮，請撥打165反詐騙專線諮詢"
        ]
    },
    "假求職詐騙": {
        "description": "以虛假工作機會為誘餌，騙取個人銀行帳戶或金融卡的詐騙",
        "examples": [
            "一名舞者在社群平台分享自己的表演影片，收到網友「寧靜致遠」私訊，表示欣賞其舞蹈風格，邀請參加私人聚會表演。雙方轉至LINE溝通，對方以支付訂金為由，要求提供銀行帳戶。此後，對方失聯，但受害者帳戶陸續有不明款項匯入。最終被告知帳戶已被列為警示帳戶，警方調查發現這些款項涉及其他詐騙案件，受害者的帳戶被用來洗錢。"
        ],
        "sop": [
            "不要提供銀行帳戶資料給陌生人",
            "帳戶有不明匯入款項，請聯繫開戶銀行並立即報警",
            "對於高薪、低門檻的工作邀約保持警覺",
            "不要輕易相信可以快速賺錢的工作機會",
            "不要寄出金融卡、提款卡或存簿給他人",
            "不要將卡片放置於指定置物櫃、郵箱供他人收取",
            "避免協助他人操作ATM或網路銀行",
            "工作內容若涉及金融交易或轉帳，多半是詐騙",
            "徵才管道應以正規求職平台為主",
            "有任何疑問，請撥打165反詐騙專線諮詢"
        ]
    },
    "假檢警詐騙": {
        "description": "冒充執法機關人員（警察、檢察官、法官等）進行詐騙，以「證件遭冒用」、「涉及刑案」等藉口，誘導被害人提供金融資訊或匯款",
        "examples": [
            "民眾小劉接獲假冒馬偕醫院人員電話，對方佯稱有人持小劉證件代領管制藥品，需要核實身分。當小劉否認有委託代領藥品一事，假冒醫院人員隨即告知將由檢警接手。隨後假冒警察、檢察官接連來電，羅織罪名後，要求小劉交付金融卡與帳戶資料。幸好小劉保持警覺，事後立即通報165檢舉。此案與近期醫療院所病患個資外洩有關，詐騙集團可能取得這些外洩個資，進行精準詐騙。"
        ],
        "sop": [
            "檢警不會用電話通知涉案，會以公文傳喚",
            "檢警不會要求提供金融帳戶、存摺或金融卡",
            "檢警不會要求解除分期付款",
            "檢警不會監管銀行帳戶或操作ATM",
            "檢警不會要求交付現金或匯款",
            "檢警不會用LINE製作筆錄",
            "檢警不會以電話傳送公文",
            "接到可疑來電，掛斷並撥打165反詐騙專線查證",
            "對來電顯示110或派出所電話保持懷疑，這些號碼可能被偽造",
            "醫院絕不會轉接檢警處理冒用身分或代領藥品事宜",
            "不透露個人資訊，不點擊不明連結，不輕易匯款"
        ]
    },
    "金融帳戶詐騙": {
        "description": "透過各種手段騙取民眾金融帳戶、金融卡或網路銀行密碼，用於非法交易或洗錢",
        "examples": [
            "受害者看到一則「出租金融帳戶，輕鬆賺租金」的廣告後心動，與對方聯繫並按指示將提款卡和帳戶資訊放置在指定的變電箱中。詐騙者取得帳戶控制權後進行大量非法交易，導致帳戶被銀行凍結，受害者不僅未得到承諾的租金，還面臨法律追訴風險。"
        ],
        "sop": [
            "帳戶、提款卡及密碼是個人財務安全核心，切勿出租或交予他人",
            "任何聲稱出租帳戶可賺錢的廣告，都是詐騙",
            "不要受高報酬誘惑出借金融帳戶",
            "不要輕信可輕鬆賺取額外收入的廣告",
            "銀行客服不會要求提供完整卡號或密碼",
            "發現帳戶有異常活動，應立即聯繫銀行或撥打165專線",
            "不要在未經確認的網站輸入金融資訊",
            "保護個人金融資訊，不要向陌生人透露"
        ]
    },
    "釣魚簡訊詐騙": {
        "description": "透過偽裝成官方機構或知名企業的訊息，誘導點擊惡意連結，騙取個人資料或金融資訊",
        "examples": [
            "民眾小張收到一則聲稱來自中華電信的簡訊，內容為：「[中華電信]您正在申請的網路服務因個資驗證失敗，請點擊下方連結重新補驗...」，並附上一串短網址。小張一時不察點擊連結，進入一個與中華電信官網極為相似的頁面，並依照指示輸入了身分證字號、銀行帳號及信用卡資訊。不久後，他便收到銀行通知有多筆不明消費，才驚覺受騙。"
        ],
        "sop": [
            "收到任何要求點擊連結並輸入個人資料的簡訊，務必提高警覺。",
            "不要點擊來源不明的簡訊連結。",
            "官方機構不會透過簡訊要求民眾輸入敏感個資或銀行帳戶資訊。",
            "仔細檢查網址是否為官方網址，釣魚網站通常會有細微差異。",
            "開啟簡訊實聯制，並確認發送號碼是否為官方號碼。",
            "若不確定簡訊真偽，應直接向官方客服查證，而非點擊簡訊中連結。",
            "安裝防毒軟體並定期更新，可協助偵測惡意網站。",
            "教育家中長輩識別釣魚簡訊的技巧。",
            "若已點擊並輸入資料，應立即聯繫銀行停卡並報警處理。"
        ]
    },
    "點數購買詐騙": {
        "description": "要求被害人購買遊戲點數、禮品卡等，並提供其序號或密碼的詐騙手法",
        "examples": [
            "🎮 虛擬寶物換現金的騙局 🎮\n\n我在《熱血江湖》遊戲打到了一件相當稀有罕見的寶物，在遊戲圈內吸引了不少玩家的注意，有一位遊戲暱稱「林北小舞」的好友私訊我，說他很想收購我的寶物。他表示寶物對他組裝裝備非常重要，願意以8,500元價格購入。因為之前我們曾組隊聊過好幾次，對方看起來不像騙子，我便答應出售寶物。\n\n不過，對方說月底才領薪水，無法馬上付款，能否先交付寶物讓他提前增強裝備，等到月底領薪後再匯款。我心想，大家都是同一個遊戲公會的老玩家，有一定的信任基礎，沒多想就把寶物交給了他。\n\n之後，我和「林北小舞」依舊每天在遊戲中互動，他誇讚我那件寶物幫了他大忙，讓他在遊戲中如虎添翼。然而，到了約定付款日期，我卻始終沒收到他的匯款消息。剛開始，我提醒他幾次，他總是各種理由推脫，要嘛薪水延遲發放、要嘛家裡臨時有急用，畢竟我們也算是朋友，就再寬限幾天吧。\n\n有天，我發現他不再回我訊息，連遊戲角色也消失得無影無蹤，我這才驚覺，自己被騙了！\n\n📊 資料來源：165打詐儀表板"
        ],
        "sop": [
            "⚠️ 常見犯罪手法及話術 ⚠️",
            "1️⃣ 雙方約定交易遊戲帳號/遊戲裝備/點數",
            "2️⃣ 要求至遊戲交易平台網站交易，卻被網站告知帳戶出錯要求儲值才能退款",
            "3️⃣ 對方稱不明原因無法交易傳送一國際擔保平台交易連結，平台客服稱帳戶凍結，需儲值才能解凍",
            "4️⃣ 要求匯款至指定帳戶儲值",
            "5️⃣ 要求購買點數卡後拍照",
            "",
            "🛡️ 防詐小撇步 🛡️",
            "虛擬寶物交易，應選擇官方認可的第三方平台，才有保障。",
            "",
            "🔍 詐騙話術解析 🔍",
            "1. 虛擬遊戲好友表達購買虛擬寶物意願",
            "2. 誘騙提前交付虛擬寶物，卻藉故延遲付款，並失聯"
        ]
    }
}

# 加載詐騙話術資料庫 (可選)
FRAUD_TACTICS_DB = "fraud_tactics.json"
fraud_tactics_data = {}

def load_fraud_tactics():
    global fraud_tactics_data
    try:
        with open(FRAUD_TACTICS_DB, 'r', encoding='utf-8') as f:
            fraud_tactics_data = json.load(f)
        logger.info(f"成功從 {FRAUD_TACTICS_DB} 加載詐騙話術數據")
    except FileNotFoundError:
        logger.warning(f"詐騙話術文件 {FRAUD_TACTICS_DB} 未找到。")
        fraud_tactics_data = {} # Ensure it's an empty dict if file not found
    except json.JSONDecodeError:
        logger.error(f"解析詐騙話術文件 {FRAUD_TACTICS_DB} 失敗。")
        fraud_tactics_data = {} # Ensure it's an empty dict on parse error
    except Exception as e:
        logger.error(f"加載詐騙話術時發生未知錯誤: {e}")
        fraud_tactics_data = {}

load_fraud_tactics()

# 詐騙話術資料庫
fraud_tactics = fraud_tactics_data

# 獲取用戶個人資料
def get_user_profile(user_id):
    try:
        profile = line_bot_api.get_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"獲取用戶 {user_id} 個人資料失敗: {e}")
        return None

# 分析詐騙風險並解析結果
def parse_fraud_analysis(analysis_result):
    """
    從ChatGPT的回應中解析出詐騙分析結果。
    預期格式：
    風險等級：[高/中/低/無風險/不確定]
    可能詐騙類型：[類型1, 類型2, ... 或 不適用]
    說明：[具體說明]
    建議：[具體建議] 
    新興手法：[是/否] (可選)
    """
    if not analysis_result:
        return {
            "risk_level": "不確定",
            "fraud_type": "未知",
            "explanation": "無法獲取分析結果。",
            "suggestions": "請稍後再試或聯繫客服。",
            "is_emerging": False
        }

    # 初始結果字典，包含預設值
    result = {
        "risk_level": "不確定",
        "fraud_type": "未知",
        "explanation": "無法解析分析結果。",
        "suggestions": "請保持警惕，如有疑問可諮詢165反詐騙專線。",
        "is_emerging": False
    }

    try:
        # 先處理最常見的情況：JSON格式
        if analysis_result.strip().startswith('{') and analysis_result.strip().endswith('}'):
            import json
            try:
                # 嘗試解析JSON
                parsed_data = json.loads(analysis_result)
                
                # 風險等級 - 處理各種可能的鍵名和格式
                for key in ['risk_level', 'risk level', 'riskLevel', '風險等級', '風險']:
                    if key in parsed_data and parsed_data[key]:
                        result["risk_level"] = parsed_data[key]
                        break
                
                # 詐騙類型 - 處理各種可能的鍵名和格式
                for key in ['fraud_type', 'type', 'fraudType', '詐騙類型', '可能詐騙類型', '類型']:
                    if key in parsed_data and parsed_data[key]:
                        result["fraud_type"] = parsed_data[key]
                        break
                
                # 處理"無"或"不適用"的詐騙類型
                if result["fraud_type"].lower() in ["不適用", "無", "none", "n/a"]:
                 result["fraud_type"] = "非詐騙相關"
                
                # 解釋說明 - 處理各種可能的鍵名和格式
                for key in ['explanation', 'explain', '說明', '分析理由', '理由', '分析']:
                    if key in parsed_data and parsed_data[key]:
                        # 如果是列表，就用換行符合併
                        if isinstance(parsed_data[key], list):
                            result["explanation"] = '\n'.join(parsed_data[key])
                        else:
                            result["explanation"] = parsed_data[key]
                        break
                
                # 建議 - 處理各種可能的鍵名和格式
                for key in ['suggestions', 'suggestion', 'advice', '建議', '防範建議']:
                    if key in parsed_data and parsed_data[key]:
                        # 如果是列表，就用換行符合併
                        if isinstance(parsed_data[key], list):
                            result["suggestions"] = '\n'.join(parsed_data[key])
                        else:
                            result["suggestions"] = parsed_data[key]
                        break
                
                # 新興手法 - 處理各種可能的鍵名和格式
                for key in ['is_emerging', 'isEmerging', '新興手法', '是否新興']:
                    if key in parsed_data:
                        # 處理不同的布爾值格式
                        val = parsed_data[key]
                        if isinstance(val, bool):
                            result["is_emerging"] = val
                        elif isinstance(val, str):
                            result["is_emerging"] = val.lower() in ['true', 'yes', '是', '1', 't', 'y']
                        elif isinstance(val, int):
                            result["is_emerging"] = val == 1
                        break
                
                # 如果任何必要字段仍然缺少，我們可以通過原始文本進行進一步解析
                if result["risk_level"] == "不確定" or result["fraud_type"] == "未知" or result["explanation"] == "無法解析分析結果。":
                    # 繼續使用文本解析方法
                    logger.info("JSON解析結果不完整，使用額外的文本解析")
                else:
    return result

            except json.JSONDecodeError as e:
                # JSON解析失敗，使用文本解析
                logger.warning(f"JSON解析失敗: {e}，改用文本解析")
        
        # 文本解析 - 增強的版本，可以處理各種格式
        # 使用多種分隔符號和模式匹配
        
        # 1. 分析風險等級
        risk_patterns = [
            r'風險等級[：:]\s*(.+?)(?:\n|$)',
            r'risk_level[：:]\s*(.+?)(?:\n|$)',
            r'風險[：:]\s*(.+?)(?:\n|$)',
            r'1\.\s*(?:風險等級)?[：:]\s*(.+?)(?:\n|$)'
        ]
        for pattern in risk_patterns:
            import re
            match = re.search(pattern, analysis_result, re.IGNORECASE)
            if match:
                result["risk_level"] = match.group(1).strip()
                break
        
        # 2. 分析詐騙類型
        fraud_patterns = [
            r'詐騙類型[：:]\s*(.+?)(?:\n|$)',
            r'fraud_type[：:]\s*(.+?)(?:\n|$)',
            r'可能詐騙類型[：:]\s*(.+?)(?:\n|$)',
            r'類型[：:]\s*(.+?)(?:\n|$)',
            r'2\.\s*(?:詐騙類型)?[：:]\s*(.+?)(?:\n|$)'
        ]
        for pattern in fraud_patterns:
            match = re.search(pattern, analysis_result, re.IGNORECASE)
            if match:
                fraud_type = match.group(1).strip()
                if fraud_type.lower() in ["不適用", "無", "none", "n/a"]:
                    fraud_type = "非詐騙相關"
                result["fraud_type"] = fraud_type
                break
        
        # 3. 分析理由/說明
        explanation_patterns = [
            r'說明[：:]\s*(.+?)(?=(?:建議|suggestions|suggestion|防範建議|新興手法|is_emerging|$))',
            r'explanation[：:]\s*(.+?)(?=(?:建議|suggestions|suggestion|防範建議|新興手法|is_emerging|$))',
            r'分析理由[：:]\s*(.+?)(?=(?:建議|suggestions|suggestion|防範建議|新興手法|is_emerging|$))',
            r'理由[：:]\s*(.+?)(?=(?:建議|suggestions|suggestion|防範建議|新興手法|is_emerging|$))',
            r'3\.\s*(?:分析理由)?[：:]\s*(.+?)(?=(?:4\.|建議|suggestions|suggestion|防範建議|新興手法|is_emerging|$))'
        ]
        for pattern in explanation_patterns:
            match = re.search(pattern, analysis_result, re.IGNORECASE | re.DOTALL)
            if match:
                explanation = match.group(1).strip()
                if explanation:
                    result["explanation"] = explanation
                break
        
        # 4. 防範建議
        suggestion_patterns = [
            r'建議[：:]\s*(.+?)(?=(?:新興手法|is_emerging|$))',
            r'suggestions[：:]\s*(.+?)(?=(?:新興手法|is_emerging|$))',
            r'suggestion[：:]\s*(.+?)(?=(?:新興手法|is_emerging|$))',
            r'防範建議[：:]\s*(.+?)(?=(?:新興手法|is_emerging|$))',
            r'4\.\s*(?:防範建議)?[：:]\s*(.+?)(?=$)'
        ]
        for pattern in suggestion_patterns:
            match = re.search(pattern, analysis_result, re.IGNORECASE | re.DOTALL)
            if match:
                suggestions = match.group(1).strip()
                if suggestions:
                    result["suggestions"] = suggestions
                break
        
        # 5. 新興手法
        emerging_patterns = [
            r'新興手法[：:]\s*(.+?)(?:\n|$)',
            r'is_emerging[：:]\s*(.+?)(?:\n|$)'
        ]
        for pattern in emerging_patterns:
            match = re.search(pattern, analysis_result, re.IGNORECASE)
            if match:
                emerging_text = match.group(1).strip().lower()
                result["is_emerging"] = emerging_text in ["是", "true", "yes", "1", "t", "y"]
                break
        
        # 確保結果中所有的文本字段不為空
        for key in ["risk_level", "fraud_type", "explanation", "suggestions"]:
            if not result[key] or result[key].strip() == "":
                if key == "risk_level":
                    result[key] = "不確定"
                elif key == "fraud_type":
                    result[key] = "未知"
                elif key == "explanation":
                    result[key] = "無法提取分析理由。"
                elif key == "suggestions":
                    result[key] = "請保持警惕，如有疑問可諮詢165反詐騙專線。"
        
        return result
    
    except Exception as e:
        logger.error(f"解析詐騙分析結果時發生錯誤: {e}")
        return {
            "risk_level": "不確定",
            "fraud_type": "未知",
            "explanation": "無法解析分析結果。系統錯誤，請稍後再試。",
            "suggestions": "請保持警惕，如有疑問可諮詢165反詐騙專線。",
            "is_emerging": False
        }

# 添加安全白名單
SAFE_DOMAINS = [
    "buymeacoffee.com/todao_antifruad",
    "buymeacoffee.com/todao",
    "ko-fi.com/todao",
    "patreon.com/todao"
]

def detect_fraud_with_chatgpt(user_message, display_name="朋友", user_id=None):
    """使用OpenAI的API檢測詐騙信息"""
    try:
        # 檢查訊息是否包含URL
        original_url = None
        expanded_url = None
        is_short_url = False
        url_expanded_successfully = False
        
        url_pattern = re.compile(r'(https?://\S+|www\.\S+)')
        url_match = url_pattern.search(user_message)
        
        if url_match:
            original_url = url_match.group(0)
            # 確保URL開頭是http://或https://
            if not original_url.startswith(('http://', 'https://')):
                original_url = 'https://' + original_url
                
            # 展開可能的短網址
            original_url, expanded_url, is_short_url, url_expanded_successfully = expand_short_url(original_url)
            
            # 如果是短網址且成功展開，調整分析訊息
            if is_short_url and url_expanded_successfully:
                # 將原始訊息中的短網址替換為展開後的URL，以便於分析
                analysis_message = user_message.replace(original_url, f"{original_url} (展開後: {expanded_url})")
                logger.info(f"已展開短網址進行分析: {original_url} -> {expanded_url}")
            else:
                analysis_message = user_message
        else:
            analysis_message = user_message

        # 檢查訊息是否包含白名單中的網址
        for safe_domain in SAFE_DOMAINS:
            if safe_domain in analysis_message:
                logger.info(f"檢測到白名單中的域名: {safe_domain}")
                return {
                    "success": True,
                    "message": "分析完成",
                    "result": {
                        "risk_level": "低風險",
                        "fraud_type": "非詐騙相關",
                        "explanation": f"這個網站是{safe_domain}，是台灣常見的可靠網站，可以安心使用。",
                        "suggestions": "這是正規網站，不必特別擔心。如有疑慮，建議您直接從官方管道進入該網站。",
                        "is_emerging": False,
                        "display_name": display_name,
                        "original_url": original_url,
                        "expanded_url": expanded_url,
                        "is_short_url": is_short_url,
                        "url_expanded_successfully": url_expanded_successfully
                    },
                    "raw_result": "經過分析，這是已知的可信任網站。"
                }
            
        # 如果是短網址但無法展開，提高風險評估
        special_notes = ""
        if is_short_url and not url_expanded_successfully:
            special_notes = "這是個短網址，但我們無法展開查看真正的目的地，這種情況要特別小心。短網址常被詐騙者利用來隱藏真實的惡意網站。除非您非常確定這個連結安全，否則不建議點擊。"
            logger.warning(f"無法展開的短網址: {original_url}，建議提高警覺")
        
        openai_prompt = f"""
        你是一個詐騙風險評估專家，專門為50歲以上的中老年人提供易懂的風險分析。
        請分析以下信息是否包含詐騙相關內容，並按照以下格式輸出結果：
        
        風險等級：（低風險、中風險、高風險）
        詐騙類型：（如果有詐騙風險，請指出具體類型，例如：假網購、假交友、假投資、假貸款、假求職等；如果無風險，填"無"）
        說明：（請用非常口語化、親切的語氣說明判斷依據，避免使用專業術語，就像在跟長輩解釋一樣。例如不要說「此網站使用混淆技術規避檢測」，而是說「這個網站看起來怪怪的，網址跟正常的不一樣，可能是假冒的」。也不要說「您」或「我」，而是直接說「這網站可能會騙人」「小心不要點這個連結」等）
        建議：（針對潛在風險，用簡單易懂的語言提供1-3點具體建議，例如「不要點這個連結」「不要提供銀行帳號」「收到這種訊息時，先打電話問問家人」等）
        新興手法：是/否
        
        {special_notes}
        
        以下是需要分析的信息：
        ---
        {analysis_message}
        ---
        
        請用繁體中文回答，避免直接使用問候語。直接開始分析。回答應簡潔直接，像是專家給出的風險提醒。
        """
        
        # 調用OpenAI API (修正為新版API格式)
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一個詐騙風險評估專家，請以50歲以上的長輩能理解的口語化方式分析詐騙風險。避免使用「您」「我」等主觀用詞，而是使用更直接的表述。提供的建議應該具體實用且直接。"},
                {"role": "user", "content": openai_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        if response and response.choices:
            analysis_result = response.choices[0].message.content.strip()
            logger.info(f"風險分析結果: {analysis_result[:100]}...")  # 僅記錄部分結果
            
            # 將結果解析成結構化格式
            parsed_result = parse_fraud_analysis(analysis_result)
            
            # 添加一個使用者可識別的標識
            parsed_result["display_name"] = display_name
            
            # 添加URL相關信息
            parsed_result["original_url"] = original_url
            parsed_result["expanded_url"] = expanded_url
            parsed_result["is_short_url"] = is_short_url
            parsed_result["url_expanded_successfully"] = url_expanded_successfully
            
            # 如果是短網址但無法展開，提高風險等級
            if is_short_url and not url_expanded_successfully:
                if parsed_result["risk_level"] == "低風險":
                    parsed_result["risk_level"] = "中風險"
                    parsed_result["explanation"] = f"{parsed_result['explanation']}\n\n⚠️ 此外，這是一個短網址但無法展開查看真正的目的地，這點也要特別小心。"
                
                if "短網址" not in parsed_result["explanation"]:
                    parsed_result["explanation"] = f"{parsed_result['explanation']}\n\n⚠️ 要注意這是一個短網址(像是縮短過的網址)，無法看到真正要去的網站，這種情況要特別小心。"
                
                if "短網址" not in parsed_result["suggestions"]:
                    parsed_result["suggestions"] = f"{parsed_result['suggestions']}\n• 遇到短網址時，最好先詢問傳送連結的人是什麼內容，或者乾脆不要點擊。"
            
            # 如果是短網址且成功展開，在結果中加入說明
            if is_short_url and url_expanded_successfully:
                parsed_result["explanation"] = f"{parsed_result['explanation']}\n\n這個連結是短網址，已經幫您展開查看真正的目的地是: {expanded_url}"
            
            # 檢查解析結果，確保所有必要欄位都有值
            if not parsed_result.get("explanation") or parsed_result["explanation"] == "無法解析分析結果。":
                # 如果無法正確解析理由，直接使用原始回應
                logger.warning("無法正確解析分析理由，使用原始回應替代")
                parsed_result["explanation"] = analysis_result.replace("風險等級：", "").replace("詐騙類型：", "").replace("說明：", "").replace("建議：", "").replace("新興手法：", "").strip()
                
                # 確保理由不為空
                if not parsed_result["explanation"] or parsed_result["explanation"].strip() == "":
                    parsed_result["explanation"] = "這個內容看起來有點奇怪，建議不要輕易點擊或提供個人資料。如果不確定，可以請家人幫忙確認一下。"
            
            return {
                "success": True,
                "message": "分析完成",
                "result": parsed_result,
                "raw_result": analysis_result
            }
        else:
            logger.error("OpenAI API 返回空結果")
            return {
                "success": False,
                "message": "分析失敗，請稍後再試"
            }
            
    except Exception as e:
        logger.exception(f"使用OpenAI分析詐騙信息時發生錯誤: {e}")
        return {
            "success": False,
            "message": f"分析過程中發生錯誤: {str(e)}"
        }

# --- Begin: Add these new functions for the game ---
def send_potato_game_question(user_id, reply_token):
    """
    Sends a new "選哪顆土豆" game question to the user.
    """
    global user_game_state
    
    # 優先從預設題庫選取題目
    if potato_game_questions:
        # 從題庫中隨機選取一道題目
        question = random.choice(potato_game_questions)
        
        # 詐騙訊息（假土豆）
        false_potato_text = question['fraud_message']
        fraud_type = question['fraud_type']
        explanation = question.get('explanation', '這是一則詐騙訊息，請保持警覺。')
        
        # 檢查題目是否已有預設選項
        if 'options' in question and question['options'] and 'correct_option' in question:
            # 使用題庫中的預設選項
            options = question['options'].copy()
            correct_option = question['correct_option']
            
            # 隨機打亂選項順序
            random.shuffle(options)
            
            # 重新映射選項ID (原本可能是A,B,C，現在換成新的順序)
            option_mapping = {'A': options[0], 'B': options[1], 'C': options[2] if len(options) > 2 else None}
            
            # 記錄正確答案的新位置
            for option_id, option in option_mapping.items():
                if option and option['id'] == correct_option:
                    new_correct_option = option_id
                    break
            else:
                new_correct_option = 'A'  # 預設值，應該不會發生
                
            # 顯示選項的文本內容
            options_display_texts = [option['text'] for option in options if option]
            if len(options_display_texts) < 3:
                # 如果選項不足三個，補充
                while len(options_display_texts) < 3:
                    options_display_texts.append("此選項不適用")
            
            # 保存遊戲狀態，包括新的選項順序和答案位置
            user_game_state[user_id] = {
                'false_potato_original': false_potato_text,
                'fraud_type_for_explanation': fraud_type,
                'custom_explanation': explanation,
                'option_A_text': options_display_texts[0],
                'option_B_text': options_display_texts[1],
                'option_C_text': options_display_texts[2] if len(options_display_texts) > 2 else "無選項C",
                'correct_option': new_correct_option,
                'using_predefined_options': True
            }
        else:
            # 題目沒有預設選項，使用原來的邏輯
            # 創建兩個明顯安全的訊息（真土豆）
            true_potato_texts = [
                "提醒您，銀行業務人員絕不會要求您提供網路銀行密碼或是ATM操作。如有任何疑問請撥打官方客服電話查詢，且務必親自撥打，不要使用對方提供的電話號碼。",
                "購物前請確認網站的安全性，選擇有https和安全認證的官方網站，並透過第三方支付或信用卡付款以獲得交易保障。遇到要求私下交易或要求先付款的賣家請特別小心。",
                "接到陌生來電宣稱您涉及刑案、洗錢，需要監管帳戶或轉帳操作，請立即掛斷。司法單位不會用電話要求您操作ATM或銀行帳戶。請撥打165反詐騙專線確認。",
                "網路投資前請查證平台合法性，任何宣稱「保證獲利」、「零風險高報酬」的投資都極可能是詐騙。合法投資管道不會要求您安裝特定APP或加入特定通訊軟體群組。",
                "保護個人資料安全，不隨意提供身分證字號、銀行帳號等資訊。對方如有要求購買遊戲點數、禮品卡，並要求提供卡號序號，幾乎都是詐騙行為。"
            ]
            
            # 從安全訊息中隨機選擇兩則
            selected_true_potatoes = random.sample(true_potato_texts, 2)
            
            # 打亂三個選項的順序
            options_display_texts = [false_potato_text] + selected_true_potatoes
            random.shuffle(options_display_texts)

            # 找出詐騙訊息在打亂後的位置
            correct_option = None
            for i, text in enumerate(options_display_texts):
                if text == false_potato_text:
                    if i == 0:
                        correct_option = 'A'
                    elif i == 1:
                        correct_option = 'B'
                    else:
                        correct_option = 'C'
                    break

            user_game_state[user_id] = {
                'false_potato_original': false_potato_text,
                'fraud_type_for_explanation': fraud_type,
                'custom_explanation': explanation,
                'option_A_text': options_display_texts[0],
                'option_B_text': options_display_texts[1],
                'option_C_text': options_display_texts[2],
                'correct_option': correct_option,
                'using_predefined_options': False
            }
    else:
        # 如果沒有預設題庫，則回退到從Firebase中獲取
        logger.warning("使用Firebase資料庫作為備選題目來源")
        report_data = firebase_manager.get_random_fraud_report_for_game()

        if not report_data:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="抱歉，目前題庫裡沒有題目了，稍後再試試吧！")
            )
            return

        # 詐騙訊息（假土豆）
        false_potato_text = report_data['message']
        fraud_type = report_data['fraud_type']
        explanation = ""
        
        # 創建兩個明顯安全的訊息（真土豆）
        true_potato_texts = [
            "提醒您，銀行業務人員絕不會要求您提供網路銀行密碼或是ATM操作。如有任何疑問請撥打官方客服電話查詢，且務必親自撥打，不要使用對方提供的電話號碼。",
            "購物前請確認網站的安全性，選擇有https和安全認證的官方網站，並透過第三方支付或信用卡付款以獲得交易保障。遇到要求私下交易或要求先付款的賣家請特別小心。",
            "接到陌生來電宣稱您涉及刑案、洗錢，需要監管帳戶或轉帳操作，請立即掛斷。司法單位不會用電話要求您操作ATM或銀行帳戶。請撥打165反詐騙專線確認。",
            "網路投資前請查證平台合法性，任何宣稱「保證獲利」、「零風險高報酬」的投資都極可能是詐騙。合法投資管道不會要求您安裝特定APP或加入特定通訊軟體群組。",
            "保護個人資料安全，不隨意提供身分證字號、銀行帳號等資訊。對方如有要求購買遊戲點數、禮品卡，並要求提供卡號序號，幾乎都是詐騙行為。"
        ]
        
        # 從安全訊息中隨機選擇兩則
        selected_true_potatoes = random.sample(true_potato_texts, 2)
        
        # 打亂三個選項的順序
        options_display_texts = [false_potato_text] + selected_true_potatoes
        random.shuffle(options_display_texts)

        # 找出詐騙訊息在打亂後的位置
        correct_option = None
        for i, text in enumerate(options_display_texts):
            if text == false_potato_text:
                if i == 0:
                    correct_option = 'A'
                elif i == 1:
                    correct_option = 'B'
                else:
                    correct_option = 'C'
                break

        user_game_state[user_id] = {
            'false_potato_original': false_potato_text,
            'fraud_type_for_explanation': fraud_type,
            'custom_explanation': explanation,
            'option_A_text': options_display_texts[0],
            'option_B_text': options_display_texts[1],
            'option_C_text': options_display_texts[2],
            'correct_option': correct_option,
            'using_predefined_options': False
        }

    flex_message_content = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='選哪顆土豆？🤔', weight='bold', size='xl', align='center', margin='md'),
                TextComponent(text='請指出下列哪一個選項「是詐騙訊息」（也就是假土豆）？', wrap=True, margin='lg', size='sm'),
                SeparatorComponent(margin='lg'),
                TextComponent(text='選項 A:', weight='bold', size='md', margin='lg'),
                TextComponent(text=user_game_state[user_id]['option_A_text'][:250] + '...' if len(user_game_state[user_id]['option_A_text']) > 250 else user_game_state[user_id]['option_A_text'], wrap=True, size='sm', margin='sm'),
                SeparatorComponent(margin='lg'),
                TextComponent(text='選項 B:', weight='bold', size='md', margin='lg'),
                TextComponent(text=user_game_state[user_id]['option_B_text'][:250] + '...' if len(user_game_state[user_id]['option_B_text']) > 250 else user_game_state[user_id]['option_B_text'], wrap=True, size='sm', margin='sm'),
                SeparatorComponent(margin='lg'),
                TextComponent(text='選項 C:', weight='bold', size='md', margin='lg'),
                TextComponent(text=user_game_state[user_id]['option_C_text'][:250] + '...' if len(user_game_state[user_id]['option_C_text']) > 250 else user_game_state[user_id]['option_C_text'], wrap=True, size='sm', margin='sm'),
            ]
        ),
        footer=BoxComponent(
            layout='vertical',
            spacing='sm',
            contents=[
                ButtonComponent(
                    style='primary',
                    color='#FF8C00', 
                    height='sm',
                    action=PostbackAction(label='選 A', data=f'action=potato_game_answer&chosen_option_id=A&uid={user_id}')
                ),
                ButtonComponent(
                    style='primary',
                    color='#FF8C00', 
                    height='sm',
                    action=PostbackAction(label='選 B', data=f'action=potato_game_answer&chosen_option_id=B&uid={user_id}')
                ),
                ButtonComponent(
                    style='primary',
                    color='#FF8C00', 
                    height='sm',
                    action=PostbackAction(label='選 C', data=f'action=potato_game_answer&chosen_option_id=C&uid={user_id}')
                )
            ]
        )
    )
    
    try:
        line_bot_api.reply_message(reply_token, FlexSendMessage(alt_text='選哪顆土豆？小遊戲', contents=flex_message_content))
    except Exception as e:
        logger.error(f"Error sending potato game question: {e}")
        line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，遊戲載入失敗，請稍後再試。"))


def handle_potato_game_answer(user_id, reply_token, data_params):
    """
    Handles the user's answer in the "選哪顆土豆" game.
    """
    global user_game_state
    chosen_option_id = data_params.get('chosen_option_id')

    if user_id not in user_game_state or 'false_potato_original' not in user_game_state[user_id]:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="糟糕，遊戲狀態好像不見了，麻煩您重新開始遊戲吧！"))
        return

    game_data = user_game_state[user_id]
    false_potato_original_text = game_data['false_potato_original']
    fraud_type_for_explanation = game_data['fraud_type_for_explanation']
    custom_explanation = game_data.get('custom_explanation', '')
    correct_option = game_data.get('correct_option')
    
    chosen_text = ""
    if chosen_option_id == 'A':
        chosen_text = game_data['option_A_text']
    elif chosen_option_id == 'B':
        chosen_text = game_data['option_B_text']
    elif chosen_option_id == 'C':
        chosen_text = game_data['option_C_text']
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="選擇出錯了，請重新玩一次哦。"))
        return

    reply_messages = []
    
    # 使用自訂解釋或從通用特徵庫獲取
    if custom_explanation:
        fraud_features = f"⚠️ 詐騙特徵說明：\n{custom_explanation}"
    else:
        fraud_features = get_fraud_features(fraud_type_for_explanation, false_potato_original_text)
    
    explanation_intro = f"這則訊息屬於【{fraud_type_for_explanation}】類型的詐騙手法。"
    explanation_detail = f"詐騙訊息：\n「{false_potato_original_text[:180]}...」" 

    # 判斷用戶是否選擇了正確的選項
    is_correct = chosen_option_id == correct_option
    
    if is_correct: 
        result_text = f"👍 恭喜答對了！您成功識別出詐騙訊息！\n\n{explanation_intro}\n\n{explanation_detail}\n\n{fraud_features}\n\n記住：提高警覺，保護自己和親友的資產安全！"
        reply_messages.append(TextSendMessage(text=result_text))
    else: 
        result_text = f"❌ 要小心！您選的不是詐騙訊息。\n\n{explanation_intro}\n\n正確答案是選項 {correct_option}：\n「{false_potato_original_text[:180]}...」\n\n{fraud_features}\n\n別灰心，透過練習您會越來越擅長識別詐騙！"
        reply_messages.append(TextSendMessage(text=result_text))

    quick_reply_items = QuickReply(items=[
        QuickReplyButton(action=PostbackAction(label="再玩一題", data=f'action=start_potato_game&uid={user_id}')),
        QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
        QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
    ])
    
    reply_messages.append(TextSendMessage(text="要不要再來一局，或是嘗試其他功能？", quick_reply=quick_reply_items))
    
    try:
        line_bot_api.reply_message(reply_token, messages=reply_messages)
    except Exception as e:
        logger.error(f"Error sending potato game answer reply: {e}")

def get_fraud_features(fraud_type, fraud_message):
    """
    根據詐騙類型提供典型詐騙特徵說明
    """
    common_features = "⚠️ 詐騙常見特徵：\n"
    
    # 根據詐騙類型添加特定特徵
    if "購物" in fraud_type:
        features = [
            "1. 要求私下交易或匯款到私人帳戶",
            "2. 急著成交，製造急迫感",
            "3. 價格明顯低於市場行情",
            "4. 要求使用非正規支付方式",
            "5. 賣家資訊模糊不清"
        ]
    elif "投資" in fraud_type or "理財" in fraud_type:
        features = [
            "1. 保證「穩賺不賠」、「高報酬、低風險」",
            "2. 聲稱有「內部資訊」或「獨家投資管道」",
            "3. 要求下載特定APP或加入特定群組",
            "4. 催促立即投資，聲稱「機會稍縱即逝」",
            "5. 要求將資金轉入「投資專戶」"
        ]
    elif "交友" in fraud_type:
        features = [
            "1. 短時間內迅速發展親密關係",
            "2. 自稱高社經地位但無法見面",
            "3. 編造各種理由請求金錢協助",
            "4. 聲稱有緊急醫療費用或意外事件",
            "5. 拒絕視訊通話或見面"
        ]
    elif "檢警" in fraud_type or "公務" in fraud_type:
        features = [
            "1. 聲稱您涉及刑案或洗錢",
            "2. 要求監管您的銀行帳戶",
            "3. 要求操作ATM或網銀",
            "4. 要求購買點數卡或禮品卡",
            "5. 警告不得向他人透露"
        ]
    elif "中獎" in fraud_type:
        features = [
            "1. 未參加也「中獎」",
            "2. 要求支付手續費、稅金才能領獎",
            "3. 使用模糊的活動辦法",
            "4. 通知管道可疑（如簡訊）",
            "5. 要求提供銀行帳號或個資"
        ]
    else:
        # 通用詐騙特徵
        features = [
            "1. 製造緊急感與恐慌",
            "2. 要求提供敏感個人資料",
            "3. 提出不合理或可疑的要求",
            "4. 語法錯誤或可疑連結",
            "5. 要求轉帳、匯款或購買點數"
        ]
    
    return common_features + "\n".join(features)

# --- End: Add these new functions ---

# 添加URL分析結果的Flex Message格式函數
def create_analysis_flex_message(analysis_data, display_name, message_to_analyze, user_id=None):
    """创建分析结果的Flex消息"""
    try:
        risk_level = analysis_data.get("risk_level", "未知風險")
        fraud_type = analysis_data.get("fraud_type", "未知類型")
        explanation = analysis_data.get("explanation", "")
        suggestions = analysis_data.get("suggestions", "")
    
        # URL相關信息
        original_url = analysis_data.get("original_url")
        expanded_url = analysis_data.get("expanded_url")
        is_short_url = analysis_data.get("is_short_url", False)
        url_expanded_successfully = analysis_data.get("url_expanded_successfully", False)
        
        # 解析分析理由和建議（如果是字符串，按行分割；如果已經是列表，直接使用）
        reasons = []
        if isinstance(explanation, str) and explanation.strip():
            reasons = [explanation.strip()]
        elif isinstance(explanation, list):
            reasons = [r for r in explanation if r and r.strip()]
        
        # 確保至少有一個預設的理由
        if not reasons:
            reasons = ["系統無法提供詳細分析理由，請謹慎判斷此內容。"]
            
        suggestion_list = []
        if isinstance(suggestions, str) and suggestions.strip():
            suggestion_list = [suggestions.strip()]
        elif isinstance(suggestions, list):
            suggestion_list = [s for s in suggestions if s and s.strip()]
            
        # 確保至少有一個預設的建議
        if not suggestion_list:
            suggestion_list = ["保持警惕，不要點擊可疑連結或提供個人敏感資訊。"]
        
        # 定義一個無限次數的指示值
        remaining_credits = "∞"  # 使用無限符號表示無限次數
        
        # 計算風險等級顏色和圖示
        if "低風險" in risk_level:
            risk_color = "#27AE60"  # 綠色
        risk_emoji = "✅"
        elif "中風險" in risk_level:
            risk_color = "#F39C12"  # 橙色
            risk_emoji = "⚠️"
        else:  # 高風險
            risk_color = "#E74C3C"  # 紅色
            risk_emoji = "🔴"
        
        # 檢查是否是贊助鏈接
        is_donation_link = False
        donation_url = ""
        for domain in SAFE_DOMAINS:
            if domain in message_to_analyze:
                is_donation_link = True
                
                # 提取完整URL，確保包含https://
                if "http://" in message_to_analyze or "https://" in message_to_analyze:
                    # 嘗試提取完整URL
                    import re
                    url_match = re.search(r'(https?://[^\s]+)', message_to_analyze)
                    if url_match:
                        donation_url = url_match.group(0)
    else:
                        donation_url = f"https://{domain}"
                else:
                    donation_url = f"https://{domain}"
                
                # 確保URL開頭是https://
                if not donation_url.startswith("https://"):
                    if donation_url.startswith("http://"):
                        donation_url = "https://" + donation_url[7:]
                    else:
                        donation_url = "https://" + donation_url
                
                logger.info(f"找到贊助鏈接: {donation_url}")
                break
        
        # 截斷過長的分析消息
        if len(message_to_analyze) > 50:
            short_message = message_to_analyze[:47] + "..."
        else:
            short_message = message_to_analyze
            
        # 構建內容區域
        contents = []
        
        # 添加風險等級
        contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": f"{risk_emoji} 風險等級",
                    "size": "md",
                    "color": "#555555",
                    "flex": 0
                },
                {
                    "type": "text",
                    "text": risk_level or "未知",  # 確保不為空
                    "size": "md",
                    "color": risk_color,
                    "weight": "bold",
                    "align": "end"
                }
            ]
        })
        
        # 添加詐騙類型
        contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": "🔍 詐騙類型",
                    "size": "md",
                    "color": "#555555",
                    "flex": 0
                },
                {
                    "type": "text",
                    "text": fraud_type or "未分類",  # 確保不為空
                    "size": "md",
                    "color": "#555555",
                    "align": "end"
                }
            ],
            "margin": "md"
        })
        
        # 添加分隔線
        contents.append({
            "type": "separator",
            "margin": "md"
        })
        
        # 顯示分析的URL信息
        if original_url:
            contents.append({
                "type": "text",
                "text": "🌐 檢測的網址",
                "weight": "bold",
                "margin": "lg",
                "size": "md",
                "color": "#1DB446"
            })
            
            # 顯示原始URL (可能是短網址)
            url_display = original_url
            if len(url_display) > 45:
                url_display = url_display[:42] + "..."
                
            contents.append({
                "type": "text",
                "text": url_display,
                "size": "sm",
                "margin": "md",
                "color": "#333333",
                "wrap": True
            })
            
            # 如果是短網址且成功展開，顯示展開後的URL
            if is_short_url and url_expanded_successfully and expanded_url != original_url:
                contents.append({
                    "type": "text",
                    "text": "👉 展開後的完整網址",
                    "weight": "bold",
                    "margin": "md",
                    "size": "sm",
                    "color": "#555555"
                })
                
                expanded_url_display = expanded_url
                if len(expanded_url_display) > 45:
                    expanded_url_display = expanded_url_display[:42] + "..."
                    
                contents.append({
                    "type": "text",
                    "text": expanded_url_display,
                    "size": "sm",
                    "margin": "sm",
                    "color": "#333333",
                    "wrap": True
                })
                
            # 如果是短網址但無法展開，顯示警告
            elif is_short_url and not url_expanded_successfully:
                contents.append({
                    "type": "text",
                    "text": "⚠️ 這是短網址，但無法查看它會連到哪裡",
                    "size": "sm",
                    "margin": "md",
                    "color": "#E74C3C",
                    "weight": "bold",
                    "wrap": True
                })
            
            contents.append({
                "type": "separator",
                "margin": "md"
            })
        
        # 如果是贊助鏈接，添加特殊感謝信息
        if is_donation_link:
            contents.append({
                "type": "text",
                "text": "🙏 感謝您的支持",
                "weight": "bold",
                "margin": "md",
                "size": "md",
                "color": "#1DB446"
            })
            
            contents.append({
                "type": "text",
                "text": "您的贊助將幫助我們提供更優質的防詐騙服務，持續改進AI分析能力！",
                "size": "sm",
                "margin": "md",
                "color": "#333333",
                "wrap": True
            })
            
            # 確保URL格式正確
            if donation_url:
                logger.info(f"贊助按鈕使用URL: {donation_url}")
                contents.append({
                    "type": "button",
                    "style": "primary",
                    "action": {
                        "type": "uri",
                        "label": "立即贊助",
                        "uri": donation_url
                    },
                    "margin": "md",
                    "color": "#FF8C00"
                })
            
            contents.append({
                "type": "separator",
                "margin": "md"
            })
            
        # 添加分析理由標題
        contents.append({
            "type": "text",
            "text": "📋 分析理由",
            "weight": "bold",
            "margin": "md",
            "size": "md",
            "color": "#1DB446"
        })
        
        # 添加分析理由 (確保每個項目都不為空)
        for reason in reasons:
            if reason and reason.strip():  # 確保理由不為空
                contents.append({
                    "type": "text",
                    "text": reason,
                    "size": "sm",
                    "margin": "md",
                    "color": "#333333",
                    "wrap": True
                })
        
        # 添加防範建議標題
        contents.append({
            "type": "text",
            "text": "🛡️ 防範建議",
            "weight": "bold",
            "margin": "md",
            "size": "md",
            "color": "#1DB446"
        })
        
        # 添加防範建議 (確保每個項目都不為空)
        for suggestion in suggestion_list:
            if suggestion and suggestion.strip():  # 確保建議不為空
                contents.append({
                    "type": "text",
                    "text": suggestion,
                    "size": "sm",
                    "margin": "md",
                    "color": "#666666",
                    "wrap": True
                })
        
        # 添加固定的提示文字
        contents.append({
            "type": "box",
            "layout": "vertical",
            "margin": "lg",
            "contents": [
                {
                    "type": "separator",
                    "color": "#DDDDDD",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": "⚠️如有任何疑慮，請直接撥打165反詐騙專線",
                    "wrap": True,
                    "size": "xs",
                    "margin": "md",
                    "color": "#999999"
                },
                {
                    "type": "text",
                    "text": "本系統僅針對內容做初步分析，請自行評估結果",
                    "wrap": True,
                    "size": "xs",
                    "margin": "sm",
                    "color": "#999999"
                }
            ]
        })
        
        # 如果有新型詐騙特征，添加标记
        if "is_emerging" in analysis_data and analysis_data["is_emerging"]:
            contents.append({
                "type": "text",
                "text": "🆕 可能是新型詐騙手法",
                "size": "sm",
                "margin": "md",
                "color": "#ffffff",
                "background": "#FF0000"
            })
        
        # 驗證所有text字段是否有內容
        for i, content in enumerate(contents):
            if content.get("type") == "text" and (not content.get("text") or content.get("text").strip() == ""):
                logger.warning(f"檢測到第{i}個元素的text字段為空，設置為預設值")
                content["text"] = "無相關內容"  # 設置預設值
            elif content.get("type") == "box" and "contents" in content:
                for j, sub_content in enumerate(content["contents"]):
                    if sub_content.get("type") == "text" and (not sub_content.get("text") or sub_content.get("text").strip() == ""):
                        logger.warning(f"檢測到第{i}個box的第{j}個元素的text字段為空，設置為預設值")
                        sub_content["text"] = "無相關內容"  # 設置預設值
            # 檢查其他可能有URI的部分
            elif content.get("type") == "button" and "action" in content:
                action = content["action"]
                if action.get("type") == "uri" and "uri" in action:
                    uri = action["uri"]
                    # 確保URI包含https://
                    if not uri.startswith("https://"):
                        logger.warning(f"檢測到URI不符合規範: {uri}，修正為https://")
                        if uri.startswith("http://"):
                            action["uri"] = "https://" + uri[7:]
                        else:
                            action["uri"] = "https://" + uri
        
        # 创建FlexSendMessage
        flex_message = FlexSendMessage(
            alt_text=f"詐騙風險分析：{risk_level}",
            contents={
                "type": "bubble",
                "size": "mega",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"{risk_emoji} 詐騙風險：{risk_level}",
                                    "color": "#ffffff",
                                    "weight": "bold",
                                    "size": "xl"
                                }
                            ]
                        }
                    ],
                    "backgroundColor": risk_color,
                    "paddingAll": "20px"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": contents,
                    "paddingAll": "20px"
                }
            }
        )
        
        return flex_message
    except Exception as e:
        logger.error(f"Error creating analysis flex message: {e}")
        # 返回一個簡單的文本消息作為備用
        return TextSendMessage(text=f"分析結果：{risk_level}\n\n詐騙類型：{fraud_type}\n\n{explanation}\n\n請注意風險，如有疑慮請撥打165反詐騙專線。")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
        
    return 'OK'

@app.route("/", methods=['GET'])
def home():
    return "Line Bot Anti-Fraud is running!"

@app.route("/fraud-statistics", methods=['GET'])
def fraud_statistics():
    """顯示詐騙統計數據頁面"""
    stats = firebase_manager.get_fraud_statistics()
    return render_template('statistics.html', stats=stats)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    profile = get_user_profile(user_id)
    display_name = profile.display_name if profile else "未知用戶"
    text_message = event.message.text
    reply_token = event.reply_token
    current_time = datetime.datetime.now()

    logger.info(f"Received message from {display_name} ({user_id}): {text_message}")

    # 檢查是否為群組訊息
    is_group_message = False
    group_id = None
    if hasattr(event.source, "type") and event.source.type in ["group", "room"]:
        is_group_message = True
        group_id = event.source.group_id if event.source.type == "group" else event.source.room_id
        logger.info(f"這是一則群組訊息 (類型: {event.source.type}, ID: {group_id})")
        
    # 更新用戶狀態
    current_state = user_conversation_state.get(user_id, {})
    current_state["last_time"] = current_time
    
    # 檢查是否包含觸發關鍵詞 "嗨土豆"或者用戶處於等待分析狀態
    waiting_for_analysis = current_state.get("waiting_for_analysis", False)
    
    # 如果是群組訊息，需要檢查是否包含觸發關鍵詞，或者用戶處於等待分析狀態
    if is_group_message and bot_trigger_keyword not in text_message and not waiting_for_analysis:
        logger.info(f"群組訊息不包含觸發關鍵詞 '{bot_trigger_keyword}'，也不在等待分析狀態，忽略此訊息")
        return

    # 如果是群組訊息且包含觸發關鍵詞，移除關鍵詞以處理實際命令
    if is_group_message and bot_trigger_keyword in text_message:
        text_message = text_message.replace(bot_trigger_keyword, "").strip()
        logger.info(f"移除觸發關鍵詞後的訊息: {text_message}")
    
    # 如果上一次的互動是請求分析，則設置等待分析狀態
    if any(text_message.strip() == prompt or text_message.strip() == prompt.rstrip("：") for prompt in analysis_prompts):
        current_state["waiting_for_analysis"] = True
        user_conversation_state[user_id] = current_state
        logger.info(f"用戶 {user_id} 進入等待分析狀態")
    elif any(pattern in text_message.lower() for pattern in follow_up_patterns):
        current_state["waiting_for_analysis"] = True
        user_conversation_state[user_id] = current_state
        logger.info(f"用戶 {user_id} 可能遇到詐騙，進入等待分析狀態")
    elif contains_url(text_message) and waiting_for_analysis:
        # 如果消息包含URL且用戶處於等待分析狀態，保持等待分析狀態
        current_state["waiting_for_analysis"] = True
        user_conversation_state[user_id] = current_state
        logger.info(f"用戶 {user_id} 提供了URL，保持等待分析狀態")
    elif waiting_for_analysis and should_perform_fraud_analysis(text_message):
        # 用戶處於等待分析狀態且這個消息看起來是需要分析的內容
        current_state["waiting_for_analysis"] = False  # 分析完後重置狀態
        user_conversation_state[user_id] = current_state
        logger.info(f"用戶 {user_id} 在等待分析狀態下發送了需要分析的內容")
    else:
        # 其他情況，重置等待分析狀態
        current_state["waiting_for_analysis"] = False
        user_conversation_state[user_id] = current_state
    
    # 如果移除關鍵詞後訊息為空，則發送功能說明
    if not text_message:
        reply_text = f"您好！我是防詐騙小幫手，我的功能包括：\n\n" \
                        f"1️⃣ 詐騙風險分析：我可以分析您收到的可疑訊息，評估是否為詐騙\n\n" \
                        f"2️⃣ 詐騙類型查詢：您可以輸入「詐騙類型列表」查看各種常見詐騙\n\n" \
                        f"3️⃣ 「選哪顆土豆」小遊戲：通過遊戲學習辨識詐騙訊息\n\n" \
                        f"請選擇您想嘗試的功能："
            
        # 如果在群組中，QuickReply按鈕需要包含觸發關鍵詞
        if is_group_message:
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="分析可疑訊息", text=f"{bot_trigger_keyword} 請幫我分析這則訊息：")),
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text=f"{bot_trigger_keyword} 詐騙類型列表"))
            ])
            # 在群組中使用mention功能
            mention_message = create_mention_message(reply_text, display_name, user_id, quick_reply)
            line_bot_api.reply_message(reply_token, mention_message)
        else:
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
            ])
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
        
        firebase_manager.save_user_interaction(user_id, display_name, text_message, "回覆功能說明", is_fraud_related=False)
            return

    # 處理「選哪顆土豆」遊戲觸發
    if any(keyword in text_message.lower() for keyword in potato_game_trigger_keywords):
        logger.info(f"User {user_id} triggered potato game.")
        firebase_manager.save_user_interaction(
            user_id, display_name, text_message, 
            "啟動「選哪顆土豆」遊戲", is_fraud_related=False
        )
        send_potato_game_question(user_id, reply_token)
        return

    # 處理詐騙類型列表查詢
    if text_message.lower() == "詐騙類型列表" or text_message.lower() == "詐騙類型":
        logger.info(f"User {user_id} is querying fraud types list")
        types_text = "目前已收集的詐騙類型有：\n"
        for f_type, info in fraud_types.items():
            types_text += f"\n⚠️ {f_type}：\n{info['description']}\n"
        
        types_text += "\n想了解特定類型，可以問我「什麼是[詐騙類型]」喔！"

        quick_reply_items = []
        for f_type in list(fraud_types.keys())[:4]:  # 只取前4個詐騙類型作為快速回覆
            if is_group_message:
                quick_reply_items.append(QuickReplyButton(action=MessageAction(label=f_type, text=f"{bot_trigger_keyword} 什麼是{f_type}")))
            else:
            quick_reply_items.append(QuickReplyButton(action=MessageAction(label=f_type, text=f"什麼是{f_type}")))

        # 在群組中回覆時前綴用戶名稱
        if is_group_message:
            mention_message = create_mention_message(types_text, display_name, user_id, 
                QuickReply(items=quick_reply_items) if quick_reply_items else None)
            line_bot_api.reply_message(reply_token, mention_message)
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=types_text, 
                quick_reply=QuickReply(items=quick_reply_items) if quick_reply_items else None))
        
        firebase_manager.save_user_interaction(user_id, display_name, text_message, "Provided list of fraud types", is_fraud_related=False)
        return
        
    # 處理特定詐騙類型資訊查詢 (例如 "什麼是網路購物詐騙")
    specific_type_query_match = re.match(r"^(什麼是|查詢|我想了解|我想知道)(.+詐騙)$", text_message.strip())
    if specific_type_query_match:
        query_type = specific_type_query_match.group(2).strip()
        logger.info(f"User {user_id} is querying about specific fraud type: {query_type}")
        
        matched_fraud_type = None
        for f_type, info in fraud_types.items():
            if query_type in f_type or f_type in query_type:
                matched_fraud_type = f_type
                break
        
        if matched_fraud_type:
            info = fraud_types[matched_fraud_type]
            response_text = f"⚠️ {matched_fraud_type} ⚠️\n\n{info['description']}\n\n"
            
            if info.get('examples') and len(info['examples']) > 0:
                response_text += "📋 案例：\n" + info['examples'][0] + "\n\n"
            
            if info.get('sop') and len(info['sop']) > 0:
                response_text += "🛡️ 防範方法：\n" + "\n".join(info['sop'][:5]) + "\n"
            
            if is_group_message:
                mention_message = create_mention_message(response_text, display_name, user_id, 
                    QuickReply(items=[
                        QuickReplyButton(action=MessageAction(label="查看其他詐騙類型", text=f"{bot_trigger_keyword} 詐騙類型列表")),
                        QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆")),
                        QuickReplyButton(action=MessageAction(label="分析可疑訊息", text=f"{bot_trigger_keyword} 請幫我分析這則訊息："))
                    ])
                )
                line_bot_api.reply_message(reply_token, mention_message)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text, 
                    quick_reply=QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="查看其他詐騙類型", text="詐騙類型列表")),
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息："))
                    ])))
            
            firebase_manager.save_user_interaction(user_id, display_name, text_message, f"Provided info about {matched_fraud_type}", is_fraud_related=False)
            return
        else:
            # 未找到匹配的詐騙類型，給出一般性回覆
            response_text = f"抱歉，我目前沒有關於「{query_type}」的詳細資訊。\n\n以下是我已收集的詐騙類型，您可以查詢這些："
            for f_type in fraud_types.keys():
                response_text += f"\n- {f_type}"
            
            if is_group_message:
                mention_message = create_mention_message(response_text, display_name, user_id, 
                    QuickReply(items=[
                        QuickReplyButton(action=MessageAction(label="查看詐騙類型列表", text=f"{bot_trigger_keyword} 詐騙類型列表")),
                        QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆"))
                    ])
                )
                line_bot_api.reply_message(reply_token, mention_message)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text, 
                    quick_reply=QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="查看詐騙類型列表", text="詐騙類型列表")),
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆"))
                    ])))
            
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "Responded to unknown fraud type query", is_fraud_related=False)
            return

    # 檢查是否為請求分析的提示語
    if any(text_message.strip() == prompt or text_message.strip() == prompt.rstrip("：") for prompt in analysis_prompts):
        logger.info(f"User {user_id} requested message analysis but didn't provide message content")
        
        # 使用隨機回覆，讓機器人回應更加多樣化
        prompt_replies = [
            f"{display_name}，您好！請將可疑的訊息或網址貼給我，我會馬上分析是否有詐騙風險。可以是陌生人傳來的連結、可疑的購物網站，或任何讓您不安的訊息。",
            f"好的，{display_name}！想知道某個網址或訊息是否安全？請直接貼上來，我會立刻為您檢查風險。無論是社群媒體連結、購物網站還是奇怪的訊息都可以。",
            f"沒問題，{display_name}！要分析什麼訊息或網址呢？請完整複製貼上您想查證的內容，像是陌生來電要求的操作、可疑網址或社群媒體訊息都可以。",
            f"收到！{display_name}，請直接將您懷疑的訊息或網址複製給我，特別是含有連結、要求個人資料或提到錢的訊息，我會立刻幫您辨識風險。"
        ]
        
        selected_reply = random.choice(prompt_replies)
        
        if is_group_message:
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text=f"{bot_trigger_keyword} 詐騙類型列表"))
            ])
            # 在群組中使用mention功能
            mention_message = create_mention_message(selected_reply, display_name, user_id, quick_reply)
            line_bot_api.reply_message(reply_token, mention_message)
        else:
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
            QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
        ])
            line_bot_api.reply_message(reply_token, TextSendMessage(text=selected_reply, quick_reply=quick_reply))
        
        firebase_manager.save_user_interaction(user_id, display_name, text_message, "Responded to analysis request prompt", is_fraud_related=False)
        return

    # 檢查訊息是否包含URL
    def contains_url(text):
        # 一個簡單的URL檢測正則表達式
        url_pattern = re.compile(r'https?://\S+|www\.\S+|\S+\.\w{2,}(/\S*)?')
        return bool(url_pattern.search(text))

    # 檢查是否需要對消息進行詐騙分析的邏輯
    def should_perform_fraud_analysis(text_message):
        # 1. 先检查是否是次数查询，避免这类消息被分析
        if any(keyword in text_message.lower() for keyword in ["剩余次数", "剩餘次數", "查詢次數", "查询次数", "還有幾次", "还有几次", "剩下幾次", "剩下几次", "幾次機會", "几次机会", "幾次分析", "几次分析"]):
            return False
            
        # 2. 直接檢查是否含有URL，如果有優先分析
        if contains_url(text_message):
            logger.info(f"訊息中含有URL，將進行詐騙分析")
            return True
            
        # 3. 檢查是否包含常見問候詞
        common_greetings = ["你好", "嗨", "哈囉", "嘿", "hi", "hello", "hey", "早安", "午安", "晚安"]
        if text_message.lower() in common_greetings or (len(text_message) <= 5 and any(greeting in text_message.lower() for greeting in common_greetings)):
            return False
            
        # 4. 檢查是否是功能相關指令
        if any(keyword in text_message.lower() for keyword in function_inquiry_keywords + potato_game_trigger_keywords) or "詐騙類型" in text_message:
            return False
            
        # 5. 檢查是否是跟踪模式的問句
        if any(pattern in text_message.lower() for pattern in follow_up_patterns):
            return True
            
        # 6. 檢查是否是請求分析的明顯特徵
        analysis_indicators = ["幫我分析", "幫忙看看", "這是不是詐騙", "這是真的嗎", "這可靠嗎", "分析一下", "這樣是詐騙嗎"]
        if any(indicator in text_message for indicator in analysis_indicators):
            return True
            
        # 7. 檢查是否包含特定詐騙相關關鍵詞
        # 只有使用者明確表示需要分析，或者文本包含多個詐騙關鍵詞才進行分析
        fraud_related_keywords = ["詐騙", "被騙", "騙子", "可疑", "轉帳", "匯款", "銀行帳號", "個資", "身份證", "密碼", 
                                "通知", "中獎", "貸款", "投資", "急需", "幫我處理", "急用", "解除設定", "提款卡", 
                                "監管帳戶", "解凍", "安全帳戶", "簽證", "保證金", "違法", "洗錢", "警察", "檢察官"]
                                
        # 要求至少包含兩個詐騙相關關鍵詞
        keyword_count = sum(1 for keyword in fraud_related_keywords if keyword in text_message)
        if keyword_count >= 2:
            return True
            
        # 8. 預設不進行詐騙分析，將訊息作為一般閒聊處理
        return False

    # 預設使用ChatGPT進行閒聊回應或詐騙分析
    logger.info(f"Message from {user_id}: {text_message} - Determining if fraud analysis is needed")
    
    # 判斷是否需要進行詐騙分析
    if should_perform_fraud_analysis(text_message):
        logger.info(f"Performing fraud analysis for message from {user_id}: {text_message}")
        # 使用現有的詐騙分析邏輯，傳入user_id
        analysis_result = detect_fraud_with_chatgpt(text_message, display_name, user_id)
        
        if analysis_result and analysis_result.get("success", False):
            analysis_data = analysis_result.get("result", {})
            raw_result = analysis_result.get("raw_result", "")

        risk_level = analysis_data.get("risk_level", "不確定")
        fraud_type = analysis_data.get("fraud_type", "未知")
        explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
        suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
        is_emerging = analysis_data.get("is_emerging", False)

        # 創建並發送Flex Message分析結果
            flex_message = create_analysis_flex_message(analysis_data, display_name, text_message, user_id)
            
            # 在群組中增加前綴提及用戶
            if is_group_message and flex_message and isinstance(flex_message, FlexSendMessage):
                # 使用官方的mention功能發送前綴通知
                mention_message = create_mention_message("以下是您要求的詐騙風險分析：", display_name, user_id)
                line_bot_api.push_message(group_id if group_id else user_id, mention_message)
                
            # 發送Flex消息
            if flex_message:
        line_bot_api.reply_message(reply_token, flex_message)
            else:
                # 如果Flex消息創建失敗，發送基本文本消息
                text_response = f"風險等級：{risk_level}\n詐騙類型：{fraud_type}\n\n分析：{explanation}\n\n建議：{suggestions}"
                if is_group_message:
                    mention_message = create_mention_message(text_response, display_name, user_id)
                    line_bot_api.reply_message(reply_token, mention_message)
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=text_response))

        if is_emerging and fraud_type != "非詐騙相關":
            # 新增詐騙手法記錄通知改為單獨推送，避免混淆Flex Message
            emerging_text = "⚠️ 這可能是一種新的詐騙手法，我已經記錄下來了，謝謝您的資訊！"
                if is_group_message:
                    mention_message = create_mention_message(emerging_text, display_name, user_id)
                    line_bot_api.push_message(group_id if group_id else user_id, mention_message)
        else:
                    line_bot_api.push_message(user_id, TextSendMessage(text=emerging_text))
                firebase_manager.save_emerging_fraud_report(user_id, display_name, text_message, raw_result)
            
            is_fraud_related = True if fraud_type != "非詐騙相關" and risk_level not in ["無風險", "低"] else False
            
        # 保存互動記錄到Firebase
        firebase_manager.save_user_interaction(
                user_id, display_name, text_message, raw_result,
            is_fraud_related=is_fraud_related,
            fraud_type=fraud_type if is_fraud_related else None,
            risk_level=risk_level if is_fraud_related else None
        )
            
            # 以15%的機率顯示贊助信息
            if random.random() < 0.15:
                logger.info(f"隨機觸發贊助信息顯示給用戶 {user_id}")
                try:
                    # 延遲1秒發送，避免訊息堆疊
                    time.sleep(1)
                    donation_message = create_donation_flex_message()
                    # 使用push_message而不是reply_message
                    line_bot_api.push_message(group_id if is_group_message else user_id, donation_message)
                except Exception as e:
                    logger.error(f"發送贊助訊息時發生錯誤: {e}")
        else:
            # 分析失敗的情況，發送錯誤消息
            error_message = analysis_result.get("message", "分析失敗，請稍後再試") if analysis_result else "分析失敗，請稍後再試"
            if is_group_message:
                mention_message = create_mention_message(error_message, display_name, user_id)
                line_bot_api.reply_message(reply_token, mention_message)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=error_message))
            
        return
    else:
        # 使用ChatGPT進行閒聊回應
        logger.info(f"Using chat response for message from {user_id}: {text_message}")
        
        try:
            # 獲取用戶最近的對話歷史
            recent_history = firebase_manager.get_recent_interactions(user_id, limit=5)
            
            # 準備對話歷史消息列表
            chat_history = []
            
            # 系統提示消息
            system_message = {
                "role": "system", 
                "content": "你是一位名為「土豆」的AI聊天機器人，你的風格友善、溫暖且貼心。你需要根據之前的對話歷史來回應用戶，提供連貫且自然的對話體驗。你是防詐騙專家，當用戶討論可疑訊息時，要保持警覺。"
            }
            
            # 如果成功獲取到歷史對話，則使用它們
            if recent_history:
                # 將歷史對話轉換為ChatGPT格式
                for interaction in recent_history:
                    # 用戶消息
                    if 'message' in interaction and interaction['message']:
                        chat_history.append({
                            "role": "user",
                            "content": interaction['message']
                        })
                    
                    # 機器人回應
                    if 'response' in interaction and interaction['response']:
                        chat_history.append({
                            "role": "assistant",
                            "content": interaction['response']
                        })
                
                logger.info(f"成功使用用戶歷史對話: {len(chat_history)} 條消息")
            else:
                # 如果沒有歷史對話或發生錯誤，使用空的歷史
                logger.info("無法獲取用戶歷史對話，使用空歷史")
            
            # 添加當前用戶消息
            current_user_message = {
                "role": "user",
                "content": text_message
            }
            
            # 構建完整的消息列表
            messages = [system_message] + chat_history + [current_user_message]
            
            # 限制消息數量，避免超出API限制
            if len(messages) > 10:
                # 保留系統消息和最近的對話
                messages = [system_message] + messages[-9:]
            
            logger.info(f"使用記憶功能，總共提供 {len(messages)} 條消息給ChatGPT")
            
            # 使用更新後的OpenAI API格式
            chat_response = openai.chat.completions.create(
                model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            
            chat_reply = chat_response.choices[0].message.content.strip()
            
            # 只在首次聊天時添加功能介紹
            is_first_time = user_id not in first_time_chatters
            if is_first_time:
                first_time_chatters.add(user_id)
                introduction = f"\n\n我是防詐騙機器人「土豆」，能幫您：\n1️⃣ 分析可疑訊息\n2️⃣ 測試您的防詐騙能力\n3️⃣ 查詢各類詐騙手法"
                reply_text = chat_reply + introduction
            else:
                reply_text = chat_reply
            
            # 在群組中添加前綴
            if is_group_message:
                mention_message = create_mention_message(reply_text, display_name, user_id, quick_reply)
                line_bot_api.reply_message(reply_token, mention_message)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
            
            is_fraud_related = False
            
        except Exception as e:
            logger.error(f"閒聊回應錯誤: {e}")
            # 如果閒聊回應失敗，使用簡單的問候
            greetings = ["您好！", "嗨！", "哈囉！", "很高興見到您！", "您好呀！"]
            
            # 只在首次聊天時添加功能介紹
            is_first_time = user_id not in first_time_chatters
            if is_first_time:
                first_time_chatters.add(user_id)
                reply_text = f"{random.choice(greetings)}有什麼我能幫您的嗎？您可以輸入「功能」來了解我能做什麼。"
            else:
                reply_text = f"{random.choice(greetings)}有什麼我能幫您的嗎？"
            
            # 在群組中添加前綴
            if is_group_message:
                mention_message = create_mention_message(reply_text, display_name, user_id, quick_reply)
                line_bot_api.reply_message(reply_token, mention_message)
            
            is_fraud_related = False
    
    # 添加功能按鈕到所有回覆
    if is_group_message:
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="分析可疑訊息", text=f"{bot_trigger_keyword} 請幫我分析這則訊息：")),
            QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text=f"{bot_trigger_keyword} 選哪顆土豆")),
            QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text=f"{bot_trigger_keyword} 詐騙類型列表"))
        ])
    else:
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
        QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
        QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
    ])
    
    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
    
    # 保存互動記錄到Firebase
    firebase_manager.save_user_interaction(
        user_id, display_name, text_message, reply_text,
        is_fraud_related=is_fraud_related,
        fraud_type=None,
        risk_level=None
    )

@handler.add(PostbackEvent)
def handle_postback(event):
    """处理PostbackEvent（按钮点击等）"""
    try:
        data = event.postback.data
    reply_token = event.reply_token
        user_id = event.source.user_id
        
        # 获取用户显示名称
        user_profile = get_user_profile(user_id)
        display_name = user_profile.display_name if user_profile else '朋友'
    
        logger.info(f"接收到來自用戶 {user_id} 的 Postback: {data}")
    
        # 解析 data 参数
        data_parts = data.split('&')
        data_params = {}
        
        for part in data_parts:
            if '=' in part:
                key, value = part.split('=', 1)
                data_params[key] = value
        
        # 获取 action 参数
        action = data_params.get('action', '')
        
        # 根据 action 参数处理不同的按钮点击
        
        # 处理土豆游戏答案 - 修复action名称不匹配问题
    if action == 'potato_game_answer':
        handle_potato_game_answer(user_id, reply_token, data_params)
        return
        
        # 处理新游戏请求
    elif action == 'start_potato_game':
            send_potato_game_question(user_id, reply_token)
            return
        
        # 处理观看广告（暫時停用）
        elif action == 'view_ad':
            # 已暫停廣告功能，直接給用戶次數
            firebase_manager.increase_user_analysis_credits(user_id, amount=5)
            current_credits = firebase_manager.get_user_analysis_credits(user_id)
            
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=f"感謝您的支持！系統已為您增加5次分析機會，目前全面開放免費無限使用。")
            )
            
            # 記錄互動
        firebase_manager.save_user_interaction(
                user_id, display_name, "請求免費分析次數", 
                "已給予5次分析次數，現已開放免費無限使用", 
                is_fraud_related=False
        )
        return
    
        # 处理赞助
        elif action == 'donate':
            amount = data_params.get('amount', 'small')
            
            # 根据赞助金额增加用户分析次数
            credits_to_add = 0
            donation_amount = "未知"
            
            if amount == 'small':
                credits_to_add = 10
                donation_amount = "NT$50"
            elif amount == 'medium':
                credits_to_add = 30
                donation_amount = "NT$100"
            elif amount == 'large':
                credits_to_add = 100
                donation_amount = "NT$250"
            
            firebase_manager.increase_user_analysis_credits(user_id, amount=credits_to_add)
            
            # 获取用户当前分析次数
            current_credits = firebase_manager.get_user_analysis_credits(user_id)
            
            # 发送确认消息 (修改為感謝支持的消息)
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=f"感謝您的{donation_amount}贊助！您已獲得{credits_to_add}次分析機會。感謝支持，目前系統已開放免費無限使用。")
            )
            
            # 记录互动
            firebase_manager.save_user_interaction(
                user_id, display_name, f"贊助:{amount}", 
                f"用戶贊助{donation_amount}獲得{credits_to_add}次分析次數", 
                is_fraud_related=False
            )
            return

    except Exception as e:
        logger.error(f"處理 Postback 事件時發生錯誤: {e}")
        line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，處理 Postback 事件時出現錯誤。請稍後再試一次。"))

# 載入詐騙題庫
POTATO_GAME_QUESTIONS_DB = os.path.join(os.path.dirname(__file__), "potato_game_questions.json")
potato_game_questions = []

def load_potato_game_questions():
    global potato_game_questions
    try:
        # 記錄載入前的路徑信息
        file_path = os.path.abspath(POTATO_GAME_QUESTIONS_DB)
        logger.info(f"嘗試從路徑讀取題庫文件: {file_path}")
        logger.info(f"當前工作目錄: {os.getcwd()}")
        
        # 檢查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            potato_game_questions = []
            return
            
        with open(POTATO_GAME_QUESTIONS_DB, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 處理不同的JSON結構
            all_questions = []
            
            if isinstance(data, dict) and "questions" in data:
                # 處理頂層questions
                top_questions = data.get("questions", [])
                
                for q in top_questions:
                    # 檢查是否有嵌套的questions數組
                    if isinstance(q, dict) and "questions" in q:
                        # 將嵌套的questions添加到總題庫
                        nested_questions = q.get("questions", [])
                        all_questions.extend(nested_questions)
                        logger.info(f"發現嵌套題目：{len(nested_questions)}題")
                    else:
                        # 將頂層題目添加到總題庫
                        all_questions.append(q)
            
            potato_game_questions = all_questions
            
        # 確認文件內容
        first_three_questions = []
        for i, q in enumerate(potato_game_questions[:3]):
            first_three_questions.append(f"題目ID: {q.get('id')}, 詐騙類型: {q.get('fraud_type')}")
            
        logger.info(f"成功從 {POTATO_GAME_QUESTIONS_DB} 加載詐騙題庫，共 {len(potato_game_questions)} 道題目")
        logger.info(f"前三個題目: {', '.join(first_three_questions)}")
        logger.info(f"題庫中選項信息: 有預設選項的題目數量: {sum(1 for q in potato_game_questions if 'options' in q and q['options'] and 'correct_option' in q)}")
    except FileNotFoundError:
        logger.warning(f"詐騙題庫文件 {POTATO_GAME_QUESTIONS_DB} 未找到。")
        potato_game_questions = []
    except json.JSONDecodeError:
        logger.error(f"解析詐騙題庫文件 {POTATO_GAME_QUESTIONS_DB} 失敗。")
        potato_game_questions = []
    except Exception as e:
        logger.error(f"加載詐騙題庫時發生未知錯誤: {e}")
        potato_game_questions = []

load_fraud_tactics()
load_potato_game_questions()  # 加載題庫

if __name__ == "__main__":
    # 確保在服務啟動時重新加載題庫
    load_fraud_tactics()
    load_potato_game_questions()
    
    # 打印題庫加載結果
    logger.info(f"服務啟動時載入題庫：potato_game_questions 包含 {len(potato_game_questions)} 道題目")
    logger.info(f"題庫中有選項的題目數量: {sum(1 for q in potato_game_questions if 'options' in q and q['options'] and 'correct_option' in q)}")
    if potato_game_questions:
        logger.info(f"題庫路徑: {os.path.abspath(POTATO_GAME_QUESTIONS_DB)}")
        logger.info(f"工作目錄: {os.getcwd()}")
        
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 

@app.route("/watch-ad/<user_id>", methods=['GET'])
def watch_ad(user_id):
    """显示Unity广告的页面"""
    return render_template('watch_ad.html', user_id=user_id)

@app.route("/watch-ad", methods=['GET'])
def watch_ad_without_id():
    """处理LIFF重定向请求"""
    # 从LIFF获取用户ID，如果没有则返回通用页面
    return render_template('watch_ad.html')

@app.route("/ad-completed", methods=['POST'])
def ad_completed():
    """处理广告观看完成的回调"""
    data = request.json
    user_id = data.get('user_id')
    ad_type = data.get('ad_type', 'unity')
    
    if not user_id:
        return jsonify({'success': False, 'message': '缺少用戶ID'}), 400
    
    # 记录广告观看
    firebase_manager.record_ad_view(user_id, ad_type)
    
    # 增加用户分析次数 (根據需求修改為固定值)
    firebase_manager.increase_user_analysis_credits(user_id, amount=5)  # 直接給5次
    
    # 获取用户当前分析次数
    current_credits = firebase_manager.get_user_analysis_credits(user_id)
    
    # 尝试发送LINE消息通知用户 (修改消息，現在是免費使用)
    try:
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"恭喜您獲得5次分析機會！感謝您的支持，目前已開放免費無限使用。")
        )
    except Exception as e:
        logger.error(f"無法發送LINE通知: {e}")
    
    return jsonify({
        'success': True, 
        'message': f'恭喜！您已獲得5次分析機會，目前免費無限使用',
        'credits': "無限"
    })

# 添加贊助訊息Flex Message函數
def create_donation_flex_message():
    """創建贊助訊息的Flex Message"""
    try:
        # 確保URL格式正確包含https://
        donation_url = "https://buymeacoffee.com/todao_antifruad"
        logger.info(f"創建贊助Flex Message，使用URL: {donation_url}")
        
        flex_message = FlexSendMessage(
            alt_text="幫助我們維持服務品質",
            contents={
                "type": "bubble",
                # 移除hero部分，不再顯示圖片
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "感謝您使用防詐騙小幫手",
                            "weight": "bold",
                            "size": "xl",
                            "color": "#FF8C00"
                        },
                        {
                            "type": "text",
                            "text": "叔叔阿姨，最近詐騙真的好多喔！幸好有這個小幫手可以幫忙檢查。它就像我們派在您身邊的小保鑣一樣！👮‍♂️",
                            "margin": "md",
                            "wrap": True,
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": "不過這個小保鑣也需要補充體力（系統維護費啦～）。如果叔叔阿姨覺得它做得不錯，願意請它吃個『乖乖』（讓系統乖乖運作），我們會超級感動的！一點點心意，就能讓它更有力氣保護大家喔！💪",
                            "margin": "md",
                            "wrap": True,
                            "size": "md"
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "我要贊助",
                                "uri": donation_url
                            },
                            "color": "#FF8C00"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "您的支持是我們持續改進的動力",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "align": "center"
                                }
                            ],
                            "margin": "md"
                        }
                    ],
                    "flex": 0
                }
            }
        )
        
        return flex_message
    except Exception as e:
        logger.error(f"創建贊助Flex Message時發生錯誤: {e}")
        # 返回一個簡單的文本消息作為備用
        return TextSendMessage(text="感謝您的使用！如果覺得服務有幫助，歡迎贊助支持我們：https://buymeacoffee.com/todao_antifruad")
    logger.info(f"User {user_id} is chatting for the first time")

# 修改原來使用@前綴的地方，改為使用Mention功能
def create_mention_message(text, display_name, user_id, quick_reply=None):
    """創建帶有文本@功能的消息，兼容舊版本SDK"""
    text_with_mention = f"@{display_name} {text}"
    return TextSendMessage(text=text_with_mention, quick_reply=quick_reply)

# 創建一個全局字典來跟踪用戶狀態
user_conversation_state = {}  # 格式: {user_id: {"last_time": timestamp, "waiting_for_analysis": True/False}}

# 改進contains_url函數，使其更準確地識別URL
def contains_url(text):
    """更準確地檢查文本是否包含URL"""
    if not text:
        return False
    # 一個更完整的URL檢測正則表達式
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        r'|(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|'
        r'(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}'
    )
    return bool(url_pattern.search(text))

# 改進should_perform_fraud_analysis函數，更好地處理網址分析
def should_perform_fraud_analysis(text_message):
    """判斷是否需要對消息進行詐騙分析"""
    if not text_message:
        return False
        
    # 1. 先检查是否是次数查询，避免这类消息被分析
    if any(keyword in text_message.lower() for keyword in ["剩余次数", "剩餘次數", "查詢次數", "查询次数", "還有幾次", "还有几次", "剩下幾次", "剩下几次", "幾次機會", "几次机会", "幾次分析", "几次分析"]):
        return False
        
    # 2. 直接檢查是否含有URL，如果有優先分析
    if contains_url(text_message):
        logger.info(f"訊息中含有URL，將進行詐騙分析")
        return True
        
    # 3. 檢查是否包含常見問候詞和簡短訊息
    common_greetings = ["你好", "嗨", "哈囉", "嘿", "hi", "hello", "hey", "早安", "午安", "晚安"]
    if text_message.lower() in common_greetings or (len(text_message) <= 5 and any(greeting in text_message.lower() for greeting in common_greetings)):
        return False
        
    # 4. 檢查是否含有明確的分析請求關鍵詞
    analysis_keywords = ["分析", "詐騙", "安全", "可疑", "風險", "網站"]
    if any(keyword in text_message.lower() for keyword in analysis_keywords) and "嗎" in text_message:
        # 如果同時包含分析關鍵詞和疑問詞，可能是請求分析
        logger.info(f"訊息包含分析請求關鍵詞和疑問詞，將進行詐騙分析")
        return True
        
    # 5. 檢查是否與已知的網域相關
    for domain in SHORT_URL_DOMAINS + SAFE_DOMAINS:
        if domain.lower() in text_message.lower():
            logger.info(f"訊息包含已知網域 {domain}，將進行詐騙分析")
            return True
    
    # 6. 檢查是否是功能相關指令
    if any(keyword in text_message.lower() for keyword in function_inquiry_keywords + potato_game_trigger_keywords) or "詐騙類型" in text_message:
        return False
        
    # 7. 檢查是否是跟踪模式的問句
    if any(pattern in text_message.lower() for pattern in follow_up_patterns):
        return True
        
    # 8. 檢查是否是請求分析的明顯特徵
    analysis_indicators = ["幫我分析", "幫忙看看", "這是不是詐騙", "這是真的嗎", "這可靠嗎", "分析一下", "這樣是詐騙嗎"]
    if any(indicator in text_message for indicator in analysis_indicators):
        return True
        
    # 9. 檢查是否包含特定詐騙相關關鍵詞
    # 只有使用者明確表示需要分析，或者文本包含多個詐騙關鍵詞才進行分析
    fraud_related_keywords = ["詐騙", "被騙", "騙子", "可疑", "轉帳", "匯款", "銀行帳號", "個資", "身份證", "密碼", 
                            "通知", "中獎", "貸款", "投資", "急需", "幫我處理", "急用", "解除設定", "提款卡", 
                            "監管帳戶", "解凍", "安全帳戶", "簽證", "保證金", "違法", "洗錢", "警察", "檢察官"]
                            
    # 要求至少包含兩個詐騙相關關鍵詞
    keyword_count = sum(1 for keyword in fraud_related_keywords if keyword in text_message)
    if keyword_count >= 2:
        return True
        
    # 10. 預設不進行詐騙分析，將訊息作為一般閒聊處理
    return False

if __name__ == "__main__":
    # 確保在服務啟動時重新加載題庫
    load_fraud_tactics()
    load_potato_game_questions()
    
    # 打印題庫加載結果
    logger.info(f"服務啟動時載入題庫：potato_game_questions 包含 {len(potato_game_questions)} 道題目")
    logger.info(f"題庫中有選項的題目數量: {sum(1 for q in potato_game_questions if 'options' in q and q['options'] and 'correct_option' in q)}")
    if potato_game_questions:
        logger.info(f"題庫路徑: {os.path.abspath(POTATO_GAME_QUESTIONS_DB)}")
        logger.info(f"工作目錄: {os.getcwd()}")
        
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 