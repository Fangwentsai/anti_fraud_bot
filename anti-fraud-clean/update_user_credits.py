#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore
import datetime

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_firebase():
    """初始化Firebase連接"""
    try:
        # 檢查是否有服務賬號密鑰文件
        service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase-key.json')
        
        if os.path.exists(service_account_path):
            # 使用服務賬號密鑰文件
            cred = credentials.Certificate(service_account_path)
            app = firebase_admin.initialize_app(cred)
        else:
            # 嘗試使用環境變量中的Firebase憑證
            firebase_credentials = os.environ.get('FIREBASE_CREDENTIALS')
            if firebase_credentials:
                try:
                    cred_dict = json.loads(firebase_credentials)
                    cred = credentials.Certificate(cred_dict)
                    app = firebase_admin.initialize_app(cred)
                except json.JSONDecodeError:
                    logger.error("無法解析環境變量中的Firebase憑證JSON")
                    return None
            else:
                logger.error("找不到Firebase憑證。請提供服務賬號密鑰文件或設置FIREBASE_CREDENTIALS環境變量")
                return None
        
        # 初始化Firestore
        db = firestore.client()
        logger.info("Firebase初始化成功")
        return db
    
    except Exception as e:
        logger.error(f"Firebase初始化失敗: {e}")
        return None

def update_all_users_credits(db, initial_credits=5):
    """為所有用戶添加或更新analysis_credits欄位"""
    if not db:
        logger.error("Firebase未初始化，無法更新用戶分析次數")
        return
    
    try:
        # 獲取所有用戶
        users_ref = db.collection('users')
        users = users_ref.stream()
        
        updated_count = 0
        for user_doc in users:
            user_id = user_doc.id
            user_data = user_doc.to_dict()
            
            # 檢查是否已有analysis_credits欄位
            if 'analysis_credits' not in user_data:
                # 添加欄位
                users_ref.document(user_id).set({
                    'analysis_credits': initial_credits,
                    'last_updated': datetime.datetime.now()
                }, merge=True)
                updated_count += 1
                logger.info(f"已為用戶 {user_id} 添加analysis_credits={initial_credits}")
        
        logger.info(f"完成！已更新 {updated_count} 個用戶")
    
    except Exception as e:
        logger.error(f"更新用戶分析次數失敗: {e}")

def main():
    """主函數"""
    print("開始更新用戶分析次數...")
    db = initialize_firebase()
    if db:
        update_all_users_credits(db)
    else:
        print("初始化Firebase失敗，無法繼續")

if __name__ == "__main__":
    main() 