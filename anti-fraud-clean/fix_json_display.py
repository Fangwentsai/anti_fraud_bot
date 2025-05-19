import json
import logging

logger = logging.getLogger(__name__)

def clean_json_value(value):
    """
    清理可能是 JSON 格式的字符串值
    
    Args:
        value: 可能是 JSON 格式的字符串
        
    Returns:
        清理後的字符串
    """
    if not isinstance(value, str):
        return value
        
    if (value.startswith('{') and value.endswith('}')) or (value.startswith('[') and value.endswith(']')):
        try:
            # 嘗試解析 JSON
            parsed_json = json.loads(value)
            
            # 如果是字典，提取可用字段
            if isinstance(parsed_json, dict):
                # 優先嘗試這些常見字段
                for field in ["explanation", "suggestions", "reason", "purpose", "suggestion"]:
                    if field in parsed_json and isinstance(parsed_json[field], str):
                        return parsed_json[field]
                
                # 如果沒有找到常見字段，提取任意字符串字段
                for json_key, json_value in parsed_json.items():
                    if isinstance(json_value, str) and len(json_value) > 10:
                        return json_value
                
                # 如果沒有找到合適的字段，將整個 JSON 格式化為可讀文本
                return '\n'.join([f"{k}: {v}" for k, v in parsed_json.items() if v])
        except json.JSONDecodeError:
            # 如果不是有效的 JSON，移除花括號並格式化
            return value.strip('{}[]').replace('"', '').replace(',', '\n')
    
    return value

def fix_url_analysis_result(analysis_result):
    """
    修復 URL 分析結果中的 JSON 格式問題
    
    Args:
        analysis_result: 原始分析結果字典
        
    Returns:
        修復後的分析結果字典
    """
    # 複製一份，避免修改原始數據
    fixed_result = analysis_result.copy()
    
    # 修復各個字段
    for key, value in fixed_result.items():
        fixed_result[key] = clean_json_value(value)
    
    # 特別處理 raw_response 字段
    if "raw_response" in fixed_result:
        raw_response = fixed_result["raw_response"]
        # 檢查是否為 JSON 格式
        if (isinstance(raw_response, str) and 
            ((raw_response.startswith('{') and raw_response.endswith('}')) or 
             (raw_response.startswith('[') and raw_response.endswith(']')))):
            try:
                parsed_json = json.loads(raw_response)
                # 從 JSON 中提取字段
                if isinstance(parsed_json, dict):
                    # 提取關鍵信息填充到主字段
                    if "explanation" in parsed_json and not fixed_result.get("reason"):
                        fixed_result["reason"] = parsed_json["explanation"]
                    if "suggestions" in parsed_json and not fixed_result.get("suggestion"):
                        fixed_result["suggestion"] = parsed_json["suggestions"]
                    if "risk_level" in parsed_json and not fixed_result.get("risk_level"):
                        fixed_result["risk_level"] = parsed_json["risk_level"]
                # 刪除 raw_response，因為我們已經提取了有用信息
                del fixed_result["raw_response"]
            except json.JSONDecodeError:
                # 保留但清理格式
                fixed_result["raw_response"] = raw_response.strip('{}[]').replace('"', '').replace(',', '\n')
    
    # 確保風險等級有值
    if not fixed_result.get("risk_level") or fixed_result.get("risk_level") == "":
        fixed_result["risk_level"] = "不確定"
    
    # 確保其他必要字段有值
    if not fixed_result.get("reason"):
        fixed_result["reason"] = "無具體原因說明"
    if not fixed_result.get("purpose"):
        fixed_result["purpose"] = "未提供網站用途資訊"
    if not fixed_result.get("suggestion"):
        fixed_result["suggestion"] = "請謹慎使用，如有疑慮請勿點擊"
    
    return fixed_result 