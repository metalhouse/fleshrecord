#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API调用迁移助手
帮助现有的API调用代码快速适配新的token认证机制
"""

import re
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.user_config import user_config_manager


class APIMigrationHelper:
    """API迁移助手"""
    
    def __init__(self):
        pass
    
    def convert_curl_command(self, curl_command: str, user_id: str) -> str:
        """转换curl命令以使用新的认证机制
        
        Args:
            curl_command: 原始curl命令
            user_id: 用户ID
            
        Returns:
            str: 转换后的curl命令
        """
        # 获取用户token
        user_config = user_config_manager.get_user_config(user_id)
        if not user_config or not user_config.api_token:
            return f"# 错误: 用户 {user_id} 没有配置API token\n# 请先运行: python manage_tokens.py generate {user_id}\n\n{curl_command}"
        
        token = user_config.api_token
        
        # 移除URL中的Authorization参数
        curl_command = re.sub(r'\?Authorization=Bearer\s+[^\s]*', '', curl_command)
        curl_command = re.sub(r'&Authorization=Bearer\s+[^\s]*', '', curl_command)
        
        # 检查是否已有X-User-ID header
        if f"X-User-ID: {user_id}" not in curl_command:
            # 添加X-User-ID header
            if "-H '" in curl_command or '-H "' in curl_command:
                # 在第一个header之前插入
                curl_command = re.sub(
                    r"(-H ['\"])",
                    f"-H 'X-User-ID: {user_id}' \\\\\n  \\1",
                    curl_command,
                    count=1
                )
            else:
                # 在URL之后添加第一个header
                curl_command = re.sub(
                    r"(http[s]?://[^\s]+)",
                    f"\\1 \\\\\n  -H 'X-User-ID: {user_id}'",
                    curl_command
                )
        
        # 添加Authorization header
        if "Authorization: Bearer" not in curl_command:
            curl_command = re.sub(
                r"(-H 'X-User-ID: [^']*' \\\\)",
                f"\\1\n  -H 'Authorization: Bearer {token}' \\\\",
                curl_command
            )
        
        return curl_command
    
    def generate_migration_examples(self, user_id: str) -> dict:
        """为特定用户生成迁移示例
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 包含各种迁移示例的字典
        """
        user_config = user_config_manager.get_user_config(user_id)
        if not user_config or not user_config.api_token:
            return {"error": f"用户 {user_id} 没有配置API token"}
        
        token = user_config.api_token
        base_headers = f"-H 'X-User-ID: {user_id}' \\\\\n  -H 'Authorization: Bearer {token}'"
        
        examples = {
            "添加交易": {
                "old": f"""curl -X POST http://192.168.1.90:9012/add_transaction?Authorization=Bearer some-token \\
  -H 'X-User-ID: {user_id}' \\
  -H 'Content-Type: application/json' \\
  -d '{{"amount": 10.50, "description": "测试"}}'""",
                
                "new": f"""curl -X POST http://192.168.1.90:9012/add_transaction \\
  {base_headers} \\
  -H 'Content-Type: application/json' \\
  -d '{{"amount": 10.50, "description": "测试"}}'"""
            },
            
            "查询预算": {
                "old": f"""curl -X GET http://192.168.1.90:9012/budgets \\
  -H 'X-User-ID: {user_id}'""",
                
                "new": f"""curl -X GET http://192.168.1.90:9012/budgets \\
  {base_headers}"""
            },
            
            "Dify助手": {
                "old": f"""curl -X POST http://192.168.1.90:9012/dify_webhook \\
  -H 'X-User-ID: {user_id}' \\
  -H 'Content-Type: application/json' \\
  -d '{{"query": "预算情况？"}}'""",
                
                "new": f"""curl -X POST http://192.168.1.90:9012/dify_webhook \\
  {base_headers} \\
  -H 'Content-Type: application/json' \\
  -d '{{"query": "预算情况？"}}'"""
            }
        }
        
        return examples
    
    def generate_code_examples(self, user_id: str) -> dict:
        """生成不同编程语言的代码示例
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 包含不同语言代码示例的字典
        """
        user_config = user_config_manager.get_user_config(user_id)
        if not user_config or not user_config.api_token:
            return {"error": f"用户 {user_id} 没有配置API token"}
        
        token = user_config.api_token
        
        examples = {
            "Python (requests)": f'''import requests

# 通用headers
headers = {{
    'X-User-ID': '{user_id}',
    'Authorization': 'Bearer {token}',
    'Content-Type': 'application/json'
}}

# 添加交易
response = requests.post(
    'http://192.168.1.90:9012/add_transaction',
    headers=headers,
    json={{
        'amount': 10.50,
        'description': '测试交易',
        'date': '2025-09-27'
    }}
)

# 查询预算
response = requests.get(
    'http://192.168.1.90:9012/budgets',
    headers=headers
)''',
            
            "JavaScript (fetch)": f'''// 通用headers
const headers = {{
    'X-User-ID': '{user_id}',
    'Authorization': 'Bearer {token}',
    'Content-Type': 'application/json'
}};

// 添加交易
const response = await fetch('http://192.168.1.90:9012/add_transaction', {{
    method: 'POST',
    headers: headers,
    body: JSON.stringify({{
        amount: 10.50,
        description: '测试交易',
        date: '2025-09-27'
    }})
}});

// 查询预算
const budgetResponse = await fetch('http://192.168.1.90:9012/budgets', {{
    method: 'GET',
    headers: headers
}});''',
            
            "PowerShell": f'''# 通用headers
$headers = @{{
    'X-User-ID' = '{user_id}'
    'Authorization' = 'Bearer {token}'
    'Content-Type' = 'application/json'
}}

# 添加交易
$body = @{{
    amount = 10.50
    description = '测试交易'
    date = '2025-09-27'
}} | ConvertTo-Json

Invoke-RestMethod -Uri 'http://192.168.1.90:9012/add_transaction' `
    -Method POST -Headers $headers -Body $body

# 查询预算
Invoke-RestMethod -Uri 'http://192.168.1.90:9012/budgets' `
    -Method GET -Headers $headers'''
        }
        
        return examples


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API调用迁移助手")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 转换curl命令
    convert_parser = subparsers.add_parser('convert', help='转换curl命令')
    convert_parser.add_argument('user_id', help='用户ID')
    convert_parser.add_argument('--command', required=True, help='原始curl命令')
    
    # 生成迁移示例
    examples_parser = subparsers.add_parser('examples', help='生成迁移示例')
    examples_parser.add_argument('user_id', help='用户ID')
    
    # 生成代码示例
    code_parser = subparsers.add_parser('code', help='生成编程语言示例')
    code_parser.add_argument('user_id', help='用户ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    helper = APIMigrationHelper()
    
    if args.command == 'convert':
        result = helper.convert_curl_command(args.command, args.user_id)
        print("🔄 转换后的curl命令:")
        print("=" * 50)
        print(result)
        
    elif args.command == 'examples':
        examples = helper.generate_migration_examples(args.user_id)
        if 'error' in examples:
            print(f"❌ {examples['error']}")
            return
        
        print(f"📖 用户 {args.user_id} 的API迁移示例:")
        print("=" * 60)
        
        for api_name, example in examples.items():
            print(f"\n### {api_name}")
            print("\n**之前 (不安全):**")
            print(example['old'])
            print("\n**现在 (安全):**")
            print(example['new'])
            print()
            
    elif args.command == 'code':
        examples = helper.generate_code_examples(args.user_id)
        if 'error' in examples:
            print(f"❌ {examples['error']}")
            return
        
        print(f"💻 用户 {args.user_id} 的代码示例:")
        print("=" * 60)
        
        for lang, code in examples.items():
            print(f"\n### {lang}")
            print("```")
            print(code)
            print("```")


if __name__ == '__main__':
    main()