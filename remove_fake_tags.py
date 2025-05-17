#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import random
import string

def generate_random_bank_name():
    """生成随机的银行名称"""
    banks = ["中國信託銀行", "國泰世華銀行", "台灣銀行", "兆豐銀行", "玉山銀行", 
             "合作金庫", "台北富邦銀行", "彰化銀行", "第一銀行", "永豐銀行",
             "凱基銀行", "臺灣土地銀行", "華南銀行", "日盛銀行", "聯邦銀行"]
    return random.choice(banks)

def generate_random_account():
    """生成随机的银行账号（13-16位数字）"""
    length = random.randint(13, 16)
    return ''.join(random.choice(string.digits) for _ in range(length))

def generate_random_name():
    """生成随机的中文姓名"""
    surnames = ["王", "李", "張", "劉", "陳", "楊", "黃", "趙", "吳", "周", "林", "蔡", "鄭", "謝", "許", "鄧", "馬", "洪"]
    names = ["小明", "小華", "小英", "家豪", "詩涵", "雅婷", "宏偉", "佳怡", "建宏", "美玲", "俊傑", "雅雯", "志明", "淑芬", "嘉宏", "佳穎"]
    return random.choice(surnames) + random.choice(names)

def generate_random_url():
    """生成随机的网址（看起来合法但是假的）"""
    domains = ["com", "org", "net", "tw", "com.tw", "org.tw", "gov.tw", "edu.tw"]
    tlds = random.choice(domains)
    
    # 生成看起来合法但实际上是假的域名
    prefixes = ["secure-", "service-", "online-", "web-", "e-", "m-", "app-", "portal-", "tw-", "my-"]
    suffixes = ["service", "online", "web", "secure", "pay", "account", "login", "support", "help", "center"]
    
    # 商业或政府服务相关
    services = ["payment", "banking", "mobile", "telecom", "gov", "tax", "water", "electric", "post", "police", 
                "health", "insurance", "delivery", "express", "shopping", "etag", "cloud", "stream"]
    
    # 随机生成域名组合
    if random.random() < 0.5:  # 50%几率使用前缀
        domain = random.choice(prefixes) + random.choice(services) + "." + tlds
    else:
        domain = random.choice(services) + random.choice(suffixes) + "." + tlds
        
    return domain

def generate_random_phone():
    """生成随机的电话号码"""
    prefixes = ["02", "03", "04", "05", "06", "07", "08", "09"]
    prefix = random.choice(prefixes)
    
    if prefix == "09":  # 手机号码
        return prefix + ''.join(random.choice(string.digits) for _ in range(8))
    else:  # 座机号码
        length = 8 if prefix == "02" else 7  # 台北座机8位，其他7位
        return prefix + '-' + ''.join(random.choice(string.digits) for _ in range(length))

def generate_random_id():
    """生成随机的身分证后四码或验证码"""
    return ''.join(random.choice(string.digits) for _ in range(4))

def generate_random_path():
    """生成随机的路径或地址"""
    districts = ["大安區", "信義區", "中山區", "松山區", "文山區", "北投區", "士林區", "內湖區", 
                "南港區", "萬華區", "中正區", "大同區", "新店區", "板橋區", "中壢區", "新竹市"]
    roads = ["復興路", "中正路", "信義路", "和平東路", "民生路", "光復路", "建國路", "忠孝東路", 
            "仁愛路", "敦化南路", "羅斯福路", "三民路", "中山路", "民權路", "林森路"]
    
    return random.choice(districts) + random.choice(roads) + str(random.randint(1, 300)) + "號"

def remove_fake_tags(json_file, output_file):
    """移除JSON文件中的[假xxx]标记，替换为随机但看起来合理的内容"""
    
    try:
        # 读取JSON文件
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 定义替换模式和对应的生成函数
        replacement_patterns = {
            r'\[假帳號\]': generate_random_account,
            r'\[假帳戶\]': generate_random_account,
            r'\[假銀行\]': generate_random_bank_name,
            r'\[假戶名\]': generate_random_name,
            r'\[假網址\]': generate_random_url,
            r'\[假電話\]': generate_random_phone,
            r'\[假電話號碼\]': generate_random_phone,
            r'\[假帳號後五碼\]': lambda: random.choice(string.digits) + ''.join(random.choice(string.digits) for _ in range(4)),
            r'\[假碼\]': generate_random_id,
            r'\[假電號\]': lambda: ''.join(random.choice(string.digits) for _ in range(11)),
            r'\[假水號\]': lambda: ''.join(random.choice(string.digits) for _ in range(12)),
            r'\[捐款人姓名\]': generate_random_name,
            r'\[某路段\]': generate_random_path,
            r'\[某地段\]': generate_random_path,
            r'\[某公司\]': lambda: random.choice(["台灣大哥大", "宏碁電腦", "中華電信", "鴻海科技", "台積電", "聯發科", "統一企業", "全家便利商店"]),
            r'\[某風水寶地\]': lambda: random.choice(["南投杉林溪", "陽明山", "阿里山", "日月潭", "台東鹿野", "宜蘭礁溪", "花蓮太魯閣"]),
            r'\[某行程\]': lambda: random.choice(["台東三日遊", "墾丁海景行", "阿里山日出團", "台南古蹟之旅", "宜蘭礁溪泡湯行", "花蓮太魯閣健行團"]),
            r'\[假LINE群組連結\]': lambda: "line.me/ti/g/" + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
        }
        
        # 计数器，跟踪替换次数
        replacements_count = 0
        
        # 应用替换模式到文本
        def apply_replacements(text):
            nonlocal replacements_count
            modified_text = text
            # 应用所有替换模式
            for pattern, generator in replacement_patterns.items():
                matches = re.findall(pattern, modified_text)
                for _ in matches:
                    replacement = generator()
                    modified_text = re.sub(pattern, replacement, modified_text, count=1)
                    replacements_count += 1
            return modified_text
        
        # 处理每个题目
        def process_questions(questions):
            for question in questions:
                # 处理嵌套题目
                if "questions" in question and isinstance(question["questions"], list):
                    process_questions(question["questions"])
                    continue
                
                # 处理fraud_message字段
                if "fraud_message" in question:
                    original_message = question["fraud_message"]
                    modified_message = apply_replacements(original_message)
                    
                    # 如果有修改，更新题目
                    if modified_message != original_message:
                        question["fraud_message"] = modified_message
                
                # 处理options中的text字段
                if "options" in question and isinstance(question["options"], list):
                    for option in question["options"]:
                        if "text" in option:
                            original_text = option["text"]
                            modified_text = apply_replacements(original_text)
                            
                            # 如果有修改，更新选项文本
                            if modified_text != original_text:
                                option["text"] = modified_text
        
        # 处理顶层题目
        if "questions" in data and isinstance(data["questions"], list):
            process_questions(data["questions"])
        
        # 保存修改后的JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"完成！共替换了 {replacements_count} 处[假xxx]标记。")
        print(f"修改后的文件已保存为：{output_file}")
        
    except Exception as e:
        print(f"发生错误：{e}")

if __name__ == "__main__":
    input_file = "potato_game_questions.json"
    output_file = "potato_game_questions_clean.json"
    
    remove_fake_tags(input_file, output_file) 