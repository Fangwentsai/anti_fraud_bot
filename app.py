import os
import json
from flask import Flask, request, abort, render_template
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

load_dotenv()

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

CHAT_TIP_PROBABILITY = 0.3 # 閒聊時回覆防詐小知識的機率

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
def detect_fraud_with_chatgpt(user_message, display_name="朋友"):
    try:
        is_url_analysis = ("網址是否安全" in user_message or 
                           (any(domain in user_message for domain in [".com", ".tw", ".org", ".net", "http://", "https://", "www."]) and len(user_message.split()) < 15))

        fraud_info = ""
        for fraud_type_key, details in fraud_tactics.items():
            if "常見話術" in details:
                fraud_info += f"詐騙類型: {fraud_type_key}\\n"
                fraud_info += "常見話術:\\n" + "\\n".join([f"- {tactic}" for tactic in details.get("常見話術", [])])
                fraud_info += "\\n\\n"

        if is_url_analysis:
            prompt = f"""哈囉 {display_name}，我是土豆，您想分析這個網址/內容是嗎？
「{user_message}」
我來幫您仔細看看。

請用清晰、易懂的方式向 {display_name} 解釋情況，就像一位耐心的技術支援人員在協助他一樣。

您的分析應包含：
1.  **這個網址/內容安全嗎？** (例如：看起來[安全/有點可疑/蠻危險的/我不太確定])
2.  **為什麼我會這樣判斷？** (簡述您的判斷理由，例如網址拼寫、是不是HTTPS開頭、網站內容等等。)
3.  **給 {display_name} 的操作建議：** (明確告知是否應該點擊或打開。如果危險，請強調「千萬不要點！」如果安全，可以說明如何安全使用。)
4.  **這可能是哪種類型的風險？** (如果可疑或危險，例如：這可能是釣魚網站，想騙您的帳號密碼；或者可能會下載怪怪的程式。)
5.  **(可選) 提醒 {display_name} 一個辨識小技巧：** (例如：以後看到類似的，可以多留意一下網址是不是官方的喔！)
            """
        else:
            prompt = f"""哈囉 {display_name}，我是您的防詐騙小幫手土豆！我來幫您看看這則訊息，請稍等我一下喔。

這是您傳來的訊息：
「{user_message}」

我會參考這些已知的詐騙資訊來幫您分析：
---
{fraud_info}
---

請您用像和朋友聊天一樣自然、口語的方式回應 {display_name}。分析結果請盡量融入到流暢的段落中，而不是生硬的點列。

您的分析應該包含以下重點，並用溫暖且支持的語氣傳達：

1.  **這則訊息的風險有多大？** (例如：我覺得這則訊息的風險比較[高/中/低]，或者看起來沒什麼問題。)
2.  **為什麼會有這樣的判斷？** (例如：主要是因為訊息裡提到了[可疑點]，或者它看起來像是普通的[訊息類型判斷]，沒有提到金錢或奇怪的要求。)
3.  **這跟哪種詐騙手法比較像？** (如果有的話，例如：這可能跟[詐騙類型]有點像。如果不像任何詐騙，或是一種新的手法，也請說明。)
4.  **給 {display_name} 的貼心建議：** (例如：建議您[具體行動]，像是不要點連結、跟家人朋友討論看看、或打給165確認一下。如果訊息安全，也可以提醒保持好習慣。)
5.  **一句鼓勵打氣的話：** (例如：{display_name}，您很小心，這樣很棒！有任何問題隨時再找我聊聊！)

如果訊息內容明顯和詐騙沒什麼關係（比如問天氣、抱怨商品），請友善地告訴 {display_name} 這可能比較不適合我分析，但可以簡單建議他可以怎麼做（例如找消保官），然後溫和地引導他回到防詐騙的話題。
            """
        
        response = openai.chat.completions.create(
            model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": "你是一位名為「土豆」的AI防詐騙顧問。你的個性充滿智慧、有耐心，並且像一位非常關心朋友的夥伴。你的目標是幫助使用者識別潛在的詐騙風險。請用溫暖、友善、口語化且易於理解的方式與使用者對話。在提供專業建議的同時，也要展現出同理心與支持，讓使用者感覺到安心和被理解。盡量避免使用過於官方或生硬的術語。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, # 略微調高以獲得更多樣性和更自然的語言，同時保持一定的真實性
            max_tokens=1500 # 增加token以應對更複雜的分析和更詳細、自然的口語回覆
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"與OpenAI API交互失敗: {e}")
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

    user_game_state[user_id] = {
        'false_potato_original': false_potato_text,
        'fraud_type_for_explanation': fraud_type,
        'custom_explanation': explanation if potato_game_questions else "",
        'option_A_text': options_display_texts[0],
        'option_B_text': options_display_texts[1],
        'option_C_text': options_display_texts[2]
    }

    flex_message_content = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='選哪顆土豆？🤔', weight='bold', size='xl', align='center', margin='md'),
                TextComponent(text='請指出下列哪一個選項「是詐騙訊息」（也就是假土豆）？', wrap=True, margin='lg', size='sm'),
                SeparatorComponent(margin='lg'),
                TextComponent(text='選項 A:', weight='bold', size='md', margin='lg'),
                TextComponent(text=options_display_texts[0][:250] + '...' if len(options_display_texts[0]) > 250 else options_display_texts[0], wrap=True, size='sm', margin='sm'),
                SeparatorComponent(margin='lg'),
                TextComponent(text='選項 B:', weight='bold', size='md', margin='lg'),
                TextComponent(text=options_display_texts[1][:250] + '...' if len(options_display_texts[1]) > 250 else options_display_texts[1], wrap=True, size='sm', margin='sm'),
                SeparatorComponent(margin='lg'),
                TextComponent(text='選項 C:', weight='bold', size='md', margin='lg'),
                TextComponent(text=options_display_texts[2][:250] + '...' if len(options_display_texts[2]) > 250 else options_display_texts[2], wrap=True, size='sm', margin='sm'),
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
                    color='#A0522D', 
                    height='sm',
                    action=PostbackAction(label='選 B', data=f'action=potato_game_answer&chosen_option_id=B&uid={user_id}')
                ),
                ButtonComponent(
                    style='primary',
                    color='#8B4513', 
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

    if chosen_text == false_potato_original_text: 
        result_text = f"👍 恭喜答對了！您成功識別出詐騙訊息！\n\n{explanation_intro}\n\n{explanation_detail}\n\n{fraud_features}\n\n記住：提高警覺，保護自己和親友的資產安全！"
        reply_messages.append(TextSendMessage(text=result_text))
    else: 
        result_text = f"❌ 要小心！您選的是安全建議，不是詐騙訊息。\n\n{explanation_intro}\n\n正確答案是：\n「{false_potato_original_text[:180]}...」\n\n{fraud_features}\n\n別灰心，透過練習您會越來越擅長識別詐騙！"
        reply_messages.append(TextSendMessage(text=result_text))

    quick_reply_items = QuickReply(items=[
        QuickReplyButton(action=PostbackAction(label="再玩一題", data=f'action=start_potato_game&uid={user_id}')),
        QuickReplyButton(action=MessageAction(label="不玩了", text="不玩了，謝謝"))
    ])
    
    reply_messages.append(TextSendMessage(text="要不要再來一局，挑戰看看？", quick_reply=quick_reply_items))
    
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

    # 0. 檢查是否正在等待用戶對某訊息提供澄清
    pending_state = user_pending_analysis.get(user_id)
    if pending_state and pending_state.get("waiting_for_clarification"):
        logger.info(f"User {user_id} is providing clarification for: {pending_state.get('original_message')}")
        clarification = text_message
        original_message_to_analyze = pending_state.get("original_message")
        
        # 將原始訊息與用戶的澄清合併後進行分析
        combined_message = f"用戶原始訊息是：\n「{original_message_to_analyze}」\n\n用戶針對此訊息，補充的疑慮或說明是：\n「{clarification}」"
        logger.info(f"Combined message for analysis for user {user_id}: {combined_message}")

        analysis_result_text = detect_fraud_with_chatgpt(combined_message, display_name)
        analysis_data = parse_fraud_analysis(analysis_result_text)

        risk_level = analysis_data.get("risk_level", "不確定")
        fraud_type_identified = analysis_data.get("fraud_type", "未知")
        explanation_text = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
        suggestions_text = analysis_data.get("suggestions", "請隨時保持警惕。")

        reply_text_parts = [
            f"{display_name}您好，針對您的訊息及補充說明，我的分析如下：",
            f"風險等級：{risk_level}",
            f"可能詐騙類型：{fraud_type_identified}"
        ]
        if explanation_text and explanation_text.strip() and not any(item in explanation_text for item in [risk_level, fraud_type_identified]):
             reply_text_parts.append(f"\n{explanation_text.strip()}")
        if suggestions_text and suggestions_text.strip():
             reply_text_parts.append(f"\n建議：\n{suggestions_text.strip()}")
        
        reply_message_text = "\n".join(reply_text_parts)

        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_message_text))
        firebase_manager.save_user_interaction(
            user_id, display_name, 
            f"Original: {original_message_to_analyze} | Clarification: {clarification}", 
            reply_message_text, 
            is_fraud_related=(risk_level.lower() not in ["無風險", "不確定", "非詐騙相關", "低", "低風險"]), # 擴展非詐騙相關判斷
            fraud_type=fraud_type_identified, 
            risk_level=risk_level
        )
        if user_id in user_pending_analysis: # 再次確認以防多重請求問題
            del user_pending_analysis[user_id] # 分析完成，清除狀態
        user_last_chat_time[user_id] = current_time # 更新最後互動時間
        return

    # 更新用戶最後聊天時間 (移至更早的位置，確保所有互動路徑都能更新)
    user_last_chat_time[user_id] = current_time

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
        user_last_chat_time[user_id] = current_time
        
        # 處理功能詢問
        if any(keyword in text_message.lower() for keyword in function_inquiry_keywords):
            reply_text = f"{display_name}您好！我是防詐騙小幫手，我的功能包括：\n\n" \
                        f"1️⃣ 詐騙風險分析：我可以分析您收到的可疑訊息，評估是否為詐騙\n\n" \
                        f"2️⃣ 詐騙類型查詢：您可以輸入「詐騙類型列表」查看各種常見詐騙\n\n" \
                        f"3️⃣ 「選哪顆土豆」小遊戲：通過遊戲學習辨識詐騙訊息\n\n" \
                        f"4️⃣ 防詐小知識：與我聊天時，我會不定時分享實用的防詐技巧\n\n" \
                        f"5️⃣ 閒聊功能：當您只是想跟我聊聊天時，我也樂意陪伴您\n\n" \
                        f"您想嘗試哪個功能呢？"
            
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="看看詐騙類型", text="詐騙類型列表")),
                QuickReplyButton(action=MessageAction(label="玩「選土豆」遊戲", text="選哪顆土豆")),
                QuickReplyButton(action=MessageAction(label="分析可疑訊息", text="我收到這個：")),
            ])
            
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "回覆功能說明", is_fraud_related=False)
            return
        
        # 處理需要追問的情況 (例如用戶明確表示被詐騙)
        if any(pattern in text_message.lower() for pattern in follow_up_patterns):
            follow_up_reply_text = (
                f"{display_name}您好！我理解您可能正在擔心是否遇到詐騙情況。\n\n"
                f"為了能更準確地幫助您分析，請您告訴我更多詳細情況：\n\n"
                f"• 您收到了什麼可疑訊息或電話？\n"
                f"• 對方提出了什麼要求？\n"
                f"• 您是否已經提供個人資料或進行付款？\n\n"
                f"請將可疑內容分享給我，我會立即為您分析風險！"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=follow_up_reply_text))
            firebase_manager.save_user_interaction(
                user_id, display_name, text_message, 
                "Responded to follow-up pattern with clarifying questions", 
                is_fraud_related=True 
            )
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
    if "詐騙類型列表" == text_message.lower() or "詐騙類型" == text_message.lower():
        types_text = "目前已收集的詐騙類型有：\n"
        for f_type, info in fraud_types.items():
            types_text += f"\n⚠️ {f_type}：\n{info['description']}\n"
        
        types_text += "\n想了解特定類型，可以問我「什麼是[詐騙類型]」喔！"

        quick_reply_items = []
        for f_type in list(fraud_types.keys())[:4]:
            quick_reply_items.append(QuickReplyButton(action=MessageAction(label=f_type, text=f"什麼是{f_type}")))

        line_bot_api.reply_message(reply_token, TextSendMessage(text=types_text, quick_reply=QuickReply(items=quick_reply_items) if quick_reply_items else None))
        firebase_manager.save_user_interaction(user_id, display_name, text_message, "Provided list of fraud types", is_fraud_related=False)
        return
    
    # 處理特定詐騙類型資訊查詢 (例如 "什麼是網路購物詐騙")
    specific_type_query_match = re.match(r"^(什麼是|查詢|我想了解|我想知道)(.+詐騙)$", text_message.strip())
    if specific_type_query_match:
        query_type_name = specific_type_query_match.group(2).strip()
        found_type = None
        for f_type_key, f_type_data in fraud_types.items():
            if query_type_name == f_type_key or query_type_name in f_type_key or f_type_key in query_type_name:
                found_type = f_type_key
                break
        
        if found_type and found_type in fraud_types:
            type_info = fraud_types[found_type]
            examples_list = type_info.get("examples", [])
            examples = "\n".join(examples_list) if examples_list else "暫無案例"
            sop_list = type_info.get("sop", [])
            sop = "\n".join(sop_list) if sop_list else "暫無建議"
            
            reply_message_parts = [
                f"【{found_type}】詳細說明：",
                type_info['description'],
                f"\n📋 常見案例與手法：\n{examples}",
                f"\n🛡️ 防範建議：\n{sop}"
            ]
            reply_message_text = "\n".join(reply_message_parts)

            line_bot_api.reply_message(reply_token,TextSendMessage(text=reply_message_text))
            firebase_manager.save_user_interaction(user_id, display_name, text_message, f"Provided details for {found_type}", is_fraud_related=False)
            return
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"抱歉，我還沒有關於「{query_type_name}」的詳細資訊。您可以輸入「詐騙類型列表」查看我已知的類型。"))
            firebase_manager.save_user_interaction(user_id, display_name, text_message, f"Specific fraud type not found: {query_type_name}", is_fraud_related=False)
            return

    # 新增：如果訊息看起來像一般分析請求，但不明確，則提問以引導用戶提供更多資訊
    is_specific_command_check = (
        any(keyword in text_message.lower() for keyword in function_inquiry_keywords) or
        any(pattern in text_message.lower() for pattern in follow_up_patterns) or 
        any(keyword in text_message.lower() for keyword in potato_game_trigger_keywords) or
        ("詐騙類型列表" == text_message.lower() or "詐騙類型" == text_message.lower()) or
        (re.match(r"^(什麼是|查詢|我想了解|我想知道)(.+詐騙)$", text_message.strip()) is not None)
    )

    if not is_specific_command_check and (len(text_message) > 15 or text_message.lower().startswith(("我收到這個", "幫我看看這個", "這則訊息", "分析一下這個", "這個是", "請問這個"))):
        logger.info(f"Message from {user_id} ('{text_message}') seems like a general analysis request. Asking for clarification.")
        user_pending_analysis[user_id] = {
            "original_message": text_message,
            "waiting_for_clarification": True,
            "timestamp": current_time 
        }
        clarification_question = (
            f"{display_name}您好，我看到您傳送了「{text_message[:30]}{'...' if len(text_message)>30 else ''}」。\n\n"
            f"為了更精準地為您分析，可以請您具體說明一下：\n"
            f"1. 您對這則訊息的哪個部分感到最可疑或不確定？\n"
            f"2. 您擔心這可能是哪種類型的問題呢（例如金錢、個資、假冒身份等）？\n\n"
            f"請直接回覆您的疑慮，我會結合您的說明為您分析。"
        )
        line_bot_api.reply_message(reply_token, TextSendMessage(text=clarification_question))
        firebase_manager.save_user_interaction(
            user_id, display_name, text_message, 
            "Asked for clarification on general analysis request", 
            is_fraud_related=False 
        )
        return

    # 如果不是任何特定指令，也不是需要提問引導的分析請求，則視為閒聊或直接分析
    # 判斷是否應進入閒聊+防詐小提示的邏輯
    # CHAT_TIP_PROBABILITY 應在文件頂部定義, e.g., CHAT_TIP_PROBABILITY = 0.3
    # 檢查訊息是否不包含任何已知指令的關鍵字，以判斷是否為一般閒聊
    general_chat_keywords = [
        "詐騙類型列表", "詐騙類型", 
        "選哪顆土豆", "玩遊戲",
        "什麼是", "查詢", "我想了解", "我想知道" # 這些是類型查詢的前綴
    ]
    general_chat_keywords.extend(function_inquiry_keywords)
    # follow_up_patterns 和 potato_game_trigger_keywords 已經在 is_specific_command_check 中考慮

    is_not_specific_command_for_chat = not any(keyword in text_message.lower() for keyword in general_chat_keywords)
    # 並且也不是正則表達式匹配的特定類型查詢
    if is_not_specific_command_for_chat and not re.match(r"^(什麼是|查詢|我想了解|我想知道)(.+詐騙)$", text_message.strip()):
        if random.random() < CHAT_TIP_PROBABILITY: 
            tip = random.choice(anti_fraud_tips)
            reply_text = f"{display_name}，和您聊天很愉快！順便分享一則防詐小知識：\n\n{tip}\n\n您想了解更多防詐資訊嗎？"
            
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="看看詐騙類型", text="詐騙類型列表")),
                QuickReplyButton(action=MessageAction(label="玩「選土豆」遊戲", text="選哪顆土豆")),
            ])
            
            firebase_manager.save_user_interaction(
                user_id, display_name, text_message, 
                reply_text, is_fraud_related=False
            )
            
            line_bot_api.reply_message(
                reply_token, 
                TextSendMessage(text=reply_text, quick_reply=quick_reply)
            )
            return
    
    # 預設使用ChatGPT進行分析 (如果以上所有條件都不滿足)
    logger.info(f"Defaulting to direct fraud analysis for message from {user_id}: {text_message}")
    analysis_result_text = detect_fraud_with_chatgpt(text_message, display_name)
    analysis_data = parse_fraud_analysis(analysis_result_text)

    risk_level = analysis_data.get("risk_level", "不確定")
    fraud_type = analysis_data.get("fraud_type", "未知")
    explanation = analysis_data.get("explanation", "分析結果不完整，請謹慎判斷。")
    suggestions = analysis_data.get("suggestions", "請隨時保持警惕。")
    is_emerging = analysis_data.get("is_emerging", False)

    reply_text = f"根據我的分析：\n風險等級：{risk_level}\n可能詐騙類型：{fraud_type}\n\n{explanation}\n\n建議：\n{suggestions}"

    if is_emerging and fraud_type != "非詐騙相關":
        emerging_text = "\n\n⚠️ 這可能是一種新的詐騙手法，我已經記錄下來了，謝謝您的資訊！"
        reply_text += emerging_text
        firebase_manager.save_emerging_fraud_report(user_id, display_name, text_message, analysis_result_text)
        is_fraud_related = True
    elif fraud_type != "非詐騙相關" and risk_level not in ["無風險", "低"]: # Consider low risk as not strictly fraud for this logging
        is_fraud_related = True
    else:
        is_fraud_related = False
        
    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
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
        with open(POTATO_GAME_QUESTIONS_DB, 'r', encoding='utf-8') as f:
            data = json.load(f)
            potato_game_questions = data.get("questions", [])
        logger.info(f"成功從 {POTATO_GAME_QUESTIONS_DB} 加載詐騙題庫，共 {len(potato_game_questions)} 道題目")
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
    # load_fraud_tactics() # Moved to be loaded once at startup
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 