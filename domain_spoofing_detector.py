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
            domain_without_www = domain[4:] if domain.startswith('www.') else domain
            
            # 創建標準化的安全網域列表（包含www和非www版本）
            normalized_safe_domains = set()
            for safe_domain in safe_domains.keys():
                safe_domain_lower = safe_domain.lower()
                normalized_safe_domains.add(safe_domain_lower)
                
                # 添加www和非www版本
                if safe_domain_lower.startswith('www.'):
                    normalized_safe_domains.add(safe_domain_lower[4:])
                else:
                    normalized_safe_domains.add('www.' + safe_domain_lower)
            
            # 檢查是否本身就是白名單網域（包含www變體）
            if domain in normalized_safe_domains or domain_without_www in normalized_safe_domains:
                continue  # 這是正常的白名單網域，跳過
            
            # 檢查每個白名單網域
            for safe_domain in safe_domains.keys():
                safe_domain_lower = safe_domain.lower()
                safe_domain_without_www = safe_domain_lower[4:] if safe_domain_lower.startswith('www.') else safe_domain_lower
                
                # 跳過完全相同的網域（包含www變體）
                if (domain == safe_domain_lower or 
                    domain == safe_domain_without_www or 
                    domain_without_www == safe_domain_lower or 
                    domain_without_www == safe_domain_without_www):
                    continue
                
                # 跳過合法的子網域（例如 mail.google.com, maps.google.com）
                if (domain.endswith('.' + safe_domain_lower) or 
                    domain.endswith('.' + safe_domain_without_www)):
                    continue
                
                # 跳過已知的合法變體（避免誤報）
                if _is_legitimate_variant(domain_without_www, safe_domain_without_www, safe_domains):
                    continue
                
                # 檢測各種變形手法（使用去除www的版本進行比較）
                spoofing_detected = False
                spoofing_type = ""
                
                # 1. 字元替換攻擊 (例如 google.com -> goog1e.com, googlе.com)
                if _is_character_substitution(domain_without_www, safe_domain_without_www):
                    spoofing_detected = True
                    spoofing_type = "字元替換"
                
                # 2. 插入額外字元 (例如 google.com -> google-tw.com, google.com.tw)
                elif _is_character_insertion(domain_without_www, safe_domain_without_www):
                    spoofing_detected = True
                    spoofing_type = "插入額外字元"
                
                # 3. 網域後綴變形 (例如 google.com -> google.com.tw, google-tw.com)
                elif _is_domain_suffix_spoofing(domain_without_www, safe_domain_without_www):
                    spoofing_detected = True
                    spoofing_type = "網域後綴變形"
                
                # 4. 同音字或相似字攻擊 (例如 google.com -> goog1e.com)
                elif _is_homograph_attack(domain_without_www, safe_domain_without_www):
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

def _is_legitimate_variant(domain, safe_domain, all_safe_domains):
    """檢查是否為合法的網域變體，避免誤報"""
    # 將所有安全網域轉為小寫列表
    safe_domain_list = [d.lower() for d in all_safe_domains.keys()]
    
    # 如果檢測的網域本身就在白名單中，則為合法
    if domain in safe_domain_list:
        return True
    
    # 已知的合法網域對（避免互相誤報）
    legitimate_pairs = [
        ('google.com', 'google.com.tw'),
        ('pchome.com.tw', 'ithome.com.tw'),  # 這兩個是不同的合法網站
        ('shopee.tw', 'shopee.com'),
        ('yahoo.com', 'yahoo.com.tw'),
        ('microsoft.com', 'office.com'),
        ('facebook.com', 'instagram.com'),  # 同公司但不同服務
    ]
    
    # 檢查是否為已知的合法對
    for pair in legitimate_pairs:
        if (domain == pair[0] and safe_domain == pair[1]) or (domain == pair[1] and safe_domain == pair[0]):
            return True
    
    # 檢查是否為同一網站的不同頂級域名
    domain_parts = domain.split('.')
    safe_parts = safe_domain.split('.')
    
    if len(domain_parts) >= 2 and len(safe_parts) >= 2:
        # 比較主要網域名稱（去除頂級域名）
        domain_main = '.'.join(domain_parts[:-1])
        safe_main = '.'.join(safe_parts[:-1])
        
        # 如果主要部分相同，可能是合法的地區變體
        if domain_main == safe_main:
            return True
    
    return False

def _is_character_substitution(suspicious_domain, safe_domain):
    """檢測字元替換攻擊 - 改進版"""
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
    
    # 改進的相似度檢測
    distance = levenshtein_distance(suspicious_domain, safe_domain)
    length_diff = abs(len(suspicious_domain) - len(safe_domain))
    max_length = max(len(suspicious_domain), len(safe_domain))
    
    # 動態調整閾值：較短的網域允許較少的差異
    if max_length <= 10:
        max_distance = 1
    elif max_length <= 15:
        max_distance = 2
    else:
        max_distance = 3
    
    # 檢查是否為字元替換攻擊
    if distance <= max_distance and length_diff <= 1:
        # 額外檢查：避免誤判完全不相關的網域
        # 計算最長公共子序列
        def lcs_length(s1, s2):
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        lcs_len = lcs_length(suspicious_domain, safe_domain)
        similarity_ratio = lcs_len / max_length
        
        # 要求至少70%的字元相似度
        return similarity_ratio >= 0.7
    
    return False

