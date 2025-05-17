import os
import json
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage,
    QuickReply, QuickReplyButton, MessageAction, PostbackEvent,
    BubbleContainer, BoxComponent, ButtonComponent, TextComponent,
    CarouselContainer, URIAction, SeparatorComponent
)
from dotenv import load_dotenv
import openai
import logging
from firebase_manager import FirebaseManager
import random

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

# 詐騙類型分類
fraud_types = {
    "網路購物詐騙": {
        "description": "涉及假冒購物網站、虛假商品或不實廣告的詐騙",
        "examples": [
            "假買家騙賣家詐騙：詐騙集團假扮買家接觸二手商品賣家，聲稱透過蝦皮等平台交易，引導賣家加入假冒客服LINE帳號，以「簽署保證書」、「銀行認證」等藉口誘導賣家進行網路銀行轉帳或LINE Pay付款，導致受害者財產損失。"
        ],
        "sop": [
            "有網路交易問題，請洽交易平臺公告的官方客服聯繫方式，不要使用陌生人提供的聯繫方式",
            "堅守平台內部交易，不要跳出蝦皮、露天或其他平台的對話系統",
            "銀行及蝦皮等平台不會以私人LINE帳號聯繫客戶",
            "遇到要求「簽署保證書」、「銀行認證」等操作時，請提高警覺",
            "絕對不要依照他人指示操作網路銀行或進行轉帳",
            "有任何疑問，請立即撥打165反詐騙專線諮詢"
        ]
    },
    "假交友投資詐騙": {
        "description": "透過網路交友平台或社群媒體，假扮有好感的異性建立感情連結，最終以各種理由騙取金錢",
        "examples": [
            "詐騙者假扮高社經地位人士（如醫生、軍官、機長等）與被害者在網路上認識並建立情感連結，長期噓寒問暖後，以生病需要醫藥費、寄送海外禮物需繳納關稅等各種理由，誘騙被害者轉帳或面交金錢。此類詐騙特別針對寡居或情感生活較為孤單的中老年人。"
        ],
        "sop": [
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
        "examples": [],
        "sop": []
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
                fraud_info += f"詐騙類型: {fraud_type_key}\n"
                fraud_info += "常見話術:\n" + "\n".join([f"- {tactic}" for tactic in details.get("常見話術", [])])
                fraud_info += "\n\n"

        if is_url_analysis:
            prompt = f"""
作為頂尖的網路安全專家，請分析 {display_name} 提供的以下網址/內容是否安全，是否為釣魚、惡意或詐騙網站。

網址/內容:
{user_message}

請提供清晰的回應，包含：
1.  **安全評估**：[安全/可疑/危險/不確定]
2.  **主要判斷理由**：[簡述原因]
3.  **給 {display_name} 的建議**：[操作建議，例如是否可以點擊、要注意什麼]
4.  **潛在風險類型**：[如果可疑或危險，指出可能的詐騙類型，例如：釣魚網站、惡意軟體下載、假冒官方網站等]
            """
        else:
            prompt = f"""
作為一位專業且極富同理心的防詐騙顧問，請細心分析 {display_name} 提供的以下訊息是否包含詐騙跡象。

{display_name} 的訊息內容:
'{user_message}'

請參考以下已知的詐騙類型和常見話術資料庫：
---
{fraud_info}
---

您的分析應包含以下幾點，並請用溫暖且支持的語氣回應：
1.  **整體風險評估**：[高風險/中風險/低風險/無詐騙風險/尚無法判斷]
2.  **是否符合已知詐騙類型**：[如果符合，請說明是哪種類型，例如：網路購物詐騙、假投資詐騙等。如果不符合，請跳到第3點。]
3.  **是否為新興或未記錄的詐騙手法**：[如果您判斷這可能是一種新的、資料庫未記載的詐騙手法，請明確指出，例如："{display_name}，這聽起來可能是一種比較新的詐騙手法，我目前資料庫裡還沒有完全一樣的記錄。"]
4.  **可疑之處分析**：[詳細說明您判斷的理由、訊息中的哪些部分讓您覺得可疑，或者為什麼覺得它不是詐騙。]
5.  **給 {display_name} 的具體建議**：[提供清晰、可操作的建議，例如：不要點擊連結、不要提供個資、向誰查證、如何應對等。]
6.  **鼓勵與關懷**：[用一句溫暖的話作結，讓 {display_name} 感到被支持。例如：「請放心，隨時都可以找我聊聊。」或「您很警覺，這很棒！」]

如果訊息內容明顯與詐騙無關（例如：詢問天氣、日常生活抱怨、商品瑕疵等消費糾紛），請友善告知這比較不屬於詐騙協談的範圍，但可以簡要提供處理該類問題的建議方向（例如找消保官），並溫和地引導回防詐騙主題。
            """
        
        response = openai.chat.completions.create(
            model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": "你是一位頂尖的防詐騙顧問和網路安全專家，擁有豐富的詐騙案例知識。你的目標是幫助使用者識別風險、提供精準建議，並且在必要時能識別出新型態的詐騙手法。你的回應專業、權威，同時充滿同理心與關懷。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6, # 略微調高以獲得更多樣性和更自然的語言
            max_tokens=1200 # 增加token以應對更複雜的分析和回覆
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
    
    report_data = firebase_manager.get_random_fraud_report_for_game()

    if not report_data:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="抱歉，目前題庫裡沒有題目了，稍後再試試吧！")
        )
        return

    false_potato_text = report_data['message']
    true_potato_text = "這是一個相對安全的提示或做法：保持警惕，仔細核實信息來源，不要輕易透露個人敏感資料或進行轉帳操作。遇到可疑情況請與家人朋友商量或報警。"
    
    options_display_texts = [false_potato_text, true_potato_text]
    random.shuffle(options_display_texts)

    user_game_state[user_id] = {
        'false_potato_original': false_potato_text,
        'fraud_type_for_explanation': report_data['fraud_type'],
        'option_A_text': options_display_texts[0],
        'option_B_text': options_display_texts[1]
    }

    flex_message_content = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='選哪顆土豆？🤔', weight='bold', size='xl', align='center', margin='md'),
                TextComponent(text='親愛的朋友，請判斷下面哪個選項「更像」是詐騙陷阱（也就是假土豆）呢？', wrap=True, margin='lg', size='sm'),
                SeparatorComponent(margin='lg'),
                TextComponent(text='選項 A:', weight='bold', size='md', margin='lg'),
                TextComponent(text=options_display_texts[0][:250] + '...' if len(options_display_texts[0]) > 250 else options_display_texts[0], wrap=True, size='sm', margin='sm'),
                SeparatorComponent(margin='lg'),
                TextComponent(text='選項 B:', weight='bold', size='md', margin='lg'),
                TextComponent(text=options_display_texts[1][:250] + '...' if len(options_display_texts[1]) > 250 else options_display_texts[1], wrap=True, size='sm', margin='sm'),
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
    
    chosen_text = ""
    if chosen_option_id == 'A':
        chosen_text = game_data['option_A_text']
    elif chosen_option_id == 'B':
        chosen_text = game_data['option_B_text']
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="選擇出錯了，請重新玩一次哦。"))
        return

    reply_messages = []
    explanation_intro = f"這則訊息和【{fraud_type_for_explanation}】詐騙手法有關。"
    explanation_detail = f"原本的詐騙訊息是：\n「{false_potato_original_text[:250]}...」" 

    if chosen_text == false_potato_original_text: 
        result_text = f"答對了！🎉 您真厲害，成功選出了假土豆！\n\n{explanation_intro}\n{explanation_detail}\n\n多一分警惕，少一分風險！"
        reply_messages.append(TextSendMessage(text=result_text))
    else: 
        result_text = f"哎呀，差一點點！您選的這個選項其實是比較安全的做法喔。\n真正的「假土豆」(詐騙陷阱)是另一個。\n\n{explanation_intro}\n{explanation_detail}\n\n沒關係，多練習幾次就會更熟悉這些手法了！"
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
    text_message = event.message.text.strip()
    reply_token = event.reply_token # Get reply_token

    profile = get_user_profile(user_id)
    display_name = profile.display_name if profile and profile.display_name else "使用者"
    logger.info(f"接收到來自 {display_name}({user_id}) 的訊息: {text_message}")

    # 遊戲觸發
    game_trigger_keywords = ["選哪顆土豆", "玩遊戲", "開始遊戲", "選土豆", "potato game"]
    if text_message.lower() in game_trigger_keywords:
        logger.info(f"User {user_id} triggered potato game.")
        firebase_manager.save_user_interaction(
            user_id, display_name, text_message, 
            "啟動「選哪顆土豆」遊戲", is_fraud_related=False
        )
        send_potato_game_question(user_id, reply_token)
        return

    # 其他既有訊息處理邏輯
    if text_message == "詐騙類型列表" or text_message == "有哪些詐騙":
        carousel_items = []
        type_names = list(fraud_types.keys())
        chunk_size = 10 # Max buttons per bubble for Flex Carousel

        for i in range(0, len(type_names), chunk_size):
            chunk = type_names[i:i+chunk_size]
            buttons = []
            for type_name in chunk:
                buttons.append(
                    ButtonComponent(
                        style='link',
                        height='sm',
                        action=MessageAction(label=type_name, text=f"我想了解 {type_name}")
                    )
                )
            
            bubble = BubbleContainer(
                body=BoxComponent(
                    layout='vertical',
                    contents=[
                        TextComponent(text='選擇想了解的詐騙類型', weight='bold', size='md')
                    ] + buttons
                )
            )
            carousel_items.append(bubble)
        
        if carousel_items:
            flex_message = FlexSendMessage(
                alt_text='詐騙類型列表',
                contents=CarouselContainer(contents=carousel_items)
            )
            line_bot_api.reply_message(reply_token, flex_message)
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "回覆詐騙類型列表 Flex Message")
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="目前沒有可顯示的詐騙類型。"))
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "回覆無詐騙類型")
        return

    elif text_message.startswith("我想了解"):
        try:
            selected_type = text_message.split("我想了解")[1].strip()
            if selected_type in fraud_types:
                type_info = fraud_types[selected_type]
                description = type_info.get("description", "暫無描述")
                examples = "\n".join([f"- {ex}" for ex in type_info.get("examples", ["暫無範例"])])
                sop = "\n".join([f"- {s}" for s in type_info.get("sop", ["暫無建議"])])

                reply_text = (
                    f"【{selected_type}】\n\n"
                    f"描述：\n{description}\n\n"
                    f"常見案例：\n{examples}\n\n"
                    f"防範方式：\n{sop}"
                )
                
                # 檢查文字長度，如果太長則分段或用Flex Message
                if len(reply_text) > 4800: # Line TextSendMessage limit is 5000 chars, leave some buffer
                    reply_text_part1 = reply_text[:4800]
                    reply_text_part2 = reply_text[4800:]
                    line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=reply_text_part1),
                        TextSendMessage(text=reply_text_part2)
                    ])
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
                
                firebase_manager.save_user_interaction(user_id, display_name, text_message, f"回覆關於 {selected_type} 的資訊")

            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=f"抱歉，我還不了解「{selected_type}」這種詐騙類型。您可以試試看「詐騙類型列表」。"))
                firebase_manager.save_user_interaction(user_id, display_name, text_message, f"查詢未知詐騙類型 {selected_type}")
        except IndexError:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="指令格式錯誤，請輸入如：「我想了解 網路購物詐騙」"))
            firebase_manager.save_user_interaction(user_id, display_name, text_message, "指令格式錯誤 (我想了解)")
        return

    elif text_message == "你好" or text_message.lower() == "hello" or text_message.lower() == "hi":
        reply_text = f"{display_name}您好！我是您的防詐騙小幫手，我可以：\n1. 分析您收到的可疑訊息，評估詐騙風險。\n2. 提供常見詐騙類型資訊與防範建議。\n3. 和您玩「選哪顆土豆」小遊戲，練習辨識詐騙！\n\n您可以直接傳送可疑訊息給我，或輸入「詐騙類型列表」或「玩遊戲」來試試看喔！"
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="看看詐騙類型", text="詐騙類型列表")),
            QuickReplyButton(action=MessageAction(label="玩「選土豆」遊戲", text="選哪顆土豆")),
            QuickReplyButton(action=MessageAction(label="我收到可疑訊息", text="我收到這個：")),
        ])
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text, quick_reply=quick_reply))
        firebase_manager.save_user_interaction(user_id, display_name, text_message, "回覆問候語與功能選單")
        return
        
    # 預設使用ChatGPT進行分析
    logger.info(f"將訊息傳送給ChatGPT進行分析: {text_message}")
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

if __name__ == "__main__":
    # load_fraud_tactics() # Moved to be loaded once at startup
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 