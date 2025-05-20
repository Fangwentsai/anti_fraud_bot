# -*- coding: utf-8 -*-
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
import openai
import logging
from firebase_manager import FirebaseManager
import random
import datetime  # 導入datetime用於時間比較
import re

# 指定 .env 文件的路徑
# 假設 anti-fraud-clean 和 linebot-anti-fraud 是同級目錄
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'linebot-anti-fraud', '.env')
load_dotenv(dotenv_path=dotenv_path)

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

    lines = analysis_result.strip().split('\n')
    result = {
        "risk_level": "不確定",
        "fraud_type": "未知",
        "explanation": analysis_result, # Default to full analysis if parsing fails for explanation
        "suggestions": "請保持警惕，如有疑問可諮詢165反詐騙專線。",
        "is_emerging": False
    }

    for line in lines:
        if line.startswith("風險等級："):
            result["risk_level"] = line.split("風險等級：")[1].strip()
        elif line.startswith("可能詐騙類型："):
            result["fraud_type"] = line.split("可能詐騙類型：")[1].strip()
            if result["fraud_type"].lower() == "不適用" or result["fraud_type"].lower() == "無":
                 result["fraud_type"] = "非詐騙相關"
        elif line.startswith("說明："):
            result["explanation"] = line.split("說明：")[1].strip()
        elif line.startswith("建議："):
            result["suggestions"] = line.split("建議：")[1].strip()
        elif line.startswith("新興手法："):
            is_emerging_text = line.split("新興手法：")[1].strip().lower()
            result["is_emerging"] = (is_emerging_text == "是")

    # 如果解析後explanation還是原始完整訊息，且有單獨的說明字段，則用單獨的說明
    if result["explanation"] == analysis_result and "說明：" in analysis_result:
        pass # Keep as is, maybe it was just one line of explanation
    elif "說明：" not in analysis_result and "建議：" not in analysis_result : # if no specific fields, use the whole thing as explanation
         result["explanation"] = analysis_result
    
    # 如果詐騙類型包含多個，取第一個主要的
    if isinstance(result["fraud_type"], str) and ',' in result["fraud_type"]:
        result["fraud_type"] = result["fraud_type"].split(',')[0].strip()
    if isinstance(result["fraud_type"], str) and '、' in result["fraud_type"]:
        result["fraud_type"] = result["fraud_type"].split('、')[0].strip()


    return result

