#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
from datetime import datetime

def load_safe_domains():
    """載入安全網域數據"""
    safe_domains_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'safe_domains.json')
    
    if not os.path.exists(safe_domains_path):
        print(f"找不到安全網域文件：{safe_domains_path}")
        return None
    
    try:
        with open(safe_domains_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        print(f"解析JSON文件時發生錯誤：{e}")
        return None
    except Exception as e:
        print(f"載入安全網域文件時發生錯誤：{e}")
        return None

def save_safe_domains(data):
    """保存安全網域數據"""
    safe_domains_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'safe_domains.json')
    
    try:
        with open(safe_domains_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"安全網域已成功保存到：{safe_domains_path}")
        return True
    except Exception as e:
        print(f"保存安全網域文件時發生錯誤：{e}")
        return False

def list_domains(data, category=None):
    """列出安全網域"""
    if not data:
        return
    
    safe_domains = data.get('safe_domains', {})
    
    if category:
        if category in safe_domains:
            print(f"類別 【{category}】 中的網域：")
            domains = safe_domains[category]
            for i, (domain, description) in enumerate(domains.items(), 1):
                print(f"{i:3d}. {domain} - {description}")
            print(f"共 {len(domains)} 個網域")
        else:
            print(f"找不到類別：{category}")
            print(f"可用類別：{', '.join(safe_domains.keys())}")
    else:
        total_count = 0
        for cat, domains in safe_domains.items():
            print(f"\n類別 【{cat}】 中的網域：")
            for i, (domain, description) in enumerate(domains.items(), 1):
                print(f"{i:3d}. {domain} - {description}")
            print(f"小計：{len(domains)} 個網域")
            print("-" * 80)
            total_count += len(domains)
        print(f"總計：{total_count} 個安全網域")

def add_domain(data, category, domain, description):
    """添加網域到安全白名單"""
    if not data:
        return False
    
    safe_domains = data.get('safe_domains', {})
    
    if category not in safe_domains:
        print(f"找不到類別：{category}")
        print(f"可用類別：{', '.join(safe_domains.keys())}")
        return False
    
    if domain in safe_domains[category]:
        print(f"網域「{domain}」已存在於類別「{category}」中")
        return False
    
    safe_domains[category][domain] = description
    print(f"已添加網域「{domain}」到類別「{category}」")
    print(f"描述：{description}")
    return True

def remove_domain(data, category, domain):
    """從安全白名單中移除網域"""
    if not data:
        return False
    
    safe_domains = data.get('safe_domains', {})
    
    if category not in safe_domains:
        print(f"找不到類別：{category}")
        print(f"可用類別：{', '.join(safe_domains.keys())}")
        return False
    
    if domain not in safe_domains[category]:
        print(f"網域「{domain}」不存在於類別「{category}」中")
        return False
    
    del safe_domains[category][domain]
    print(f"已從類別「{category}」中移除網域「{domain}」")
    return True

def add_category(data, category):
    """添加新類別"""
    if not data:
        return False
    
    safe_domains = data.get('safe_domains', {})
    
    if category in safe_domains:
        print(f"類別「{category}」已存在")
        return False
    
    safe_domains[category] = {}
    print(f"已添加新類別「{category}」")
    return True

def search_domain(data, keyword):
    """搜索包含關鍵詞的網域"""
    if not data:
        return
    
    safe_domains = data.get('safe_domains', {})
    results = []
    
    for category, domains in safe_domains.items():
        for domain, description in domains.items():
            if keyword.lower() in domain.lower() or keyword.lower() in description.lower():
                results.append((category, domain, description))
    
    if results:
        print(f"找到 {len(results)} 個包含「{keyword}」的網域：")
        print("-" * 80)
        for i, (category, domain, description) in enumerate(results, 1):
            print(f"{i:3d}. [{category}] {domain} - {description}")
    else:
        print(f"沒有找到包含「{keyword}」的網域")

def list_categories(data):
    """列出所有類別"""
    if not data:
        return
    
    safe_domains = data.get('safe_domains', {})
    donation_domains = data.get('donation_domains', {})
    
    print("安全網域類別：")
    for i, (category, domains) in enumerate(safe_domains.items(), 1):
        print(f"{i:3d}. {category} ({len(domains)} 個網域)")
    
    print(f"\n贊助網域：{len(donation_domains)} 個")
    for domain, description in donation_domains.items():
        print(f"     - {domain} - {description}")

def main():
    parser = argparse.ArgumentParser(description='管理安全網域白名單')
    
    subparsers = parser.add_subparsers(dest='command', help='要執行的命令')
    
    # 列出網域命令
    list_parser = subparsers.add_parser('list', help='列出安全網域')
    list_parser.add_argument('-c', '--category', help='指定要列出的類別')
    
    # 添加網域命令
    add_parser = subparsers.add_parser('add', help='添加網域到安全白名單')
    add_parser.add_argument('-c', '--category', required=True, help='指定要添加到的類別')
    add_parser.add_argument('-d', '--domain', required=True, help='要添加的網域')
    add_parser.add_argument('-desc', '--description', required=True, help='網域的描述')
    
    # 移除網域命令
    remove_parser = subparsers.add_parser('remove', help='從安全白名單中移除網域')
    remove_parser.add_argument('-c', '--category', required=True, help='指定要從中移除的類別')
    remove_parser.add_argument('-d', '--domain', required=True, help='要移除的網域')
    
    # 添加類別命令
    add_category_parser = subparsers.add_parser('add-category', help='添加新類別')
    add_category_parser.add_argument('-c', '--category', required=True, help='要添加的新類別名稱')
    
    # 搜索網域命令
    search_parser = subparsers.add_parser('search', help='搜索網域')
    search_parser.add_argument('-k', '--keyword', required=True, help='搜索關鍵詞')
    
    # 列出類別命令
    categories_parser = subparsers.add_parser('categories', help='列出所有類別')
    
    # 解析命令行參數
    args = parser.parse_args()
    
    # 載入安全網域數據
    data = load_safe_domains()
    if not data:
        return
    
    # 執行相應的命令
    if args.command == 'list':
        list_domains(data, args.category)
    elif args.command == 'add':
        if add_domain(data, args.category, args.domain, args.description):
            save_safe_domains(data)
    elif args.command == 'remove':
        if remove_domain(data, args.category, args.domain):
            save_safe_domains(data)
    elif args.command == 'add-category':
        if add_category(data, args.category):
            save_safe_domains(data)
    elif args.command == 'search':
        search_domain(data, args.keyword)
    elif args.command == 'categories':
        list_categories(data)
    else:
        # 如果沒有指定命令，默認列出所有類別
        list_categories(data)
        print("\n使用 --help 查看可用命令")

if __name__ == '__main__':
    main() 