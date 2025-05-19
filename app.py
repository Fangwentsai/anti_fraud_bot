import sys
import os
from flask import Flask, request, abort, render_template, jsonify
import json

# 添加anti-fraud-clean目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
anti_fraud_clean_dir = os.path.join(current_dir, "anti-fraud-clean")
sys.path.insert(0, anti_fraud_clean_dir)

# 创建Flask应用
app = Flask(__name__, 
            template_folder=os.path.join(anti_fraud_clean_dir, "templates"),
            static_folder=os.path.join(anti_fraud_clean_dir, "static"))

# 导入子目录中的firebase_manager和其他所需模块
from firebase_manager import FirebaseManager
firebase_manager = FirebaseManager()

# 加载诈骗类型数据
fraud_tactics_path = os.path.join(anti_fraud_clean_dir, "fraud_tactics.json")
with open(fraud_tactics_path, 'r', encoding='utf-8') as f:
    fraud_tactics_data = json.load(f)

@app.route("/", methods=["GET"])
def index():
    # 传递fraud_types变量给模板
    return render_template("index.html", fraud_types=fraud_tactics_data)

@app.route("/callback", methods=["POST"])
def callback():
    # 这里只是一个简单的回调处理，具体业务逻辑可以在部署成功后再完善
    return "OK"

@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return "OK"

# 如果直接运行此文件
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000))) 