# ChatGPT檢測詐騙訊息函數
def detect_fraud_with_chatgpt(user_message, display_name="朋友", user_id=None):
    """使用ChatGPT API分析訊息是否為詐騙
    
    Args:
        user_message: 用戶訊息
        display_name: 用戶顯示名稱
        user_id: 用戶ID，用於獲取歷史對話
        
    Returns:
        分析結果的文本
    """
    # 檢查用戶是否有足夠的分析次數
    if user_id:
        firebase_manager = FirebaseManager.get_instance()
        logger.info(f"檢查用戶 {user_id} 的分析次數")
        
        try:
            # 嘗試獲取用戶資訊
            user_doc = firebase_manager.db.collection('users').document(user_id).get() if firebase_manager.db else None
            if user_doc and user_doc.exists:
                user_data = user_doc.to_dict()
                logger.info(f"用戶 {user_id} 資訊：{user_data}")
            else:
                logger.info(f"用戶 {user_id} 文檔不存在或無法獲取")
                
            analysis_credits = firebase_manager.get_user_analysis_credits(user_id)
            logger.info(f"用戶 {user_id} 當前分析次數：{analysis_credits}")
            
            if analysis_credits <= 0:
                # 用戶沒有足夠的分析次數，返回提示信息
                logger.info(f"用戶 {user_id} 分析次數不足，提示觀看廣告")
                return f"""
風險等級：分析受限
詐騙類型：無法評估
說明：您的免費分析次數已用完。您需要觀看廣告或進行小額贊助以獲取更多分析次數。
建議：請點擊下方的「觀看廣告」按鈕獲取免費分析次數，或選擇小額贊助支持我們的服務。

每次觀看廣告可獲得1次分析機會，或者每NT$50的贊助可獲得10次分析機會。
"""
            
            # 減少用戶的分析次數
            decrease_result = firebase_manager.decrease_user_analysis_credits(user_id)
            logger.info(f"用戶 {user_id} 減少分析次數操作結果：{decrease_result}，剩餘 {analysis_credits-1} 次")
            
            # 如果用戶次數減少後剩餘不多，額外發送提醒
            if analysis_credits - 1 <= 1:
                try:
                    # 在分析結果後額外發送次數不足提醒
                    reminder_message = f"提醒：您的分析次數剩餘不多（僅剩 {analysis_credits-1} 次）。請考慮觀看廣告或進行小額贊助以獲取更多分析次數。"
                    logger.info(f"將在分析後額外發送次數提醒給用戶 {user_id}")
                    
                    # 使用非同步方式發送，避免阻塞主流程
                    # 注意：這裡不要立即發送，而是在外部代碼中處理
                    firebase_manager.set_user_state(user_id, {
                        'needs_credits_reminder': True,
                        'remaining_credits': analysis_credits-1
                    })
                except Exception as e:
                    logger.error(f"設置次數提醒狀態失敗: {e}")
        except Exception as e:
            logger.error(f"檢查用戶 {user_id} 分析次數時出錯：{e}")
            # 即使出錯，也繼續分析，避免影響用戶體驗
    else:
        logger.info("未提供user_id，跳過分析次數檢查")
    
    try:
        # 構建基本系統提示
        system_prompt = """你是一個專業的詐騙分析專家，請分析以下訊息是否可能是詐騙：

提供分析結果時，請使用以下格式（用中文回答）：
{
"risk_level": "高/中/低/無風險",
"fraud_type": "詐騙類型或'非詐騙相關'",
"explanation": "詳細解釋為什麼這是或不是詐騙（100-200字）",
"suggestions": "給用戶的建議（如果有風險）",
"is_emerging": true/false（是否可能是新型詐騙手法）
}

分析時請特別注意：
1. 是否要求轉帳、提供個人資料或點擊可疑連結
2. 是否製造緊急感或威脅
3. 是否有不合理的誘惑（高報酬、中獎等）
4. 是否偽裝成官方機構或熟人
5. 是否有拼寫或語法錯誤

請客觀分析內容，不要過度敏感，也不要放過可疑跡象。"""

        # 如果提供了user_id，嘗試獲取歷史對話作為上下文
        messages = [{"role": "system", "content": system_prompt}]
        
        if user_id:
            recent_history = firebase_manager.get_recent_interactions(user_id, limit=3)
            
            if recent_history and len(recent_history) > 0:
                # 添加歷史上下文信息
                context_prompt = "以下是用戶最近的對話歷史，可能有助於你的分析："
                
                for interaction in recent_history:
                    if 'message' in interaction and interaction['message']:
                        context_prompt += f"\n用戶: {interaction['message']}"
                    if 'response' in interaction and interaction['response']:
                        context_prompt += f"\n機器人: {interaction['response']}"
                
                context_prompt += "\n\n請根據這些歷史對話和當前訊息進行分析。"
                
                messages.append({"role": "user", "content": context_prompt})
                logger.info(f"詐騙分析使用了 {len(recent_history)} 條歷史對話記錄")
            else:
                logger.info("詐騙分析無法獲取歷史對話，使用單一訊息分析")
        else:
            logger.info("未提供user_id，詐騙分析將不使用歷史記錄")
        
        # 添加要分析的當前訊息
        analysis_prompt = f"""請分析這則訊息：

{user_message}

這是來自「{display_name}」的訊息。請依照系統提示的格式提供JSON格式的分析結果。"""

        messages.append({"role": "user", "content": analysis_prompt})
        
        # 調用ChatGPT API
        logger.info(f"發送詐騙分析請求給ChatGPT，共{len(messages)}條消息")
        response = openai.chat.completions.create(
            model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
            messages=messages,
            temperature=0.2,  # 較低的溫度，使結果更確定性
            max_tokens=800
        )
        
        result = response.choices[0].message.content.strip()
        
        return result
    except Exception as e:
        logger.error(f"ChatGPT 詐騙分析錯誤: {e}")
        return "抱歉，我現在無法分析您的訊息。請稍後再試。"

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
def create_analysis_flex_message(analysis_data, display_name, message_to_analyze):
    """
    創建詐騙分析結果的Flex Message格式
    
    Args:
        analysis_data: 分析結果數據
        display_name: 用戶顯示名稱
        message_to_analyze: 被分析的訊息
        
    Returns:
        Flex Message對象
    """
    risk_level = analysis_data.get("risk_level", "不確定")
    fraud_type = analysis_data.get("fraud_type", "未知")
    explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
    suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
    
    # 檢查是否為用戶次數不足的情況
    if "您的免費分析次數已用完" in explanation:
        bubble = BubbleContainer(
            header=BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(
                        text="分析次數不足",
                        weight='bold',
                        size='xl',
                        color='#ffffff'
                    )
                ],
                background_color='#ff5551'
            ),
            body=BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(
                        text="您的免費分析次數已用完",
                        wrap=True,
                        weight='bold',
                        size='md',
                        margin='md'
                    ),
                    TextComponent(
                        text="請觀看廣告或進行小額贊助以獲取更多分析次數",
                        wrap=True,
                        size='sm',
                        margin='md'
                    ),
                    TextComponent(
                        text="每位用戶初始有5次免費分析機會",
                        wrap=True,
                        size='xs',
                        margin='md',
                        color='#aaaaaa'
                    )
                ]
            ),
            footer=BoxComponent(
                layout='vertical',
                spacing='sm',
                contents=[
                    ButtonComponent(
                        style='primary',
                        action=PostbackAction(
                            label="觀看廣告獲取1次機會",
                            data="action=view_ad&type=standard",
                            display_text="我想觀看廣告獲取分析機會"
                        )
                    ),
                    ButtonComponent(
                        style='secondary',
                        action=PostbackAction(
                            label="小額贊助(NT$50/10次)",
                            data="action=donate&amount=small",
                            display_text="我想小額贊助支持此服務"
                        )
                    ),
                    ButtonComponent(
                        style='secondary',
                        action=PostbackAction(
                            label="中額贊助(NT$100/30次)",
                            data="action=donate&amount=medium",
                            display_text="我想中額贊助支持此服務"
                        )
                    ),
                    ButtonComponent(
                        style='secondary',
                        action=PostbackAction(
                            label="大額贊助(NT$250/100次)",
                            data="action=donate&amount=large",
                            display_text="我想大額贊助支持此服務"
                        )
                    )
                ]
            )
        )
        
        return FlexSendMessage(alt_text='分析次數不足', contents=bubble)
    
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
                    text=f"幫我分析這個網站是不是詐騙：\n{message_to_analyze[:60] + '...' if len(message_to_analyze) > 60 else message_to_analyze}",
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
    user_message = event.message.text
    reply_token = event.reply_token
    
    # 記錄接收的消息
    logger.info(f"接收到來自 {user_id} 的消息: {user_message}")
    
    # 獲取用戶資料
    profile = get_user_profile(user_id)
    
    # 如果無法獲取用戶資料，使用默認值
    display_name = profile.display_name if profile else "使用者"

    # 檢查用戶是否需要發送次數提醒
    firebase_manager = FirebaseManager.get_instance()
    user_state = firebase_manager.get_user_state(user_id)
    
    if user_state.get('needs_credits_reminder', False):
        try:
            remaining_credits = user_state.get('remaining_credits', 0)
            logger.info(f"用戶 {user_id} 需要發送次數提醒，剩餘 {remaining_credits} 次")
            
            # 發送次數提醒
            if remaining_credits <= 1:
                # 次數很少，發送帶按鈕的提醒
                flex_message = FlexSendMessage(
                    alt_text='分析次數提醒',
                    contents={
                        "type": "bubble",
                        "body": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "⚠️ 分析次數提醒",
                                    "weight": "bold",
                                    "size": "xl"
                                },
                                {
                                    "type": "text",
                                    "text": f"您的分析次數剩餘不多，僅剩 {remaining_credits} 次！",
                                    "wrap": True,
                                    "margin": "md",
                                    "color": "#ff5551"
                                },
                                {
                                    "type": "text",
                                    "text": "建議您通過觀看廣告或小額贊助獲取更多分析次數，以確保服務持續可用。",
                                    "wrap": True,
                                    "margin": "md"
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
                                    "action": {
                                        "type": "postback",
                                        "label": "觀看廣告獲取1次機會",
                                        "data": "action=view_ad&type=standard",
                                        "displayText": "我想觀看廣告獲取分析機會"
                                    }
                                },
                                {
                                    "type": "button",
                                    "style": "secondary",
                                    "action": {
                                        "type": "postback",
                                        "label": "小額贊助(NT$50/10次)",
                                        "data": "action=donate&amount=small",
                                        "displayText": "我想小額贊助支持此服務"
                                    }
                                }
                            ]
                        }
                    }
                )
                
                # 使用push_message而不是reply_message，避免干擾當前對話
                line_bot_api.push_message(user_id, flex_message)
            
            # 清除提醒狀態
            firebase_manager.set_user_state(user_id, {
                'needs_credits_reminder': False
            })
        except Exception as e:
            logger.error(f"發送次數提醒失敗: {e}")
    
    # 將文本標準化（去除空格、轉為小寫）方便匹配命令
    text_message = user_message.strip()
    
    # 查詢剩餘分析次數 - 擴大匹配範圍並添加詳細日誌
    if any(keyword in text_message.lower() for keyword in ["剩餘次數", "查詢次數", "我還有幾次", "剩餘分析次數", "次數", "幾次", "分析次數", "分析機會"]):
        logger.info(f"用戶 {user_id} 正在查詢剩餘分析次數，輸入文本: {text_message}")
        user_id = event.source.user_id
        firebase_manager = FirebaseManager.get_instance()
        
        try:
            # 獲取用戶文檔
            user_doc = firebase_manager.db.collection('users').document(user_id).get() if firebase_manager.db else None
            if user_doc and user_doc.exists:
                user_data = user_doc.to_dict()
                logger.info(f"用戶 {user_id} 數據: {user_data}")
                
            # 獲取分析次數
            analysis_credits = firebase_manager.get_user_analysis_credits(user_id)
            logger.info(f"用戶 {user_id} 剩餘分析次數: {analysis_credits}")
            
            if not firebase_manager.db:
                # Firebase連接失敗的情況，使用一般回覆
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"您好，{display_name}！網頁/訊息分析功能目前完全免費，無使用次數限制。\n\n若您有發現可疑訊息，歡迎直接分享給我進行分析！")
                )
            else:
                # Firebase連接成功，提供準確的次數信息
                response_text = f"您好，{display_name}！\n\n您目前剩餘 {analysis_credits} 次網頁/訊息分析機會。\n\n"
                
                # 根據剩餘次數提供不同的建議
                if analysis_credits <= 1:
                    response_text += "您的分析次數即將用完！可以選擇以下方式獲取更多分析機會：\n\n1. 觀看廣告（+1次）\n2. 小額贊助（每NT$50可獲得10次）\n\n請使用下方按鈕增加您的分析次數。"
                    
                    # 添加按鈕
                    flex_message = FlexSendMessage(
                        alt_text='查詢分析次數結果',
                        contents={
                            "type": "bubble",
                            "body": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": f"剩餘分析次數：{analysis_credits}",
                                        "weight": "bold",
                                        "size": "xl"
                                    },
                                    {
                                        "type": "text",
                                        "text": "您的分析次數即將用完！",
                                        "wrap": True,
                                        "margin": "md",
                                        "color": "#ff5551"
                                    },
                                    {
                                        "type": "text",
                                        "text": "可透過以下方式獲取更多分析機會：",
                                        "wrap": True,
                                        "margin": "md"
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
                                        "action": {
                                            "type": "postback",
                                            "label": "觀看廣告獲取1次機會",
                                            "data": "action=view_ad&type=standard",
                                            "displayText": "我想觀看廣告獲取分析機會"
                                        }
                                    },
                                    {
                                        "type": "button",
                                        "style": "secondary",
                                        "action": {
                                            "type": "postback",
                                            "label": "小額贊助(NT$50/10次)",
                                            "data": "action=donate&amount=small",
                                            "displayText": "我想小額贊助支持此服務"
                                        }
                                    }
                                ]
                            }
                        }
                    )
                    
                    line_bot_api.reply_message(event.reply_token, flex_message)
                else:
                    # 次數充足的情況
                    response_text += f"每位用戶初始有5次免費分析機會。如需更多次數，可以透過觀看廣告或小額贊助獲取。\n\n觀看一次廣告可獲得1次分析機會，或者每NT$50的贊助可獲得10次分析機會。"
                    
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=response_text)
                    )
            
            # 記錄互動
            firebase_manager.save_user_interaction(
                user_id, display_name, text_message, 
                f"查詢剩餘分析次數，當前剩餘{analysis_credits}次", 
                is_fraud_related=False
            )
        except Exception as e:
            logger.error(f"處理次數查詢時出錯: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"抱歉，查詢次數時出現錯誤。您可以繼續使用分析功能，我們會盡快修復問題。")
            )
        return
    
    # 檢查是否為首次對話的用戶
    is_first_time = user_id not in first_time_chatters
    if is_first_time:
        first_time_chatters.add(user_id)
        logger.info(f"User {user_id} is chatting for the first time")

    # 更新用戶最後聊天時間
    user_last_chat_time[user_id] = datetime.datetime.now()

    # 0. 檢查是否正在等待用戶對某訊息提供澄清
    pending_state = user_pending_analysis.get(user_id)
    if pending_state and pending_state.get("waiting_for_clarification"):
        logger.info(f"User {user_id} is providing clarification for: {pending_state.get('original_message')}")
        clarification = text_message
        original_message_to_analyze = pending_state.get("original_message")
        
        # 將原始訊息與用戶的澄清合併後進行分析
        combined_message = f"用戶原始訊息是：\n「{original_message_to_analyze}」\n\n用戶針對此訊息，補充的疑慮或說明是：\n「{clarification}」"
        logger.info(f"Combined message for analysis for user {user_id}: {combined_message}")

        analysis_result_text = detect_fraud_with_chatgpt(combined_message, display_name, user_id)
        analysis_data = parse_fraud_analysis(analysis_result_text)

        # 創建並發送Flex Message分析結果
        flex_message = create_analysis_flex_message(analysis_data, display_name, combined_message)
        line_bot_api.reply_message(reply_token, flex_message)

        # 保存互動記錄
        risk_level = analysis_data.get("risk_level", "不確定")
        fraud_type = analysis_data.get("fraud_type", "未知")
        firebase_manager.save_user_interaction(
            user_id, display_name, 
            f"Original: {original_message_to_analyze} | Clarification: {clarification}", 
            analysis_result_text, 
            is_fraud_related=(risk_level.lower() not in ["無風險", "不確定", "非詐騙相關", "低", "低風險"]),
            fraud_type=fraud_type, 
            risk_level=risk_level
        )
        
        if user_id in user_pending_analysis:
            del user_pending_analysis[user_id]
        user_last_chat_time[user_id] = datetime.datetime.now()
        return

    # 檢查用戶是否在遊戲中
    if user_id in user_game_state:
        logger.info(f"User {user_id} is in potato game state.")
        # 檢查是否需要重置自動回覆計時器 (例如超過5分鐘沒有互動)
        # 這段邏輯可以根據實際需求保留或調整
        # if user_id in user_last_chat_time and (current_time - user_last_chat_time[user_id]) > AUTO_REPLY_RESET_INTERVAL:
        # logger.info(f"Resetting auto-reply for user {user_id} due to inactivity.")
        # # 可以在這裡發送一個新的問候語或提示
        # greeting_message = f"{display_name}您好！又見面了，有什麼可以幫您的嗎？試試看輸入「功能」了解我會做什麼！"
        # line_bot_api.push_message(user_id, TextSendMessage(text=greeting_message))
        # firebase_manager.save_user_interaction(user_id, display_name, "Auto-reply reset", greeting_message, is_fraud_related=False)

        # 更新用戶最後聊天時間 (即便只是用戶發訊息，尚未回覆，也更新)
        user_last_chat_time[user_id] = datetime.datetime.now()
        
        # 處理功能詢問
        if any(keyword in text_message.lower() for keyword in function_inquiry_keywords):
            reply_text = f"{display_name}您好！我是防詐騙小幫手，我的功能包括：\n\n" \
                        f"1️⃣ 詐騙風險分析：我可以分析您收到的可疑訊息，評估是否為詐騙\n\n" \
                        f"2️⃣ 詐騙類型查詢：您可以輸入「詐騙類型列表」查看各種常見詐騙\n\n" \
                        f"3️⃣ 「選哪顆土豆」小遊戲：通過遊戲學習辨識詐騙訊息\n\n" \
                        f"請選擇您想嘗試的功能："
            
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
            ])
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "回覆功能說明", is_fraud_related=False)
            return
        
        # 處理需要追問的情況 (例如用戶明確表示被詐騙)
        if any(pattern in text_message.lower() for pattern in follow_up_patterns):
            follow_up_reply_text = (
                f"{display_name}您好！請不要擔心，我了解您可能正在擔心遇到詐騙情況。\n\n"
                f"為了能更準確地幫助您分析，請您告訴我更多詳細情況：\n\n"
                f"• 您收到了什麼可疑訊息或電話？\n"
                f"• 對方提出了什麼要求？\n"
                f"• 您是否已經提供個人資料或進行付款？\n\n"
                f"請將可疑內容分享給我，我會立即為您分析風險！\n\n"
                f"【溫馨提醒】：請一次性將完整情況描述清楚，避免分成多則短訊息發送，這樣我才能更準確地理解並分析您遇到的情況。"
            )
            
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
            ])
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=follow_up_reply_text, quick_reply=quick_reply))
            firebase_manager.save_user_interaction(
                user_id, display_name, text_message, 
                "Responded to follow-up pattern with clarifying questions", 
                is_fraud_related=True 
            )
            return

    # 處理「選哪顆土豆」遊戲觸發 (注意：這部分代碼從user_game_state條件內移出)
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
            quick_reply_items.append(QuickReplyButton(action=MessageAction(label=f_type, text=f"什麼是{f_type}")))

        line_bot_api.reply_message(reply_token, TextSendMessage(text=types_text, quick_reply=QuickReply(items=quick_reply_items) if quick_reply_items else None))
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
            
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="查看其他詐騙類型", text="詐騙類型列表")),
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息："))
            ])
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text, quick_reply=quick_reply))
            firebase_manager.save_user_interaction(user_id, display_name, text_message, f"Provided info about {matched_fraud_type}", is_fraud_related=False)
            return
        else:
            # 未找到匹配的詐騙類型，給出一般性回覆
            response_text = f"抱歉，我目前沒有關於「{query_type}」的詳細資訊。\n\n以下是我已收集的詐騙類型，您可以查詢這些："
            for f_type in fraud_types.keys():
                response_text += f"\n- {f_type}"
            
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="查看詐騙類型列表", text="詐騙類型列表")),
                QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆"))
            ])
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text, quick_reply=quick_reply))
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "Responded to unknown fraud type query", is_fraud_related=False)
            return

    # 檢查是否為請求分析的提示語
    analysis_prompts = ["請幫我分析這則訊息：", "幫我分析這則訊息", "分析這則訊息", "幫我分析訊息"]
    if any(text_message.strip() == prompt or text_message.strip() == prompt.rstrip("：") for prompt in analysis_prompts):
        logger.info(f"User {user_id} requested message analysis but didn't provide message content")
        prompt_reply = f"{display_name}，您好！請將您想要分析的可疑訊息完整發送給我，我會立即為您進行詐騙風險評估。\n\n例如：\n- 銀行通知您的帳戶異常需要操作ATM\n- 不明網拍賣家要求私下交易\n- 陌生人傳來的投資理財訊息\n等等。"
        
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
            QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表"))
        ])
        
        line_bot_api.reply_message(reply_token, TextSendMessage(text=prompt_reply, quick_reply=quick_reply))
        firebase_manager.save_user_interaction(user_id, display_name, text_message, "Responded to analysis request prompt", is_fraud_related=False)
        return

    # 檢查是否需要對消息進行詐騙分析的邏輯
    def should_perform_fraud_analysis(text_message):
        # 1. 檢查是否包含常見問候詞
        common_greetings = ["你好", "嗨", "哈囉", "嘿", "hi", "hello", "hey", "早安", "午安", "晚安"]
        if text_message.lower() in common_greetings or (len(text_message) <= 5 and any(greeting in text_message.lower() for greeting in common_greetings)):
            return False
            
        # 2. 檢查是否是功能相關指令
        if any(keyword in text_message.lower() for keyword in function_inquiry_keywords + potato_game_trigger_keywords) or "詐騙類型" in text_message:
            return False
            
        # 3. 檢查是否是跟踪模式的問句
        if any(pattern in text_message.lower() for pattern in follow_up_patterns):
            return True
            
        # 4. 檢查是否是請求分析的明顯特徵
        analysis_indicators = ["幫我分析", "幫忙看看", "這是不是詐騙", "這是真的嗎", "這可靠嗎", "分析一下", "這樣是詐騙嗎"]
        if any(indicator in text_message for indicator in analysis_indicators):
            return True
            
        # 5. 檢查是否包含特定詐騙相關關鍵詞
        # 只有使用者明確表示需要分析，或者文本包含多個詐騙關鍵詞才進行分析
        fraud_related_keywords = ["詐騙", "被騙", "騙子", "可疑", "轉帳", "匯款", "銀行帳號", "個資", "身份證", "密碼", 
                                "通知", "中獎", "貸款", "投資", "急需", "幫我處理", "急用", "解除設定", "提款卡", 
                                "監管帳戶", "解凍", "安全帳戶", "簽證", "保證金", "違法", "洗錢", "警察", "檢察官"]
                                
        # 要求至少包含兩個詐騙相關關鍵詞
        keyword_count = sum(1 for keyword in fraud_related_keywords if keyword in text_message)
        if keyword_count >= 2:
            return True
            
        # 關鍵變化：不再使用「消息長度>20」作為自動分析的條件
        # 更明確的判斷是用戶是否實際請求分析詐騙風險
            
        # 6. 預設不進行詐騙分析，將訊息作為一般閒聊處理
        return False

    # 預設使用ChatGPT進行閒聊回應或詐騙分析
    logger.info(f"Message from {user_id}: {text_message} - Determining if fraud analysis is needed")
    
    # 判斷是否需要進行詐騙分析
    if should_perform_fraud_analysis(text_message):
        logger.info(f"Performing fraud analysis for message from {user_id}: {text_message}")
        # 使用現有的詐騙分析邏輯，傳入user_id
        analysis_result_text = detect_fraud_with_chatgpt(text_message, display_name, user_id)
        analysis_data = parse_fraud_analysis(analysis_result_text)

        risk_level = analysis_data.get("risk_level", "不確定")
        fraud_type = analysis_data.get("fraud_type", "未知")
        explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
        suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
        is_emerging = analysis_data.get("is_emerging", False)

        # 創建並發送Flex Message分析結果
        flex_message = create_analysis_flex_message(analysis_data, display_name, text_message)
        line_bot_api.reply_message(reply_token, flex_message)

        if is_emerging and fraud_type != "非詐騙相關":
            # 新增詐騙手法記錄通知改為單獨推送，避免混淆Flex Message
            emerging_text = "⚠️ 這可能是一種新的詐騙手法，我已經記錄下來了，謝謝您的資訊！"
            line_bot_api.push_message(user_id, TextSendMessage(text=emerging_text))
            firebase_manager.save_emerging_fraud_report(user_id, display_name, text_message, analysis_result_text)
            is_fraud_related = True
        elif fraud_type != "非詐騙相關" and risk_level not in ["無風險", "低"]: 
            is_fraud_related = True
        else:
            is_fraud_related = False
            
        # 保存互動記錄到Firebase
        firebase_manager.save_user_interaction(
            user_id, display_name, text_message, analysis_result_text,
            is_fraud_related=is_fraud_related,
            fraud_type=fraud_type if is_fraud_related else None,
            risk_level=risk_level if is_fraud_related else None
        )
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
            
            # 使用更友善的閒聊回應並帶有記憶功能
            chat_response = openai.chat.completions.create(
                model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            
            chat_reply = chat_response.choices[0].message.content.strip()
            
            # 只在首次聊天時添加功能介紹
            if is_first_time:
                introduction = f"\n\n我是防詐騙機器人「土豆」，能幫您：\n1️⃣ 分析可疑訊息\n2️⃣ 測試您的防詐騙能力\n3️⃣ 查詢各類詐騙手法"
                reply_text = chat_reply + introduction
            else:
                reply_text = chat_reply
            
            is_fraud_related = False
            
        except Exception as e:
            logger.error(f"閒聊回應錯誤: {e}")
            # 如果閒聊回應失敗，使用簡單的問候
            greetings = ["您好！", "嗨！", "哈囉！", "很高興見到您！", "您好呀！"]
            
            # 只在首次聊天時添加功能介紹
            if is_first_time:
                reply_text = f"{random.choice(greetings)}有什麼我能幫您的嗎？您可以輸入「功能」來了解我能做什麼。"
            else:
                reply_text = f"{random.choice(greetings)}有什麼我能幫您的嗎？"
            
            is_fraud_related = False
    
    # 添加功能按鈕到所有回覆
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="請幫我分析這則訊息：")),
        QuickReplyButton(action=MessageAction(label="防詐騙能力測試", text="選哪顆土豆")),
        QuickReplyButton(action=MessageAction(label="詐騙類型查詢", text="詐騙類型列表")),
        QuickReplyButton(action=MessageAction(label="查詢剩餘次數", text="剩餘次數"))
    ])
    
    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
    
    # 保存互動記錄到Firebase
    firebase_manager.save_user_interaction(
        user_id, display_name, text_message, reply_text,
        is_fraud_related=is_fraud_related,
        fraud_type=fraud_type if is_fraud_related else None,
        risk_level=risk_level if is_fraud_related else None
    )

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    postback_data_str = event.postback.data
    
    logger.info(f"接收到來自 {user_id} 的 Postback: {postback_data_str}")
    
    # 解析 postback_data (e.g., "action=value&key=value")
    # Ensure robust parsing for various possible postback data formats
    try:
        data_params = dict(item.split("=", 1) for item in postback_data_str.split("&") if "=" in item)
    except ValueError:
        logger.error(f"無法解析 Postback data: {postback_data_str}")
        data_params = {} # Avoid crashing if data is malformed

    action = data_params.get('action')
    uid_from_data = data_params.get('uid')

    if uid_from_data and uid_from_data != user_id:
       logger.warning(f"User ID mismatch in postback: event.source.user_id={user_id}, data_params.uid={uid_from_data}. Using event.source.user_id.")
       # Prefer user_id from event source for security and consistency.

    profile = get_user_profile(user_id) # Get profile for display name if needed
    display_name = profile.display_name if profile and profile.display_name else "使用者"

    # 處理廣告觀看
    if action == 'view_ad':
        ad_type = data_params.get('type', 'standard')
        
        # 創建LIFF URL (LINE Frontend Framework)
        liff_url = f"{request.host_url}watch-ad/{user_id}"
        
        # 發送確認消息，包含打開網頁觀看廣告的按鈕
        flex_message = FlexSendMessage(
            alt_text='觀看廣告獲得分析機會',
            contents={
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "觀看廣告獲得分析機會",
                            "weight": "bold",
                            "size": "xl"
                        },
                        {
                            "type": "text",
                            "text": "完整觀看一則廣告即可獲得1次免費分析機會",
                            "wrap": True,
                            "margin": "md"
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
                            "action": {
                                "type": "uri",
                                "label": "觀看廣告",
                                "uri": liff_url
                            }
                        }
                    ]
                }
            }
        )
        
        line_bot_api.reply_message(event.reply_token, flex_message)
        
        # 記錄互動
        firebase_manager.save_user_interaction(
            user_id, display_name, f"請求觀看廣告:{ad_type}", 
            "發送廣告觀看頁面連結", 
            is_fraud_related=False
        )
        return
    
    # 處理贊助
    if action == 'donate':
        amount = data_params.get('amount', 'small')
        
        firebase_manager = FirebaseManager.get_instance()
        
        # 根據贊助金額增加用戶分析次數
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
        
        # 獲取用戶當前分析次數
        current_credits = firebase_manager.get_user_analysis_credits(user_id)
        
        # 發送確認消息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"感謝您的{donation_amount}贊助！您已獲得{credits_to_add}次分析機會，目前剩餘{current_credits}次分析機會。")
        )
        
        # 記錄互動
        firebase_manager.save_user_interaction(
            user_id, display_name, f"贊助:{amount}", 
            f"用戶贊助{donation_amount}獲得{credits_to_add}次分析次數，當前剩餘{current_credits}次", 
            is_fraud_related=False
        )
        return

    if action == 'potato_game_answer':
        logger.info(f"User {display_name}({user_id}) answered potato game.")
        # Log game interaction before handling answer
        chosen_option = data_params.get('chosen_option_id', 'N/A')
        firebase_manager.save_user_interaction(
            user_id, display_name, f"PotatoGame_Answer:{chosen_option}", 
            "處理「選哪顆土豆」遊戲答案", is_fraud_related=False 
        )
        handle_potato_game_answer(user_id, reply_token, data_params)
        return
    elif action == 'start_potato_game':
        logger.info(f"User {display_name}({user_id}) wants to play potato game again.")
        firebase_manager.save_user_interaction(
            user_id, display_name, "PotatoGame_Restart", 
            "重新開始「選哪顆土豆」遊戲", is_fraud_related=False
        )
        send_potato_game_question(user_id, reply_token)
        return
    
    # 你可以在這裡添加更多的 postback 處理邏輯
    # 例如處理其他 Flex Message 按鈕的點擊事件

    else:
        logger.warning(f"未知的 Postback action: {action} from user {user_id}")
        # line_bot_api.reply_message(reply_token, TextSendMessage(text="收到一個我無法處理的指令，請再試一次。"))
        # Decided not to reply for unknown postbacks to avoid interrupting other flows or causing confusion.
        # If specific unhandled postbacks need a reply, add explicit conditions.

