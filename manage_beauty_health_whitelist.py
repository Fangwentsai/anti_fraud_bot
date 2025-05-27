#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
from datetime import datetime

def load_whitelist():
    """載入白名單數據"""
    whitelist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'beauty_health_whitelist.json')
    
    if not os.path.exists(whitelist_path):
        print(f"找不到白名單文件：{whitelist_path}")
        return None
    
    try:
        with open(whitelist_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        print(f"解析JSON文件時發生錯誤：{e}")
        return None
    except Exception as e:
        print(f"載入白名單文件時發生錯誤：{e}")
        return None

def save_whitelist(data):
    """保存白名單數據"""
    whitelist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'beauty_health_whitelist.json')
    
    try:
        # 更新版本號和最後更新時間
        data['version'] = str(float(data.get('version', '1.0')) + 0.1)
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        with open(whitelist_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"白名單已成功保存到：{whitelist_path}")
        return True
    except Exception as e:
        print(f"保存白名單文件時發生錯誤：{e}")
        return False

def list_keywords(data, category=None):
    """列出白名單關鍵詞"""
    if not data:
        return
    
    print(f"白名單版本：{data.get('version', '未知')}")
    print(f"最後更新時間：{data.get('last_updated', '未知')}")
    print("-" * 50)
    
    categories = data.get('categories', {})
    
    if category:
        if category in categories:
            print(f"類別 【{category}】 中的關鍵詞：")
            for i, keyword in enumerate(categories[category], 1):
                print(f"{i:3d}. {keyword}")
            print(f"共 {len(categories[category])} 個關鍵詞")
        else:
            print(f"找不到類別：{category}")
            print(f"可用類別：{', '.join(categories.keys())}")
    else:
        total_count = 0
        for cat, keywords in categories.items():
            print(f"類別 【{cat}】 中的關鍵詞：")
            for i, keyword in enumerate(keywords, 1):
                print(f"{i:3d}. {keyword}")
            print(f"小計：{len(keywords)} 個關鍵詞")
            print("-" * 50)
            total_count += len(keywords)
        print(f"總計：{total_count} 個關鍵詞")

def add_keyword(data, category, keyword):
    """添加關鍵詞到白名單"""
    if not data:
        return False
    
    categories = data.get('categories', {})
    
    if category not in categories:
        print(f"找不到類別：{category}")
        print(f"可用類別：{', '.join(categories.keys())}")
        return False
    
    if keyword in categories[category]:
        print(f"關鍵詞「{keyword}」已存在於類別「{category}」中")
        return False
    
    categories[category].append(keyword)
    print(f"已添加關鍵詞「{keyword}」到類別「{category}」")
    return True

def remove_keyword(data, category, keyword):
    """從白名單中移除關鍵詞"""
    if not data:
        return False
    
    categories = data.get('categories', {})
    
    if category not in categories:
        print(f"找不到類別：{category}")
        print(f"可用類別：{', '.join(categories.keys())}")
        return False
    
    if keyword not in categories[category]:
        print(f"關鍵詞「{keyword}」不存在於類別「{category}」中")
        return False
    
    categories[category].remove(keyword)
    print(f"已從類別「{category}」中移除關鍵詞「{keyword}」")
    return True

def add_category(data, category):
    """添加新類別"""
    if not data:
        return False
    
    categories = data.get('categories', {})
    
    if category in categories:
        print(f"類別「{category}」已存在")
        return False
    
    categories[category] = []
    print(f"已添加新類別「{category}」")
    return True

def main():
    parser = argparse.ArgumentParser(description='管理醫美和健康白名單關鍵詞')
    
    subparsers = parser.add_subparsers(dest='command', help='要執行的命令')
    
    # 列出關鍵詞命令
    list_parser = subparsers.add_parser('list', help='列出白名單關鍵詞')
    list_parser.add_argument('-c', '--category', help='指定要列出的類別')
    
    # 添加關鍵詞命令
    add_parser = subparsers.add_parser('add', help='添加關鍵詞到白名單')
    add_parser.add_argument('-c', '--category', required=True, help='指定要添加到的類別')
    add_parser.add_argument('-k', '--keyword', required=True, help='要添加的關鍵詞')
    
    # 移除關鍵詞命令
    remove_parser = subparsers.add_parser('remove', help='從白名單中移除關鍵詞')
    remove_parser.add_argument('-c', '--category', required=True, help='指定要從中移除的類別')
    remove_parser.add_argument('-k', '--keyword', required=True, help='要移除的關鍵詞')
    
    # 添加類別命令
    add_category_parser = subparsers.add_parser('add-category', help='添加新類別')
    add_category_parser.add_argument('-c', '--category', required=True, help='要添加的新類別名稱')
    
    # 解析命令行參數
    args = parser.parse_args()
    
    # 載入白名單數據
    data = load_whitelist()
    if not data:
        return
    
    # 執行相應的命令
    if args.command == 'list':
        list_keywords(data, args.category)
    elif args.command == 'add':
        if add_keyword(data, args.category, args.keyword):
            save_whitelist(data)
    elif args.command == 'remove':
        if remove_keyword(data, args.category, args.keyword):
            save_whitelist(data)
    elif args.command == 'add-category':
        if add_category(data, args.category):
            save_whitelist(data)
    else:
        # 如果沒有指定命令，默認列出所有關鍵詞
        list_keywords(data)
        parser.print_help()

if __name__ == '__main__':
    main() 