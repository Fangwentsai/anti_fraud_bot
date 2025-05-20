#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging

# 添加目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
anti_fraud_dir = os.path.join(current_dir, "anti-fraud-clean")
sys.path.insert(0, anti_fraud_dir)

# 导入必要的模块
try:
    from firebase_manager import FirebaseManager
    from anti_fraud_clean_app import detect_fraud_with_chatgpt, parse_fraud_analysis
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_analysis(message, user_id=None):
    """
    测试分析功能
    
    Args:
        message: 待分析的消息
        user_id: 用户ID，可选
    """
    try:
        # 初始化Firebase管理器
        firebase_manager = FirebaseManager.get_instance()
        
        # 检查Firebase连接状态
        if not firebase_manager.db:
            print("警告: Firebase连接未成功初始化")
        
        # 进行分析
        print(f"\n测试分析以下消息: \"{message}\"")
        print("-" * 50)
        
        # 调用分析函数
        analysis_result = detect_fraud_with_chatgpt(message, "测试用户", user_id)
        print(f"原始分析结果:\n{analysis_result}")
        
        # 解析分析结果
        try:
            analysis_data = parse_fraud_analysis(analysis_result)
            print("\n解析后的结果:")
            for key, value in analysis_data.items():
                print(f"{key}: {value}")
            
            # 检查是否有次数限制相关的信息
            if "分析受限" in analysis_result or "次数" in analysis_result:
                print("\n检测到次数限制相关信息!")
        except Exception as e:
            print(f"解析分析结果失败: {e}")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")

if __name__ == "__main__":
    # 测试消息
    test_messages = [
        "你好，请问需要分析什么?",
        "请帮我分析这个链接: http://example.com 是否安全?",
        "有人要求我转账5000元到这个账号: 1234567890"
    ]
    
    # 测试的用户ID
    test_user_id = "ed661ab2-ae1f-4a65-ba50-fb0aa6eab92b"  # 使用提供的UUID
    
    for msg in test_messages:
        test_analysis(msg, test_user_id)
        print("\n" + "=" * 70 + "\n") 