#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量Token管理工具
用于批量管理用户API token
"""

import sys
from pathlib import Path
import json

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.user_config import user_config_manager
from security.token_validator import TokenValidator


def batch_generate_tokens(force=False):
    """为所有用户批量生成token"""
    users = user_config_manager.list_users()
    token_validator = TokenValidator()
    
    print(f"发现 {len(users)} 个用户配置文件")
    
    results = []
    for user_id in users:
        user_config = user_config_manager.get_user_config(user_id)
        if not user_config:
            print(f"❌ 无法加载用户 {user_id} 的配置")
            continue
        
        # 检查是否已有token
        has_token = bool(user_config.api_token)
        
        if has_token and not force:
            print(f"⏭️  用户 {user_id} 已有token，跳过")
            results.append({
                'user_id': user_id,
                'status': 'skipped',
                'token': user_config.api_token[:16] + '...',
                'action': 'none'
            })
            continue
        
        # 生成新token
        new_token = token_validator.generate_token()
        user_config.api_token = new_token
        
        # 保存配置
        if user_config_manager.save_user_config(user_config):
            action = 'regenerated' if has_token else 'generated'
            print(f"✅ 成功为用户 {user_id} {action} token")
            results.append({
                'user_id': user_id,
                'status': 'success',
                'token': new_token,
                'action': action
            })
        else:
            print(f"❌ 保存用户 {user_id} 配置失败")
            results.append({
                'user_id': user_id,
                'status': 'failed',
                'token': None,
                'action': 'save_failed'
            })
    
    return results


def export_tokens_to_file(filename='api_tokens_backup.json'):
    """导出所有token到文件（用于备份）"""
    users = user_config_manager.list_users()
    tokens = {}
    
    for user_id in users:
        user_config = user_config_manager.get_user_config(user_id)
        if user_config and user_config.api_token:
            tokens[user_id] = {
                'api_token': user_config.api_token,
                'firefly_api_url': user_config.firefly_api_url,
                'notification_enabled': user_config.notification_enabled
            }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已导出 {len(tokens)} 个用户的token到 {filename}")
    return filename


def generate_curl_examples():
    """生成所有用户的curl使用示例"""
    users = user_config_manager.list_users()
    
    examples = []
    for user_id in users:
        user_config = user_config_manager.get_user_config(user_id)
        if user_config and user_config.api_token:
            example = f"""
# 用户: {user_id}
curl -X POST http://192.168.1.90:9012/add_transaction \\
  -H 'X-User-ID: {user_id}' \\
  -H 'Authorization: Bearer {user_config.api_token}' \\
  -H 'Content-Type: application/json' \\
  -d '{{
    "amount": 10.50,
    "description": "测试交易",
    "date": "2025-09-08",
    "source_account": "现金账户",
    "destination_account": "餐饮",
    "category": "餐饮"
  }}'
"""
            examples.append(example)
    
    return examples


def security_audit():
    """进行安全审计"""
    users = user_config_manager.list_users()
    audit_results = {
        'total_users': len(users),
        'users_with_token': 0,
        'users_without_token': 0,
        'weak_tokens': [],
        'recommendations': []
    }
    
    for user_id in users:
        user_config = user_config_manager.get_user_config(user_id)
        if not user_config:
            continue
        
        if user_config.api_token:
            audit_results['users_with_token'] += 1
            
            # 检查token强度（长度）
            if len(user_config.api_token) < 32:
                audit_results['weak_tokens'].append({
                    'user_id': user_id,
                    'token_length': len(user_config.api_token),
                    'issue': 'Token too short'
                })
        else:
            audit_results['users_without_token'] += 1
    
    # 生成建议
    if audit_results['users_without_token'] > 0:
        audit_results['recommendations'].append(
            f"建议为 {audit_results['users_without_token']} 个用户生成API token"
        )
    
    if audit_results['weak_tokens']:
        audit_results['recommendations'].append(
            f"建议重新生成 {len(audit_results['weak_tokens'])} 个弱token"
        )
    
    return audit_results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量Token管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 批量生成token命令
    batch_parser = subparsers.add_parser('batch-generate', help='为所有用户批量生成token')
    batch_parser.add_argument('--force', action='store_true', help='强制重新生成所有token')
    
    # 导出token命令
    export_parser = subparsers.add_parser('export', help='导出所有token到文件')
    export_parser.add_argument('--file', default='api_tokens_backup.json', help='导出文件名')
    
    # 生成示例命令
    examples_parser = subparsers.add_parser('examples', help='生成curl使用示例')
    
    # 安全审计命令
    audit_parser = subparsers.add_parser('audit', help='进行安全审计')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'batch-generate':
        print("🚀 开始批量生成token...")
        results = batch_generate_tokens(args.force)
        
        # 统计结果
        success_count = len([r for r in results if r['status'] == 'success'])
        skipped_count = len([r for r in results if r['status'] == 'skipped'])
        failed_count = len([r for r in results if r['status'] == 'failed'])
        
        print(f"\n📊 结果统计:")
        print(f"   ✅ 成功: {success_count}")
        print(f"   ⏭️  跳过: {skipped_count}")
        print(f"   ❌ 失败: {failed_count}")
        
        # 显示成功生成的token
        successful_tokens = [r for r in results if r['status'] == 'success']
        if successful_tokens:
            print(f"\n🔑 新生成的Token:")
            for result in successful_tokens:
                print(f"   {result['user_id']}: {result['token']}")
    
    elif args.command == 'export':
        export_tokens_to_file(args.file)
        print(f"⚠️  警告: 请妥善保管备份文件 {args.file}，其中包含敏感信息")
    
    elif args.command == 'examples':
        examples = generate_curl_examples()
        print("📖 API使用示例:")
        print("=" * 80)
        for example in examples:
            print(example)
    
    elif args.command == 'audit':
        results = security_audit()
        print("🔍 安全审计结果:")
        print("=" * 50)
        print(f"总用户数: {results['total_users']}")
        print(f"已配置token的用户: {results['users_with_token']}")
        print(f"未配置token的用户: {results['users_without_token']}")
        
        if results['weak_tokens']:
            print(f"\n⚠️  发现 {len(results['weak_tokens'])} 个弱token:")
            for weak in results['weak_tokens']:
                print(f"   - {weak['user_id']}: {weak['issue']} (长度: {weak['token_length']})")
        
        if results['recommendations']:
            print(f"\n💡 安全建议:")
            for rec in results['recommendations']:
                print(f"   - {rec}")
        else:
            print(f"\n✅ 所有用户的token配置都符合安全要求")


if __name__ == '__main__':
    main()
