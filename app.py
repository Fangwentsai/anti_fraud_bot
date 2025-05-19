import sys
import os

# 添加anti-fraud-clean目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
anti_fraud_clean_dir = os.path.join(current_dir, "anti-fraud-clean")
sys.path.insert(0, anti_fraud_clean_dir)

# 从子目录导入所有内容
from anti_fraud_clean_app import app, line_bot_api, handler

# 这个文件只作为入口点，所有的功能都在anti_fraud_clean_app.py中
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000))) 