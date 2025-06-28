#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证502错误修复
"""

import requests
import json

def test_budgets_endpoint():
    """
    测试/budgets端点是否正确使用用户配置
    """
    url = "http://localhost:9012/budgets"
    headers = {
        "X-User-ID": "example_user",  # 使用已存在的用户配置
        "Content-Type": "application/json"
    }
    
    try:
        print("测试 /budgets 端点...")
        print(f"请求URL: {url}")
        print(f"请求头: {headers}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")  # 只显示前500字符
        
        if response.status_code == 200:
            print("✅ /budgets端点测试成功！")
            return True
        elif response.status_code == 502:
            print("❌ 仍然存在502错误")
            return False
        else:
            print(f"⚠️  收到非期望状态码: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_dify_webhook_endpoint():
    """
    测试/dify_webhook端点是否正确使用用户配置
    """
    url = "http://localhost:9012/dify_webhook"
    headers = {
        "X-User-ID": "example_user",
        "Content-Type": "application/json"
    }
    
    # 模拟Dify webhook请求
    data = {
        "api_endpoint": "/budgets",
        "query_parameters": ""
    }
    
    try:
        print("\n测试 /dify_webhook 端点...")
        print(f"请求URL: {url}")
        print(f"请求头: {headers}")
        print(f"请求数据: {data}")
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")  # 只显示前500字符
        
        if response.status_code == 200:
            print("✅ /dify_webhook端点测试成功！")
            return True
        elif response.status_code == 502:
            print("❌ 仍然存在502错误")
            return False
        else:
            print(f"⚠️  收到非期望状态码: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试502错误修复...")
    print("="*50)
    
    # 检查example_user.json配置文件
    try:
        with open("data/users/example_user.json", "r", encoding="utf-8") as f:
            user_config = json.load(f)
            firefly_url = user_config.get("firefly_api_url")
            print(f"用户配置中的Firefly API URL: {firefly_url}")
    except FileNotFoundError:
        print("❌ 找不到example_user.json配置文件")
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
    
    print("="*50)
    
    # 运行测试
    budgets_ok = test_budgets_endpoint()
    dify_ok = test_dify_webhook_endpoint()
    
    print("\n" + "="*50)
    print("测试总结:")
    print(f"  /budgets端点: {'✅ 通过' if budgets_ok else '❌ 失败'}")
    print(f"  /dify_webhook端点: {'✅ 通过' if dify_ok else '❌ 失败'}")
    
    if budgets_ok and dify_ok:
        print("\n🎉 所有测试通过！502错误已修复。")
    else:
        print("\n⚠️  部分测试失败，可能需要进一步调试。")