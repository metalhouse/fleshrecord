#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Token管理工具
用于生成、更新和管理用户的API访问token
"""

import json
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.user_config import user_config_manager, UserConfig
from security.token_validator import TokenValidator


class TokenManager:
    """Token管理器"""
    
    def __init__(self):
        self.user_config_manager = user_config_manager
        self.token_validator = TokenValidator()
    
    def generate_token_for_user(self, user_id: str, force: bool = False) -> Optional[str]:
        """为用户生成API token
        
        Args:
            user_id: 用户ID
            force: 是否强制重新生成（即使已存在）
            
        Returns:
            Optional[str]: 生成的token，失败返回None
        """
        # 检查用户配置是否存在
        user_config = self.user_config_manager.get_user_config(user_id)
        if not user_config:
            print(f"错误: 用户 '{user_id}' 的配置文件不存在")
            return None
        
        # 检查是否已有token
        if user_config.api_token and not force:
            print(f"用户 '{user_id}' 已有API token")
            response = input("是否要重新生成? (y/N): ").strip().lower()
            if response != 'y':
                print("操作取消")
                return user_config.api_token
        
        # 生成新token
        new_token = self.token_validator.generate_token()
        
        # 更新用户配置
        user_config.api_token = new_token
        
        # 保存配置
        if self.user_config_manager.save_user_config(user_config):
            print(f"✅ 成功为用户 '{user_id}' 生成API token")
            return new_token
        else:
            print(f"❌ 保存用户 '{user_id}' 配置失败")
            return None
    
    def revoke_token_for_user(self, user_id: str) -> bool:
        """撤销用户的API token
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        user_config = self.user_config_manager.get_user_config(user_id)
        if not user_config:
            print(f"错误: 用户 '{user_id}' 的配置文件不存在")
            return False
        
        if not user_config.api_token:
            print(f"用户 '{user_id}' 没有API token")
            return True
        
        # 清除token
        user_config.api_token = None
        
        # 保存配置
        if self.user_config_manager.save_user_config(user_config):
            print(f"✅ 成功撤销用户 '{user_id}' 的API token")
            return True
        else:
            print(f"❌ 保存用户 '{user_id}' 配置失败")
            return False
    
    def list_users_with_tokens(self) -> None:
        """列出所有用户及其token状态"""
        users = self.user_config_manager.list_users()
        
        if not users:
            print("没有找到用户配置文件")
            return
        
        print(f"{'用户ID':<20} {'Token状态':<10} {'Token前缀'}")
        print("-" * 50)
        
        for user_id in users:
            user_config = self.user_config_manager.get_user_config(user_id)
            if user_config:
                if user_config.api_token:
                    token_preview = user_config.api_token[:8] + "..."
                    status = "✅ 已设置"
                else:
                    token_preview = "无"
                    status = "❌ 未设置"
                
                print(f"{user_id:<20} {status:<10} {token_preview}")
    
    def validate_token_for_user(self, user_id: str, token: str) -> bool:
        """验证用户token
        
        Args:
            user_id: 用户ID
            token: 要验证的token
            
        Returns:
            bool: 验证结果
        """
        is_valid = self.token_validator.validate_api_token(user_id, token)
        if is_valid:
            print(f"✅ 用户 '{user_id}' 的token验证通过")
        else:
            print(f"❌ 用户 '{user_id}' 的token验证失败")
        return is_valid


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API Token管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 生成token命令
    generate_parser = subparsers.add_parser('generate', help='为用户生成API token')
    generate_parser.add_argument('user_id', help='用户ID')
    generate_parser.add_argument('--force', action='store_true', help='强制重新生成')
    
    # 撤销token命令
    revoke_parser = subparsers.add_parser('revoke', help='撤销用户的API token')
    revoke_parser.add_argument('user_id', help='用户ID')
    
    # 列出用户命令
    list_parser = subparsers.add_parser('list', help='列出所有用户及token状态')
    
    # 验证token命令
    validate_parser = subparsers.add_parser('validate', help='验证token')
    validate_parser.add_argument('user_id', help='用户ID')
    validate_parser.add_argument('token', help='要验证的token')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    token_manager = TokenManager()
    
    if args.command == 'generate':
        token = token_manager.generate_token_for_user(args.user_id, args.force)
        if token:
            print(f"\n🔑 API Token: {token}")
            print("\n📖 使用方法:")
            print(f"curl -X POST http://your-server:port/add_transaction \\")
            print(f"  -H 'X-User-ID: {args.user_id}' \\")
            print(f"  -H 'Authorization: Bearer {token}' \\")
            print(f"  -H 'Content-Type: application/json' \\")
            print(f"  -d '{{\"amount\": 10.50, \"description\": \"测试交易\", ...}}'")
    
    elif args.command == 'revoke':
        token_manager.revoke_token_for_user(args.user_id)
    
    elif args.command == 'list':
        token_manager.list_users_with_tokens()
    
    elif args.command == 'validate':
        token_manager.validate_token_for_user(args.user_id, args.token)


if __name__ == '__main__':
    main()
