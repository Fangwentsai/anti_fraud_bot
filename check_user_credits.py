#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging

# 添加目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
anti_fraud_dir = os.path.join(current_dir, "anti-fraud-clean")
sys.path.insert(0, anti_fraud_dir)

# 导入Firebase管理器
from firebase_manager import FirebaseManager

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_user_credits(user_id):
    """
    检查特定用户的分析次数
    
    Args:
        user_id: 用户ID
    """
    # 初始化Firebase管理器
    firebase_manager = FirebaseManager.get_instance()
    
    try:
        # 获取用户信息
        user_profile = firebase_manager.get_user_profile(user_id)
        
        if user_profile:
            display_name = user_profile.get('display_name', '未知用户')
            
            # 获取用户分析次数
            credits = firebase_manager.get_user_analysis_credits(user_id)
            
            print(f"用户ID: {user_id}")
            print(f"用户名称: {display_name}")
            print(f"剩余分析次数: {credits}")
            
            # 检查Firebase连接状态
            if not firebase_manager.db:
                print("警告: Firebase连接未成功初始化，这可能导致次数显示不正确")
        else:
            print(f"未找到用户ID为 {user_id} 的信息")
    except Exception as e:
        print(f"查询过程中出错: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    else:
        user_id = "ed661ab2-ae1f-4a65-ba50-fb0aa6eab92b"  # 使用提供的UUID作为默认ID
    
    check_user_credits(user_id) 