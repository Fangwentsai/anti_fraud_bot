import json
import logging
import sys

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 從 fix_json_display.py 導入修復函數
try:
    from fix_json_display import fix_url_analysis_result, clean_json_value
    logger.info("成功導入 fix_json_display 模塊")
except ImportError:
    logger.error("無法導入 fix_json_display 模塊")
    sys.exit(1)

# 測試數據 - 包含 JSON 格式的分析結果
test_data = {
    "risk_level": "不確定",
    "reason": '{  "risk_level": "中",  "fraud_type": "可能的釣魚網站或詐騙網站",  "explanation": "該網址使用了非主流的二級域名「soybeanmob.com」，且網址中包含「#news」這類片段，可能用於偽裝或誘導用戶點擊。訊息來自名為「傑西蔡」的發送者，但無法確認其真實身份，且沒有提供任何官方認證或安全保證。雖然目前沒有明顯的緊急感或威脅，也未見明顯的高報酬誘惑，但此類不明來源的網站仍有可能誘導用戶輸入個人資料或進行不安全操作，存在一定風險。建議用戶保持警惕，避免隨意點擊或輸入敏感資訊。",  "suggestions": "建議用戶不要輕易點擊該連結，尤其不要在該網站輸入任何個人或金融資料。如已點擊，應注意帳戶安全，並可透過官方管道核實該網站真偽。遇到可疑訊息時，建議撥打165反詐騙專線尋求協助。",  "is_emerging": false}',
    "purpose": "未提供網站用途資訊",
    "suggestion": "建議：\n請保持警惕，如有疑問可諮詢165反詐騙專線。",
    "raw_response": '{  "risk_level": "中",  "fraud_type": "可能的釣魚網站或詐騙網站",  "explanation": "該網址使用了非主流的二級域名「soybeanmob.com」，且網址中包含「#news」這類片段，可能用於偽裝或誘導用戶點擊。訊息來自名為「傑西蔡」的發送者，但無法確認其真實身份，且沒有提供任何官方認證或安全保證。雖然目前沒有明顯的緊急感或威脅，也未見明顯的高報酬誘惑，但此類不明來源的網站仍有可能誘導用戶輸入個人資料或進行不安全操作，存在一定風險。建議用戶保持警惕，避免隨意點擊或輸入敏感資訊。",  "suggestions": "建議用戶不要輕易點擊該連結，尤其不要在該網站輸入任何個人或金融資料。如已點擊，應注意帳戶安全，並可透過官方管道核實該網站真偽。遇到可疑訊息時，建議撥打165反詐騙專線尋求協助。",  "is_emerging": false}'
}

def test_json_fix():
    """測試修復 JSON 格式的功能"""
    logger.info("原始數據:")
    for key, value in test_data.items():
        logger.info(f"{key}: {value[:50]}..." if len(str(value)) > 50 else f"{key}: {value}")
    
    # 使用修復函數處理
    fixed_result = fix_url_analysis_result(test_data)
    
    logger.info("\n修復後數據:")
    for key, value in fixed_result.items():
        logger.info(f"{key}: {value[:50]}..." if len(str(value)) > 50 else f"{key}: {value}")
    
    # 檢查結果
    assert "raw_response" not in fixed_result, "raw_response 應該被移除"
    assert fixed_result["risk_level"] == "中", "風險等級應該為中"
    assert "soybeanmob.com" in fixed_result["reason"], "原因應該包含網址信息"
    assert "不要輕易點擊" in fixed_result["suggestion"], "建議應該包含警告信息"
    
    logger.info("測試通過!")

def test_clean_json_value():
    """測試清理 JSON 值的功能"""
    test_values = [
        '{"explanation": "這是一個測試", "risk": "高"}',
        '{"random_key": "這是隨機內容", "details": "更多內容"}',
        'not a json string',
        '{"invalid json',
        123,
        None
    ]
    
    logger.info("\n測試 clean_json_value 函數:")
    for value in test_values:
        cleaned = clean_json_value(value)
        logger.info(f"原始: {value}")
        logger.info(f"清理後: {cleaned}")
        logger.info("---")
    
    logger.info("測試完成!")

if __name__ == "__main__":
    logger.info("開始測試 URL 分析 JSON 修復功能")
    test_json_fix()
    test_clean_json_value()
    logger.info("所有測試完成!") 