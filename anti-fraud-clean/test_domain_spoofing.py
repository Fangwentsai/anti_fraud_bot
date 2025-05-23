from domain_spoofing_detector import detect_domain_spoofing

# 測試案例
safe_domains = {
    'cht.com.tw': '中華電信',
    'google.com': 'Google',
    'facebook.com': 'Facebook'
}

test_cases = [
    'cht-tw.com.tw',  # 插入額外字元
    'cht.com.tw.fake.com',  # 網域後綴變形
    'goog1e.com',  # 字元替換
    'facebook-taiwan.com',  # 插入額外字元
    'cht.com.tw'  # 正常網域（應該不被標記）
]

print("🔍 網域變形檢測測試")
print("=" * 50)

for test_url in test_cases:
    result = detect_domain_spoofing(test_url, safe_domains)
    if result['is_spoofed']:
        print(f'✅ 檢測到變形: {test_url}')
        print(f'   模仿網域: {result["original_domain"]}')
        print(f'   變形類型: {result["spoofing_type"]}')
        print()
    else:
        print(f'❌ 未檢測到變形: {test_url}')
        print() 