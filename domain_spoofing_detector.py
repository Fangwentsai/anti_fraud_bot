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
            
            # 🚨 新增：專門檢測政府網域變形攻擊
            gov_spoofing_result = _detect_government_domain_spoofing(domain_without_www)
            if gov_spoofing_result['is_spoofed']:
                return gov_spoofing_result
            
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
            
            # 🚨 新增：優先檢查基礎域名相似度（如 cht.tw 與 cht.com.tw）
            domain_parts = domain_without_www.split('.')
            base_domain = domain_parts[0]
            
            # 檢查是否有相同基礎域名的白名單網域
            similar_domains = []
            legitimate_variant_found = False
            
            for safe_domain in safe_domains.keys():
                safe_domain_lower = safe_domain.lower()
                safe_parts = safe_domain_lower.split('.')
                safe_base = safe_parts[0]
                
                # 處理 www 前綴：如果第一部分是 www，取第二部分作為基礎網域
                if safe_base == 'www' and len(safe_parts) > 1:
                    safe_base = safe_parts[1]
                
                # 如果基礎域名相同，檢查是否為合法的變體
                if base_domain == safe_base:
                    # 檢查是否為合法的域名變體（如 cht.tw 是 cht.com.tw 的變體）
                    if _is_legitimate_domain_variant(domain_without_www, safe_domain_lower):
                        legitimate_variant_found = True
                        continue  # 這是合法的域名變體，跳過
                    else:
                        # 基礎域名相同但不是合法變體，記錄為相似域名
                        site_description = safe_domains.get(safe_domain, "知名網站")
                        similar_domains.append({
                            'domain': safe_domain,
                            'description': site_description,
                            'type': '基礎域名相同'
                        })
            
            # 如果找到合法變體，跳過檢測
            if legitimate_variant_found:
                continue
            
            # 如果找到多個相似域名，提供多重警告
            if len(similar_domains) > 0:
                if len(similar_domains) == 1:
                    # 單一相似域名
                    similar_domain = similar_domains[0]
                    return {
                        'is_spoofed': True,
                        'original_domain': similar_domain['domain'],
                        'spoofed_domain': domain,
                        'spoofing_type': "基礎域名變形攻擊",
                        'risk_explanation': f"⚠️ 高風險警告！\n\n這個網址 {domain} 疑似模仿正牌的 {similar_domain['domain']} ({similar_domain['description']})。\n\n詐騙集團使用相同的基礎域名但不同的後綴來製作假網站。\n\n🚨 千萬不要在這個網站輸入任何個人資料、密碼或信用卡號碼！"
                    }
                else:
                    # 多重相似域名 - 限制最多顯示3個
                    domain_list = []
                    # 只取前3個相似域名
                    for similar in similar_domains[:3]:
                        domain_list.append(f"{similar['domain']}({similar['description']})")
                    
                    # 如果還有更多相似域名，添加提示
                    if len(similar_domains) > 3:
                        domain_list.append(f"...等共{len(similar_domains)}個相似網域")
                    
                    return {
                        'is_spoofed': True,
                        'original_domain': 'multiple',
                        'spoofed_domain': domain,
                        'spoofing_type': "多重基礎域名變形攻擊",
                        'risk_explanation': f"⚠️ 高風險警告！\n\n這個網址 {domain} 可能模仿多個正牌網域：\n\n" + "\n".join([f"• {d}" for d in domain_list]) + f"\n\n這是個可疑的網域，詐騙集團常用相似的網域名稱來混淆視聽，製作假網站騙取個人資料或信用卡資訊。\n\n🚨 千萬不要在這個網站輸入任何個人資料、密碼或信用卡號碼！"
                    }
            
            # 快速檢測：特別檢查-tw和-taiwan後綴域名（高風險）
            for safe_domain in safe_domains.keys():
                safe_domain_lower = safe_domain.lower()
                safe_parts = safe_domain_lower.split('.')
                safe_base = safe_parts[0]
                
                # 處理 www 前綴：如果第一部分是 www，取第二部分作為基礎網域
                if safe_base == 'www' and len(safe_parts) > 1:
                    safe_base = safe_parts[1]
                
                # 檢查是否為基礎域名加上-tw或-taiwan（直接判定為高風險）
                if base_domain == safe_base + '-tw' or base_domain == safe_base + '-taiwan':
                    site_description = safe_domains.get(safe_domain, "知名網站")
                    return {
                        'is_spoofed': True,
                        'original_domain': safe_domain,
                        'spoofed_domain': domain,
                        'spoofing_type': "插入額外字元攻擊",
                        'risk_explanation': f"⚠️ 高風險警告！\n\n這個網址 {domain} 疑似模仿正牌的 {safe_domain} ({site_description})。\n\n詐騙集團常使用添加'-tw'或'-taiwan'字樣的手法製作假網站來騙取個人資料或信用卡資訊。\n\n🚨 千萬不要在這個網站輸入任何個人資料、密碼或信用卡號碼！"
                    }
                
                # 新增：檢查明顯的網域名稱變形攻擊（如 fetc-nete 模仿 fetc）
                # 檢查是否為基礎域名的變形（插入字元、替換字元等）
                if _is_obvious_domain_spoofing(base_domain, safe_base):
                    site_description = safe_domains.get(safe_domain, "知名網站")
                    return {
                        'is_spoofed': True,
                        'original_domain': safe_domain,
                        'spoofed_domain': domain,
                        'spoofing_type': "網域名稱變形攻擊",
                        'risk_explanation': f"⚠️ 高風險警告！\n\n這個網址 {domain} 疑似模仿正牌的 {safe_domain} ({site_description})。\n\n詐騙集團常用相似的網域名稱來混淆視聽，製作假網站騙取個人資料或信用卡資訊。\n\n🚨 千萬不要在這個網站輸入任何個人資料、密碼或信用卡號碼！"
                    }
            
            # 檢查每個白名單網域是否有相似性
            similar_domains_advanced = []
            
            for safe_domain in safe_domains.keys():
                safe_domain_lower = safe_domain.lower()
                safe_domain_without_www = safe_domain_lower[4:] if safe_domain_lower.startswith('www.') else safe_domain_lower
                
                # 跳過完全相同的網域（包含www變體）
                if (domain == safe_domain_lower or 
                    domain == safe_domain_without_www or 
                    domain_without_www == safe_domain_lower or 
                    domain_without_www == safe_domain_without_www):
                    continue
                
                # 只檢測高相似度的變形（避免誤報）
                # 需要域名長度相近（差距不超過2個字符）且有高度相似性
                length_diff = abs(len(domain_without_www) - len(safe_domain_without_www))
                if length_diff > 2:
                    continue  # 長度差距太大，跳過
                
                # 額外檢查：網域名稱必須有足夠的相似性
                if not _has_sufficient_similarity(domain_without_www, safe_domain_without_www):
                    continue  # 相似度不足，跳過
                
                # 只檢測非常相似的網域
                spoofing_detected = False
                spoofing_type = ""
                
                # 1. 字元替換攻擊（只檢測1個字符的差異）
                if _is_character_substitution(domain_without_www, safe_domain_without_www, max_substitutions=1):
                    spoofing_detected = True
                    spoofing_type = "字元替換"
                
                # 2. 插入額外字元（只檢測1個字符的插入）
                elif _is_character_insertion(domain_without_www, safe_domain_without_www, max_insertions=1):
                    spoofing_detected = True
                    spoofing_type = "插入額外字元"
                
                # 3. 相似字元攻擊（國際化域名攻擊）
                elif _is_homograph_attack(domain_without_www, safe_domain_without_www):
                    spoofing_detected = True
                    spoofing_type = "相似字元攻擊"
                
                if spoofing_detected:
                    site_description = safe_domains.get(safe_domain, "知名網站")
                    similar_domains_advanced.append({
                        'domain': safe_domain,
                        'description': site_description,
                        'type': spoofing_type
                    })
            
            # 如果找到多個相似域名，提供多重警告
            if len(similar_domains_advanced) > 0:
                if len(similar_domains_advanced) == 1:
                    # 單一相似域名
                    similar_domain = similar_domains_advanced[0]
                    return {
                        'is_spoofed': True,
                        'original_domain': similar_domain['domain'],
                        'spoofed_domain': domain,
                        'spoofing_type': similar_domain['type'],
                        'risk_explanation': f"⚠️ 高風險警告！\n\n這個網址 {domain} 疑似模仿正牌的 {similar_domain['domain']} ({similar_domain['description']})。\n\n詐騙集團常用這種手法製作假網站來騙取個人資料或信用卡資訊。\n\n🚨 千萬不要在這個網站輸入任何個人資料、密碼或信用卡號碼！"
                    }
                else:
                    # 多重相似域名 - 限制最多顯示3個
                    domain_list = []
                    # 只取前3個相似域名
                    for similar in similar_domains_advanced[:3]:
                        domain_list.append(f"{similar['domain']}({similar['description']})")
                    
                    # 如果還有更多相似域名，添加提示
                    if len(similar_domains_advanced) > 3:
                        domain_list.append(f"...等共{len(similar_domains_advanced)}個相似網域")
                    
                    return {
                        'is_spoofed': True,
                        'original_domain': 'multiple',
                        'spoofed_domain': domain,
                        'spoofing_type': "多重變形攻擊",
                        'risk_explanation': f"⚠️ 高風險警告！\n\n這個網址 {domain} 可能模仿多個正牌網域：\n\n" + "\n".join([f"• {d}" for d in domain_list]) + f"\n\n這是個可疑的網域，詐騙集團常用相似的網域名稱來混淆視聽，製作假網站騙取個人資料或信用卡資訊。\n\n🚨 千萬不要在這個網站輸入任何個人資料、密碼或信用卡號碼！"
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

def _is_character_substitution(suspicious_domain, safe_domain, max_substitutions=2):
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
    if distance <= max_distance and length_diff <= max_substitutions:
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

def _is_character_insertion(suspicious_domain, safe_domain, max_insertions=2):
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
    safe_base = safe_parts[0]  # 例如 google, pchome, cht, amazon
    suspicious_base = suspicious_parts[0]  # 例如 google-search, pchome-24h, cht-tw, amazoner
    
    # 0. 優先檢查是否為-tw或-taiwan後綴的變形攻擊（高風險）
    if suspicious_base.endswith('-tw') or suspicious_base.endswith('-taiwan'):
        # 檢查去除後綴後是否與安全網域匹配
        if suspicious_base.endswith('-tw'):
            base_without_suffix = suspicious_base[:-3]  # 移除'-tw'
        else:  # '-taiwan'
            base_without_suffix = suspicious_base[:-8]  # 移除'-taiwan'
        
        # 檢查去除後綴後是否與安全網域匹配
        if base_without_suffix == safe_base:
            return True
    
    # 1. 檢查字母後綴插入 (amazon -> amazoner, google -> googles, facebook -> facebooker)
    if suspicious_base.startswith(safe_base) and len(suspicious_base) > len(safe_base):
        added_part = suspicious_base[len(safe_base):]
        # 常見的字母添加模式
        common_letter_suffixes = ['r', 's', 'er', 'es', 'ing', 'ed', 'ly', 'al', 'ic', 'tion', 'ment']
        if added_part in common_letter_suffixes:
            return True
        # 檢查是否只是添加了1-4個字母
        if len(added_part) <= 4 and added_part.isalpha():
            return True
    
    # 2. 檢查連字符插入 (google -> google-search, pchome -> pchome-24h)
    if '-' in suspicious_base and safe_base in suspicious_base:
        # 移除連字符後檢查是否包含原始網域
        base_without_dash = suspicious_base.replace('-', '')
        if safe_base in base_without_dash:
            return True
        
        # 檢查連字符前的部分是否與安全網域匹配
        dash_parts = suspicious_base.split('-')
        if dash_parts[0] == safe_base:
            return True
    
    # 3. 檢查數字插入 (pchome -> pchome24h)
    import re
    # 移除數字後檢查
    base_without_numbers = re.sub(r'\d+', '', suspicious_base)
    if base_without_numbers == safe_base:
        return True
    
    # 4. 檢查常見後綴插入
    common_suffixes = ['search', 'official', 'secure', 'login', 'bank', 'pay', 'tw', 'taiwan', '24h', 'shop', 'store', 'online', 'web', 'site', 'net', 'app', 'mobile']
    for suffix in common_suffixes:
        if suspicious_base == safe_base + suffix:
            return True
        if suspicious_base == safe_base + '-' + suffix:
            return True
    
    # 5. 檢查子網域中的變形攻擊
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
            
            # 檢查字母後綴插入
            if suspicious_part.startswith(safe_base) and len(suspicious_part) > len(safe_base):
                added_part = suspicious_part[len(safe_base):]
                if len(added_part) <= 4 and added_part.isalpha():
                    return True
    
    # 6. 檢查完整網域的字母插入 (amazon.com -> amazoner.com)
    if len(safe_parts) == len(suspicious_parts):
        # 檢查每個部分
        for safe_part, suspicious_part in zip(safe_parts, suspicious_parts):
            if suspicious_part.startswith(safe_part) and len(suspicious_part) > len(safe_part):
                added_part = suspicious_part[len(safe_part):]
                # 如果只是在某個部分後面加了字母
                if len(added_part) <= 4 and added_part.isalpha():
                    return True
    
    # 7. 原有的模式檢測
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
    
    # 檢查是否在基礎網域名稱後加了-tw或-taiwan（直接判定為高風險）
    if suspicious_base == safe_base + '-tw' or suspicious_base == safe_base + '-taiwan':
        return True
    
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

def _is_obvious_domain_spoofing(suspicious_base, safe_base):
    """檢查明顯的網域名稱變形攻擊"""
    # 如果完全相同，不是變形攻擊
    if suspicious_base == safe_base:
        return False
    
    # 檢查是否包含原始網域名稱作為子字串
    if safe_base in suspicious_base:
        # 檢查是否為常見的變形模式
        
        # 1. 插入連字符和額外字元 (fetc -> fetc-nete, google -> google-search)
        if suspicious_base.startswith(safe_base + '-'):
            return True
        
        # 2. 在中間插入字元 (fetc -> fetc-nete, amazon -> amazoner)
        if suspicious_base.startswith(safe_base):
            added_part = suspicious_base[len(safe_base):]
            # 如果添加的部分是常見的變形模式
            if len(added_part) <= 6 and (added_part.startswith('-') or added_part.isalpha()):
                return True
        
        # 3. 檢查是否在原始網域中間插入字元
        # 例如 fetc -> fe-tc, f-etc 等
        for i in range(1, len(safe_base)):
            prefix = safe_base[:i]
            suffix = safe_base[i:]
            # 檢查是否為 prefix + 插入字元 + suffix 的模式
            if suspicious_base.startswith(prefix) and suspicious_base.endswith(suffix):
                middle_part = suspicious_base[len(prefix):-len(suffix)] if suffix else suspicious_base[len(prefix):]
                if len(middle_part) <= 4 and ('-' in middle_part or middle_part.isalpha()):
                    return True
    
    # 4. 檢查字元替換攻擊（更寬鬆的條件）
    if abs(len(suspicious_base) - len(safe_base)) <= 2:
        # 計算編輯距離
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
        
        distance = levenshtein_distance(suspicious_base, safe_base)
        max_length = max(len(suspicious_base), len(safe_base))
        
        # 如果編輯距離小於等於2，且有足夠的相似性
        if distance <= 2:
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
            
            lcs_len = lcs_length(suspicious_base, safe_base)
            similarity_ratio = lcs_len / max_length
            
            # 降低閾值到60%，專門針對明顯的變形攻擊
            if similarity_ratio >= 0.6:
                return True
    
    return False

def _has_sufficient_similarity(domain1, domain2):
    """檢查兩個網域是否有足夠的相似性"""
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
    
    # 計算相似度比例
    max_length = max(len(domain1), len(domain2))
    lcs_len = lcs_length(domain1, domain2)
    similarity_ratio = lcs_len / max_length
    
    # 要求至少80%的字元相似度
    return similarity_ratio >= 0.8 

def _detect_government_domain_spoofing(domain):
    """
    專門檢測政府網域變形攻擊
    
    Args:
        domain: 要檢測的域名（已移除www前綴）
        
    Returns:
        dict: 檢測結果
    """
    # 首先檢查是否是正確的政府網域格式
    if domain.endswith('.gov.tw'):
        return {'is_spoofed': False}  # 正確的政府網域格式，不是詐騙
    
    # 檢查是否是頂級的gov.tw域名（這是合法的）
    if domain == 'gov.tw':
        return {'is_spoofed': False}  # gov.tw本身是合法的
    
    # 檢查是否包含 "gov" 但不是正確的格式
    has_gov = 'gov' in domain.lower()
    
    if has_gov:
        # 常見的政府網域變形模式
        suspicious_patterns = [
            '-gov.com',  # example-gov.com
            'gov.com',   # somegovdepartment.com  
            'gov.net',   # gov.net
            'gov.org',   # gov.org
            '.com/tw',   # 如 cdic-gov.com/tw
            '-gov.net',  # example-gov.net
            'gov-',      # gov-something.com
            'govtw',     # govtw.com
            'gov.tw.',   # gov.tw.fake.com
        ]
        
        # 檢查是否匹配可疑模式
        for pattern in suspicious_patterns:
            if pattern in domain.lower():
                return {
                    'is_spoofed': True,
                    'original_domain': 'gov.tw',
                    'spoofed_domain': domain,
                    'spoofing_type': '政府網域變形攻擊',
                    'risk_explanation': f"🚨 極高風險警告！\n\n這個網址「{domain}」是假冒政府網站的詐騙網址！\n\n✅ 真正的政府網站都是以「.gov.tw」結尾\n❌ 這個網址使用了錯誤的格式來冒充政府機關\n\n網頁標題亂碼顯示，假冒政府機關詐騙。政府機關不會透過LINE要求個資或操作ATM。\n\n🛡️ 請記住：政府機關的官方網站一律以「.gov.tw」結尾，任何其他格式都是假的！\n\n📞 如有疑問請撥打165反詐騙專線確認"
                }
        
        # 如果包含gov但沒有匹配到特定模式，給出較溫和的警告
        # 但要排除一些可能的合法情況
        if not any(legitimate in domain.lower() for legitimate in ['google', 'govtech', 'government']):
            return {
                'is_spoofed': True,
                'original_domain': 'gov.tw',
                'spoofed_domain': domain,
                'spoofing_type': '疑似政府網域變形攻擊',
                'risk_explanation': f"⚠️ 高風險警告！\n\n這個網址「{domain}」包含「gov」字樣但不是正確的政府網站格式！\n\n✅ 真正的政府網站都是以「.gov.tw」結尾\n❌ 這個網址格式可疑，可能是詐騙網站\n\n網頁標題亂碼顯示，假冒政府機關詐騙。政府機關不會透過LINE要求個資或操作ATM。\n\n請務必確認：\n• 政府機關官網一律以「.gov.tw」結尾\n• 如需辦理政府業務，請直接到官方網站\n• 不要在可疑網站輸入個人資料\n\n📞 如有疑問請撥打165反詐騙專線確認"
            }
    
    return {'is_spoofed': False} 


def _is_legitimate_domain_variant(suspicious_domain, safe_domain):
    """
    檢查是否為合法的域名變體
    
    Args:
        suspicious_domain: 可疑域名（如 cht.tw）
        safe_domain: 安全域名（如 cht.com.tw）
        
    Returns:
        bool: 是否為合法變體
    """
    # 提取基礎域名
    suspicious_parts = suspicious_domain.split('.')
    safe_parts = safe_domain.split('.')
    
    suspicious_base = suspicious_parts[0]
    safe_base = safe_parts[0]
    
    # 如果基礎域名不同，不是變體
    if suspicious_base != safe_base:
        return False
    
    # 檢查是否為合法的短域名變體
    # 例如：cht.tw 是 cht.com.tw 的合法變體
    if len(suspicious_parts) == 2 and len(safe_parts) == 3:
        # 檢查是否為 .tw 對 .com.tw 的變體
        if (suspicious_parts[1] == 'tw' and 
            safe_parts[1] == 'com' and 
            safe_parts[2] == 'tw'):
            return True
    
    # 檢查是否為其他常見的合法變體
    # 例如：example.com 和 example.net 都是同一機構的合法域名
    legitimate_variants = [
        # 台灣域名變體
        ('.tw', '.com.tw'),
        ('.tw', '.org.tw'),
        ('.tw', '.net.tw'),
        # 國際域名變體
        ('.com', '.net'),
        ('.com', '.org'),
        ('.net', '.com'),
        ('.org', '.com'),
    ]
    
    for variant in legitimate_variants:
        if (suspicious_domain.endswith(variant[0]) and 
            safe_domain.endswith(variant[1])):
            return True
    
    return False