import os
import json
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
from dotenv import load_dotenv
import openai
import logging
from firebase_manager import FirebaseManager

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
            "受害者收到一封偽裝成監理站的電子郵件，通知有逾期罰單需立即處理，並提供一個看似官方的網址。受害者點擊連結後在假冒的繳費網站輸入信用卡資料，導致信用卡被盜刷3萬多元及手續費。事後發現發件人和網址都不是官方來源。"
        ],
        "sop": [
            "政府機構絕不會以電郵或不明網址傳送通知或罰單",
            "收到疑似官方機構的電子郵件，直接聯繫官方客服查證",
            "不要點擊不明連結、不要輸入個人或信用卡資訊",
            "檢查發信地址是否為官方網域(.gov.tw等)",
            "官方機構不會使用免費郵箱或不明網域",
            "懷疑訊息真實性時，直接聯繫官方客服查證",
            "使用官方APP或直接輸入官網網址，而非通過連結",
            "啟用金融卡或信用卡的交易通知服務",
            "定期檢查銀行和信用卡對帳單",
            "已點擊可疑連結應立即更改密碼並通知相關機構"
        ]
    }
}

# 載入詐騙話術的資料庫
def load_fraud_tactics():
    try:
        with open('fraud_tactics.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"載入詐騙話術資料庫失敗: {e}")
        return {}

# 詐騙話術資料庫
fraud_tactics = load_fraud_tactics()

# 獲取用戶個人資料
def get_user_profile(user_id):
    try:
        profile = line_bot_api.get_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"獲取用戶資料失敗: {e}")
        return None

# 分析詐騙風險並解析結果
def parse_fraud_analysis(analysis_result):
    """
    解析ChatGPT詐騙分析結果，提取風險等級和詐騙類型
    """
    risk_level = None
    fraud_type = None
    
    # 嘗試找出風險評估
    if "風險評估" in analysis_result and ("高" in analysis_result or "中" in analysis_result or "低" in analysis_result):
        if "高風險" in analysis_result:
            risk_level = "高"
        elif "中風險" in analysis_result:
            risk_level = "中"
        elif "低風險" in analysis_result:
            risk_level = "低"
    
    # 嘗試找出詐騙類型
    for fraud in fraud_types.keys():
        if fraud in analysis_result:
            fraud_type = fraud
            break
    
    return risk_level, fraud_type

