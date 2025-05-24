#!/usr/bin/env python3
"""
防詐騙知識庫模組
包含詐騙類型分類、防範措施和小知識
"""

import json
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

def load_fraud_tactics():
    """載入詐騙手法資料"""
    try:
        with open('fraud_tactics.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("fraud_tactics.json 檔案不存在，使用預設資料")
        return get_default_fraud_tactics()
    except Exception as e:
        logger.error(f"載入 fraud_tactics.json 時發生錯誤: {e}")
        return get_default_fraud_tactics()

def get_default_fraud_tactics():
    """取得預設的詐騙手法資料"""
    return {
        "假交友投資詐騙": {
            "description": "透過交友軟體或社群媒體建立感情關係，再誘導投資虛假平台",
            "keywords": ["投資", "獲利", "穩賺", "內線", "老師", "帶單", "跟單", "交友", "感情"],
            "risk_level": "極高",
            "sop": [
                "🚫 絕對不要相信網路上認識的人推薦的投資",
                "🔍 任何投資都要先查證平台是否合法",
                "🌐 可到金管會網站查詢合法投資平台",
                "🛡️ 不要下載來路不明的投資APP",
                "💡 記住：天下沒有穩賺不賠的投資"
            ]
        },
        "假網購詐騙": {
            "description": "建立假的購物網站或在社群媒體刊登假商品廣告",
            "keywords": ["限時優惠", "超低價", "清倉", "免運", "貨到付款", "私訊下單"],
            "risk_level": "高",
            "sop": [
                "🚫 避免在來路不明的網站購物",
                "🔍 購買前先查看賣家評價和商店資訊",
                "🌐 使用有保障的付款方式",
                "🛡️ 價格過低的商品要特別小心",
                "💡 記住：便宜沒好貨，好貨不便宜"
            ]
        },
        "假冒機構詐騙": {
            "description": "冒充政府機關、銀行、電信公司等要求提供個資或轉帳",
            "keywords": ["健保", "國稅局", "法院", "檢察官", "警察", "銀行", "信用卡", "帳戶異常"],
            "risk_level": "極高",
            "sop": [
                "🚫 政府機關不會電話要求轉帳或提供密碼",
                "🔍 接到可疑電話要掛斷後主動回撥官方電話確認",
                "🌐 可撥打165反詐騙專線查證",
                "🛡️ 不要透露個人資料和帳戶資訊",
                "💡 記住：真的公務員不會要你轉帳"
            ]
        },
        "假親友急難詐騙": {
            "description": "冒充親友聲稱遇到緊急狀況需要金錢協助",
            "keywords": ["急用錢", "出車禍", "住院", "被關", "手機壞了", "換號碼"],
            "risk_level": "高",
            "sop": [
                "🚫 不要立即匯款，先確認對方身份",
                "🔍 用其他方式聯絡當事人確認",
                "🌐 詢問只有真正親友才知道的事情",
                "🛡️ 要求視訊通話或當面確認",
                "💡 記住：真正的親友不會只用訊息要錢"
            ]
        },
        "假求職詐騙": {
            "description": "刊登假的高薪工作機會，要求先繳費或提供個資",
            "keywords": ["高薪", "在家工作", "輕鬆賺錢", "保證錄取", "先繳費", "保證金"],
            "risk_level": "中高",
            "sop": [
                "🚫 正當工作不會要求先繳錢",
                "🔍 查證公司是否真實存在",
                "🌐 到勞動部網站查詢合法職缺",
                "🛡️ 面試地點要選在正當場所",
                "💡 記住：天下沒有免費的午餐"
            ]
        }
    }

def get_fraud_features(fraud_type, fraud_message):
    """取得特定詐騙類型的特徵和建議"""
    fraud_tactics = load_fraud_tactics()
    
    if fraud_type in fraud_tactics:
        fraud_info = fraud_tactics[fraud_type]
        return {
            "type": fraud_type,
            "description": fraud_info["description"],
            "risk_level": fraud_info["risk_level"],
            "prevention_tips": fraud_info["sop"],
            "keywords": fraud_info["keywords"]
        }
    
    # 如果找不到特定類型，返回通用建議
    return {
        "type": "一般詐騙",
        "description": "可疑的詐騙訊息",
        "risk_level": "中",
        "prevention_tips": [
            "🚫 不要輕易相信陌生人的訊息",
            "🔍 遇到可疑訊息要多方查證",
            "🌐 可撥打165反詐騙專線諮詢",
            "🛡️ 保護個人資料不外洩",
            "💡 記住：小心駛得萬年船"
        ],
        "keywords": []
    }

def get_anti_fraud_tips():
    """取得防詐騙小知識"""
    tips = [
        "💡 記住165反詐騙專線，遇到可疑狀況立即撥打！",
        "🚫 任何要求先付錢的工作機會都要小心，正當工作不會要求先繳費！",
        "🔍 網路購物時要選擇有保障的付款方式，避免使用來路不明的網站！",
        "🌐 政府機關不會透過電話要求提供密碼或轉帳，接到這種電話要立即掛斷！",
        "🛡️ 投資理財要透過合法管道，可到金管會網站查詢合法業者！",
        "💰 天下沒有穩賺不賠的投資，高報酬必定伴隨高風險！",
        "📱 不要隨意下載來路不明的APP，特別是投資或借貸相關的！",
        "👥 遇到親友急需用錢的訊息，要用其他方式確認身份再行動！",
        "🎯 便宜沒好貨，價格過低的商品要特別小心是否為詐騙！",
        "🔐 個人資料要妥善保管，不要隨意提供給陌生人！"
    ]
    
    return tips

def get_random_anti_fraud_tip():
    """取得隨機的防詐騙小知識"""
    tips = get_anti_fraud_tips()
    import random
    return random.choice(tips)

def analyze_fraud_keywords(message: str) -> List[str]:
    """
    分析訊息中的詐騙關鍵詞
    
    Args:
        message: 要分析的訊息
        
    Returns:
        匹配的詐騙類型列表
    """
    if not message:
        return []
    
    message_lower = message.lower()
    matched_types = []
    
    # 詐騙關鍵詞字典
    fraud_keywords = {
        "投資詐騙": ["投資", "穩賺", "保證獲利", "高報酬", "零風險", "內線消息", "飆股"],
        "購物詐騙": ["限時優惠", "超低價", "免費贈送", "先付款", "貨到付款"],
        "交友詐騙": ["交友", "認識", "寂寞", "陪伴", "借錢", "急用"],
        "假冒詐騙": ["銀行", "客服", "帳戶異常", "凍結", "驗證", "身分證"],
        "中獎詐騙": ["中獎", "恭喜", "獲得", "獎金", "手續費", "稅金"],
        "釣魚詐騙": ["點擊連結", "立即處理", "馬上", "緊急", "驗證碼"]
    }
    
    # 檢查每種詐騙類型的關鍵詞
    for fraud_type, keywords in fraud_keywords.items():
        for keyword in keywords:
            if keyword in message_lower:
                if fraud_type not in matched_types:
                    matched_types.append(fraud_type)
                break
    
    return matched_types

def get_risk_level_color(risk_level):
    """根據風險等級取得對應顏色"""
    color_map = {
        "極高": "#FF0000",  # 紅色
        "高": "#FF6600",    # 橙色  
        "中高": "#FF9900",  # 橙黃色
        "中": "#FFCC00",    # 黃色
        "低": "#00CC00",    # 綠色
        "極低": "#00FF00"   # 亮綠色
    }
    return color_map.get(risk_level, "#FFCC00")  # 預設黃色

def get_risk_level_emoji(risk_level):
    """根據風險等級取得對應emoji"""
    emoji_map = {
        "極高": "🚨",
        "高": "⚠️", 
        "中高": "⚠️",
        "中": "⚡",
        "低": "✅",
        "極低": "✅"
    }
    return emoji_map.get(risk_level, "⚡")  # 預設警告符號 