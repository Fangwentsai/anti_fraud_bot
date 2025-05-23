"""
網域變形攻擊檢測模組
用於檢測模仿白名單網域的可疑網址
"""

import re
from urllib.parse import urlparse

def detect_domain_spoofing(url_or_message, safe_domains):
    """
    檢測網域變形攻擊 - 識別模仿白名單網域的可疑網址
    
    Args:
        url_or_message: 要檢測的URL或包含URL的訊息
        safe_domains: 白名單網域字典
        
    Returns:
        dict: {
            'is_spoofed': bool,  # 是否為變形網域
            'original_domain': str,  # 被模仿的原始網域
            'spoofed_domain': str,  # 可疑的變形網域
            'spoofing_type': str,  # 變形類型
            'risk_explanation': str  # 風險說明
        }
    """
    # 提取URL
    url_pattern = re.compile(r'https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}[^\s]*')
    urls = url_pattern.findall(url_or_message)
    
    if not urls:
        return {'is_spoofed': False}
    
    for url in urls:
        # 標準化URL
        if not url.startswith(('http://', 'https://')):
            if url.startswith('www.'):
                url = 'https://' + url
            else:
                url = 'https://' + url
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 移除 www. 前綴進行比較
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # 檢查每個白名單網域
            for safe_domain in safe_domains.keys():
                safe_domain_lower = safe_domain.lower()
                
                # 跳過完全相同的網域（這是正常的）
                if domain == safe_domain_lower:
                    continue
                
                # 跳過合法的子網域（例如 mail.google.com, maps.google.com）
                if domain.endswith('.' + safe_domain_lower):
                    continue
                
                # 檢測各種變形手法
                spoofing_detected = False
                spoofing_type = ""
                
                # 1. 字元替換攻擊 (例如 google.com -> goog1e.com, googlе.com)
                if _is_character_substitution(domain, safe_domain_lower):
                    spoofing_detected = True
                    spoofing_type = "字元替換"
                
                # 2. 插入額外字元 (例如 google.com -> google-tw.com, google.com.tw)
                elif _is_character_insertion(domain, safe_domain_lower):
                    spoofing_detected = True
                    spoofing_type = "插入額外字元"
                
                # 3. 網域後綴變形 (例如 google.com -> google.com.tw, google-tw.com)
                elif _is_domain_suffix_spoofing(domain, safe_domain_lower):
                    spoofing_detected = True
                    spoofing_type = "網域後綴變形"
                
                # 4. 同音字或相似字攻擊 (例如 google.com -> goog1e.com)
                elif _is_homograph_attack(domain, safe_domain_lower):
                    spoofing_detected = True
                    spoofing_type = "相似字元攻擊"
                
                if spoofing_detected:
                    site_description = safe_domains.get(safe_domain, "知名網站")
                    return {
                        'is_spoofed': True,
                        'original_domain': safe_domain,
                        'spoofed_domain': domain,
                        'spoofing_type': spoofing_type,
                        'risk_explanation': f"⚠️ 高風險警告！\n\n這個網址 {domain} 疑似模仿正牌的 {safe_domain} ({site_description})。\n\n詐騙集團常用這種手法製作假網站來騙取個人資料或信用卡資訊。\n\n🚨 千萬不要在這個網站輸入任何個人資料、密碼或信用卡號碼！"
                    }
        
        except Exception as e:
            # URL解析失敗，繼續檢查下一個
            continue
    
    return {'is_spoofed': False}

def _is_character_substitution(suspicious_domain, safe_domain):
    """檢測字元替換攻擊"""
    # 計算編輯距離（Levenshtein distance）
    def levenshtein_distance(s1, s2):
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    # 如果編輯距離很小且長度相近，可能是字元替換
    distance = levenshtein_distance(suspicious_domain, safe_domain)
    length_diff = abs(len(suspicious_domain) - len(safe_domain))
    
    return distance <= 2 and length_diff <= 1

def _is_character_insertion(suspicious_domain, safe_domain):
    """檢測字元插入攻擊"""
    # 常見的插入模式
    insertion_patterns = [
        f"{safe_domain.split('.')[0]}-tw.{'.'.join(safe_domain.split('.')[1:])}",  # google.com -> google-tw.com
        f"{safe_domain.split('.')[0]}-taiwan.{'.'.join(safe_domain.split('.')[1:])}",  # google.com -> google-taiwan.com
        f"{safe_domain}.tw",  # google.com -> google.com.tw
        f"tw.{safe_domain}",  # google.com -> tw.google.com
        f"taiwan.{safe_domain}",  # google.com -> taiwan.google.com
    ]
    
    return suspicious_domain in insertion_patterns

def _is_domain_suffix_spoofing(suspicious_domain, safe_domain):
    """檢測網域後綴變形"""
    # 檢查是否包含完整的安全網域作為前綴
    if suspicious_domain.startswith(safe_domain + '.'):
        # 例如 cht.com.tw.fake.com 包含 cht.com.tw.
        return True
    
    safe_base = safe_domain.split('.')[0]  # 例如從 google.com 取得 google
    suspicious_base = suspicious_domain.split('.')[0]  # 例如從 google-tw.com 取得 google-tw
    
    # 檢查是否在基礎網域名稱後加了額外字元
    if suspicious_base.startswith(safe_base) and len(suspicious_base) > len(safe_base):
        added_part = suspicious_base[len(safe_base):]
        # 常見的添加模式
        common_additions = ['-tw', '-taiwan', '-official', '-secure', '-login', '-bank', '-pay']
        return any(added_part.startswith(addition) for addition in common_additions)
    
    return False

def _is_homograph_attack(suspicious_domain, safe_domain):
    """檢測同音字或相似字元攻擊"""
    # 常見的字元替換對應
    homograph_map = {
        'o': ['0', 'ο', 'о'],  # 英文o, 數字0, 希臘字母omicron, 俄文o
        'a': ['а', 'α'],  # 英文a, 俄文a, 希臘字母alpha
        'e': ['е', 'ε'],  # 英文e, 俄文e, 希臘字母epsilon
        'i': ['1', 'l', 'і', 'ι'],  # 英文i, 數字1, 英文l, 俄文i, 希臘字母iota
        'l': ['1', 'i', 'ι'],  # 英文l, 數字1, 英文i, 希臘字母iota
        'n': ['η'],  # 英文n, 希臘字母eta
        'p': ['ρ'],  # 英文p, 希臘字母rho
        'c': ['с'],  # 英文c, 俄文c
        'x': ['х'],  # 英文x, 俄文x
    }
    
    # 生成可能的同音字變形
    def generate_homograph_variants(domain):
        variants = [domain]
        for char, replacements in homograph_map.items():
            new_variants = []
            for variant in variants:
                for replacement in replacements:
                    new_variants.append(variant.replace(char, replacement))
            variants.extend(new_variants)
        return variants
    
    safe_variants = generate_homograph_variants(safe_domain)
    return suspicious_domain in safe_variants 