# ChatGPT檢測詐騙訊息函數
def detect_fraud_with_chatgpt(user_message):
    try:
        # 创建提示，包含用户消息和已知詐騙類型信息
        fraud_info = ""
        for fraud_type, details in fraud_tactics.items():
            if "常見話術" in details:
                fraud_info += f"詐騙類型: {fraud_type}\n"
                fraud_info += "常見話術:\n" + "\n".join([f"- {tactic}" for tactic in details.get("常見話術", [])])
                fraud_info += "\n\n"
        
        prompt = f"""
作為防詐騙顧問，請分析以下訊息是否包含詐騙跡象。參考已知詐騙類型和話術，提供詳細分析。

用戶訊息:
{user_message}

已知詐騙類型和話術:
{fraud_info}

請提供:
1. 詐騙風險評估 (高/中/低)
2. 可能的詐騙類型 (如果有)
3. 識別出的可疑跡象
4. 防範建議和下一步行動
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位專業的防詐騙顧問，協助用戶識別可能的詐騙風險並提供適當建議。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"ChatGPT詐騙檢測失敗: {e}")
        return "無法分析訊息，請嘗試其他方式獲取協助或直接撥打165反詐騙專線。"

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
    return render_template('index.html', fraud_types=fraud_types)

@app.route("/fraud-statistics", methods=['GET'])
def fraud_statistics():
    """顯示詐騙統計數據頁面"""
    stats = firebase_manager.get_fraud_statistics()
    return render_template('statistics.html', stats=stats)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    
    # 獲取用戶個人資料
    profile = get_user_profile(user_id)
    display_name = profile.display_name if profile else "未知用戶"
    
    # 初始化響應變數
    response_text = ""
    is_fraud_related = False
    fraud_type = None
    risk_level = None
    
    if "詐騙類型" in user_message:
        types_text = "目前已收集的詐騙類型有：\n"
        for fraud_type, info in fraud_types.items():
            types_text += f"- {fraud_type}：{info['description']}\n"
        response_text = types_text
    
    elif "分析" in user_message or "檢查" in user_message or "是否詐騙" in user_message:
        # 移除指令部分，只分析主要内容
        content_to_analyze = user_message.replace("分析", "").replace("檢查", "").replace("是否詐騙", "").strip()
        
        if len(content_to_analyze) < 5:
            response_text = "請提供更多內容讓我分析是否含有詐騙跡象。"
        else:
            # 使用ChatGPT進行詐騙分析
            analysis_result = detect_fraud_with_chatgpt(content_to_analyze)
            response_text = analysis_result
            
            # 解析分析結果，判斷是否與詐騙相關
            risk_level, fraud_type = parse_fraud_analysis(analysis_result)
            is_fraud_related = risk_level is not None
    
    elif "我的紀錄" in user_message or "查詢紀錄" in user_message:
        # 獲取用戶詐騙報告歷史
        reports = firebase_manager.get_user_fraud_reports(user_id)
        
        if reports:
            response_text = f"{display_name}的詐騙分析記錄：\n\n"
            for i, report in enumerate(reports, 1):
                response_text += f"{i}. 時間: {report.get('timestamp', '未知')}\n"
                response_text += f"   詐騙類型: {report.get('fraud_type', '未分類')}\n"
                response_text += f"   風險等級: {report.get('risk_level', '未評估')}\n"
                response_text += f"   訊息: {report.get('message', '')[:30]}...\n\n"
        else:
            response_text = f"{display_name}，您目前還沒有詐騙分析記錄。"
        
    elif any(fraud_type in user_message for fraud_type in fraud_types):
        # 找出用戶提到的詐騙類型
        for ft, info in fraud_types.items():
            if ft in user_message:
                fraud_type = ft
                if "案例" in user_message:
                    if info["examples"]:
                        examples_text = f"{ft}的案例：\n"
                        for i, example in enumerate(info["examples"], 1):
                            examples_text += f"{i}. {example}\n"
                        response_text = examples_text
                    else:
                        response_text = f"目前還沒有收集到{ft}的案例，敬請期待。"
                elif "處理方法" in user_message or "SOP" in user_message:
                    if info["sop"]:
                        sop_text = f"{ft}的處理方法：\n"
                        for i, step in enumerate(info["sop"], 1):
                            sop_text += f"{i}. {step}\n"
                        response_text = sop_text
                    else:
                        response_text = f"目前還沒有收集到{ft}的處理方法，敬請期待。"
                else:
                    info_text = f"{ft}：{info['description']}\n\n"
                    info_text += "您可以詢問相關案例或處理方法。"
                    response_text = info_text
                
                # 標記為詐騙相關查詢
                is_fraud_related = True
                break
                    
    else:
        help_text = f"您好，{display_name}！我是防詐騙小助手，可以提供以下協助：\n"
        help_text += "1. 查詢「詐騙類型」列表\n"
        help_text += "2. 輸入特定詐騙類型查看相關資訊\n"
        help_text += "3. 查詢特定詐騙類型的「案例」\n"
        help_text += "4. 查詢特定詐騙類型的「處理方法」或「SOP」\n"
        help_text += "5. 輸入「分析」+訊息內容，檢查是否含有詐騙跡象\n"
        help_text += "6. 輸入「我的紀錄」查看您的詐騙分析歷史\n"
        help_text += "\n若您遇到可疑情況，請立即撥打165反詐騙專線尋求協助！"
        response_text = help_text
    
    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_text)
    )
    
    # 記錄用戶互動
    firebase_manager.save_user_interaction(
        user_id=user_id,
        display_name=display_name,
        message=user_message,
        response=response_text,
        is_fraud_related=is_fraud_related,
        fraud_type=fraud_type,
        risk_level=risk_level
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 