# 載入詐騙題庫
POTATO_GAME_QUESTIONS_DB = "potato_game_questions.json"
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

@app.route("/watch-ad/<user_id>", methods=['GET'])
def watch_ad(user_id):
    """顯示Unity廣告的頁面"""
    return render_template('watch_ad.html', user_id=user_id)

@app.route("/ad-completed", methods=['POST'])
def ad_completed():
    """處理廣告觀看完成的回調"""
    data = request.json
    user_id = data.get('user_id')
    ad_type = data.get('ad_type', 'unity')
    
    if not user_id:
        return jsonify({'success': False, 'message': '缺少用戶ID'}), 400
    
    firebase_manager = FirebaseManager.get_instance()
    
    # 記錄廣告觀看
    firebase_manager.record_ad_view(user_id, ad_type)
    
    # 增加用戶分析次數
    firebase_manager.increase_user_analysis_credits(user_id, amount=1)
    
    # 獲取用戶當前分析次數
    current_credits = firebase_manager.get_user_analysis_credits(user_id)
    
    # 嘗試發送LINE訊息通知用戶
    try:
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"恭喜您觀看廣告獲得1次分析機會！目前剩餘{current_credits}次分析機會。")
        )
    except Exception as e:
        logger.error(f"無法發送LINE通知: {e}")
    
    return jsonify({
        'success': True, 
        'message': f'恭喜！您已獲得1次分析機會，目前剩餘{current_credits}次',
        'credits': current_credits
    })

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