#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Token验证测试脚本
测试新的token认证机制
"""

import requests
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.user_config import user_config_manager


def test_api_token_authentication():
    """测试API token认证"""
    
    # 配置
    base_url = "http://192.168.1.90:9012"
    user_id = "metalhouse"
    
    # 获取用户配置和token
    user_config = user_config_manager.get_user_config(user_id)
    if not user_config or not user_config.api_token:
        print(f"❌ 用户 {user_id} 没有配置API token")
        return False
    
    api_token = user_config.api_token
    print(f"🔍 测试用户: {user_id}")
    print(f"🔑 使用Token: {api_token[:16]}...")
    
    # 测试数据
    test_transaction = {
        "amount": 1.00,
        "description": "API Token 测试交易",
        "date": "2025-09-08",
        "source_account": "测试账户",
        "destination_account": "测试目标",
        "category": "测试分类"
    }
    
    print("\n🧪 开始测试...")
    
    # 测试1: 无认证header
    print("\n1️⃣ 测试无认证header:")
    try:
        response = requests.post(
            f"{base_url}/add_transaction",
            headers={"Content-Type": "application/json"},
            json=test_transaction,
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试2: 只有用户ID，无token
    print("\n2️⃣ 测试只有用户ID，无token:")
    try:
        response = requests.post(
            f"{base_url}/add_transaction",
            headers={
                "X-User-ID": user_id,
                "Content-Type": "application/json"
            },
            json=test_transaction,
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试3: 错误的token格式
    print("\n3️⃣ 测试错误的token格式:")
    try:
        response = requests.post(
            f"{base_url}/add_transaction",
            headers={
                "X-User-ID": user_id,
                "Authorization": "InvalidFormat",
                "Content-Type": "application/json"
            },
            json=test_transaction,
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试4: 错误的token
    print("\n4️⃣ 测试错误的token:")
    try:
        response = requests.post(
            f"{base_url}/add_transaction",
            headers={
                "X-User-ID": user_id,
                "Authorization": "Bearer invalid_token_here",
                "Content-Type": "application/json"
            },
            json=test_transaction,
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试5: 正确的认证
    print("\n5️⃣ 测试正确的认证:")
    try:
        response = requests.post(
            f"{base_url}/add_transaction",
            headers={
                "X-User-ID": user_id,
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            },
            json=test_transaction,
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        
        if response.status_code == 201:
            print("   ✅ 认证成功，交易创建成功！")
            return True
        else:
            print("   ❌ 认证失败或交易创建失败")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def main():
    """主函数"""
    print("🚀 API Token认证测试")
    print("=" * 50)
    
    success = test_api_token_authentication()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 测试完成！新的token认证机制工作正常")
    else:
        print("⚠️  测试完成！请检查服务器是否运行或配置是否正确")


if __name__ == '__main__':
    main()