def _is_character_insertion(suspicious_domain, safe_domain):
    """檢測字元插入攻擊 - 改進版"""
    # 移除 www. 前綴
    if suspicious_domain.startswith('www.'):
        suspicious_domain = suspicious_domain[4:]
    if safe_domain.startswith('www.'):
        safe_domain = safe_domain[4:]
    
    # 分解網域名稱
    safe_parts = safe_domain.split('.')
    suspicious_parts = suspicious_domain.split('.')
    
    # 檢查基礎網域名稱的插入攻擊
    safe_base = safe_parts[0]  # 例如 google, pchome, cht
    suspicious_base = suspicious_parts[0]  # 例如 google-search, pchome-24h, cht-tw
    
    # 1. 檢查連字符插入 (google -> google-search, pchome -> pchome-24h)
    if '-' in suspicious_base and safe_base in suspicious_base:
        # 移除連字符後檢查是否包含原始網域
        base_without_dash = suspicious_base.replace('-', '')
        if safe_base in base_without_dash:
            return True
        
        # 檢查連字符前的部分是否與安全網域匹配
        dash_parts = suspicious_base.split('-')
        if dash_parts[0] == safe_base:
            return True
    
    # 2. 檢查數字插入 (pchome -> pchome24h)
    import re
    # 移除數字後檢查
    base_without_numbers = re.sub(r'\d+', '', suspicious_base)
    if base_without_numbers == safe_base:
        return True
    
    # 3. 檢查常見後綴插入
    common_suffixes = ['search', 'official', 'secure', 'login', 'bank', 'pay', 'tw', 'taiwan', '24h', 'shop', 'store']
    for suffix in common_suffixes:
        if suspicious_base == safe_base + suffix:
            return True
        if suspicious_base == safe_base + '-' + suffix:
            return True
    
    # 3.5. 檢查字母插入 (apple -> apples, google -> googles)
    # 檢查是否在原網域後加了單個或少數字母
    if suspicious_base.startswith(safe_base) and len(suspicious_base) > len(safe_base):
        added_part = suspicious_base[len(safe_base):]
        # 常見的字母添加（複數形式、常見後綴等）
        if len(added_part) <= 3 and added_part.isalpha():
            return True
    
    # 4. 檢查子網域中的變形攻擊（新增）
    # 例如 event.liontravel-tw.com 中的 liontravel-tw 是對 liontravel 的變形
    if len(suspicious_parts) >= 2:
        for i, suspicious_part in enumerate(suspicious_parts):
            # 檢查每個部分是否包含對安全網域的變形
            if '-' in suspicious_part and safe_base in suspicious_part:
                # 檢查連字符前的部分是否與安全網域匹配
                dash_parts = suspicious_part.split('-')
                if dash_parts[0] == safe_base:
                    return True
            
            # 檢查是否為安全網域加上常見後綴
            for suffix in common_suffixes:
                if suspicious_part == safe_base + '-' + suffix:
                    return True
                if suspicious_part == safe_base + suffix:
                    return True
    
    # 5. 原有的模式檢測
    insertion_patterns = [
        f"{safe_domain.split('.')[0]}-tw.{'.'.join(safe_domain.split('.')[1:])}",
        f"{safe_domain.split('.')[0]}-taiwan.{'.'.join(safe_domain.split('.')[1:])}",
        f"{safe_domain}.tw",
        f"tw.{safe_domain}",
        f"taiwan.{safe_domain}",
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
    """檢測同音字或相似字元攻擊 - 改進版"""
    # 擴展的字元替換對應表
    homograph_map = {
        'o': ['0', 'ο', 'о', 'ø', 'ö', 'ò', 'ó', 'ô', 'õ'],  # 英文o及各種變形
        'a': ['а', 'α', 'à', 'á', 'â', 'ã', 'ä', 'å', '@'],  # 英文a及各種變形
        'e': ['е', 'ε', 'è', 'é', 'ê', 'ë', '3'],  # 英文e及各種變形
        'i': ['1', 'l', 'і', 'ι', 'ì', 'í', 'î', 'ï', '!', '|'],  # 英文i及各種變形
        'l': ['1', 'i', 'ι', '|', 'ł'],  # 英文l及各種變形
        'n': ['η', 'ñ'],  # 英文n及各種變形
        'p': ['ρ'],  # 英文p及各種變形
        'c': ['с', 'ç', '©'],  # 英文c及各種變形
        'x': ['х', '×'],  # 英文x及各種變形
        'u': ['υ', 'ù', 'ú', 'û', 'ü'],  # 英文u及各種變形
        's': ['$', '5', 'ş'],  # 英文s及各種變形
        'g': ['9', 'ğ'],  # 英文g及各種變形
        't': ['7', 'ţ'],  # 英文t及各種變形
        'b': ['6', 'β'],  # 英文b及各種變形
        'd': ['ð'],  # 英文d及各種變形
        'f': ['ƒ'],  # 英文f及各種變形
        'h': ['ħ'],  # 英文h及各種變形
        'k': ['κ'],  # 英文k及各種變形
        'm': ['μ'],  # 英文m及各種變形
        'r': ['ρ', 'ř'],  # 英文r及各種變形
        'v': ['ν'],  # 英文v及各種變形
        'w': ['ω'],  # 英文w及各種變形
        'y': ['ý', 'ÿ'],  # 英文y及各種變形
        'z': ['ζ', 'ž'],  # 英文z及各種變形
    }
    
    # 檢查每個字元是否被替換
    if len(suspicious_domain) != len(safe_domain):
        return False
    
    substitution_count = 0
    for i, (sus_char, safe_char) in enumerate(zip(suspicious_domain, safe_domain)):
        if sus_char != safe_char:
            # 檢查是否為已知的相似字元替換
            if safe_char.lower() in homograph_map:
                if sus_char in homograph_map[safe_char.lower()]:
                    substitution_count += 1
                else:
                    return False  # 不是已知的相似字元替換
            else:
                return False  # 字元不在替換表中
    
    # 如果有1-3個字元被替換，認為是相似字元攻擊
    return 1 <= substitution_count <= 3 