import sys
import os

# 添加anti-fraud-clean目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
anti_fraud_clean_dir = os.path.join(current_dir, "anti-fraud-clean")
sys.path.insert(0, anti_fraud_clean_dir)

# 导入子目录中的app
from app import app

# 如果直接运行此文件
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
