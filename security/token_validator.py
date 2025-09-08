# -*- coding: utf-8 -*-
"""
Token验证模块
提供API token验证功能
"""

import secrets
import hashlib
from typing import Optional, Tuple
from functools import wraps
from flask import request, jsonify, current_app as app

from utils.response_builder import APIResponseBuilder
from models.user_config import user_config_manager


class TokenValidator:
    """Token验证器"""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成安全的随机token
        
        Args:
            length: token长度（字节数）
            
        Returns:
            str: 十六进制格式的token字符串
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """对token进行哈希处理（用于安全存储）
        
        Args:
            token: 原始token
            
        Returns:
            str: SHA256哈希值
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    @staticmethod
    def validate_api_token(user_id: str, provided_token: str) -> bool:
        """验证API token
        
        Args:
            user_id: 用户ID
            provided_token: 提供的token
            
        Returns:
            bool: 验证是否通过
        """
        user_config = user_config_manager.get_user_config(user_id)
        if not user_config or not user_config.api_token:
            app.logger.warning(f"用户 {user_id} 没有配置API token")
            return False
        
        # 使用安全的字符串比较避免时序攻击
        return secrets.compare_digest(user_config.api_token, provided_token)
    
    @staticmethod
    def extract_bearer_token(authorization_header: str) -> Optional[str]:
        """从Authorization header中提取Bearer token
        
        Args:
            authorization_header: Authorization header值
            
        Returns:
            Optional[str]: 提取的token，如果格式错误返回None
        """
        if not authorization_header:
            return None
        
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        return parts[1]


def require_api_token(f):
    """API token验证装饰器
    
    验证请求头中的Authorization: Bearer <token>
    同时验证X-User-ID header
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取用户ID
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            app.logger.warning("API请求缺少X-User-ID请求头")
            return jsonify(APIResponseBuilder.error_response(
                "X-User-ID header is required", 401
            )), 401
        
        # 获取Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            app.logger.warning(f"用户 {user_id} 的API请求缺少Authorization header")
            return jsonify(APIResponseBuilder.error_response(
                "Authorization header is required", 401
            )), 401
        
        # 提取Bearer token
        token = TokenValidator.extract_bearer_token(auth_header)
        if not token:
            app.logger.warning(f"用户 {user_id} 的Authorization header格式错误")
            return jsonify(APIResponseBuilder.error_response(
                "Invalid Authorization header format. Expected: Bearer <token>", 401
            )), 401
        
        # 验证token
        if not TokenValidator.validate_api_token(user_id, token):
            app.logger.warning(f"用户 {user_id} 的API token验证失败")
            return jsonify(APIResponseBuilder.error_response(
                "Invalid API token", 403
            )), 403
        
        app.logger.info(f"用户 {user_id} API token验证通过")
        return f(*args, **kwargs)
    
    return decorated_function


def require_api_token_with_user_id(f):
    """API token验证装饰器（带用户ID注入）
    
    验证token后，将user_id作为第一个参数传递给被装饰的函数
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取用户ID
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            app.logger.warning("API请求缺少X-User-ID请求头")
            return jsonify(APIResponseBuilder.error_response(
                "X-User-ID header is required", 401
            )), 401
        
        # 获取Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            app.logger.warning(f"用户 {user_id} 的API请求缺少Authorization header")
            return jsonify(APIResponseBuilder.error_response(
                "Authorization header is required", 401
            )), 401
        
        # 提取Bearer token
        token = TokenValidator.extract_bearer_token(auth_header)
        if not token:
            app.logger.warning(f"用户 {user_id} 的Authorization header格式错误")
            return jsonify(APIResponseBuilder.error_response(
                "Invalid Authorization header format. Expected: Bearer <token>", 401
            )), 401
        
        # 验证token
        if not TokenValidator.validate_api_token(user_id, token):
            app.logger.warning(f"用户 {user_id} 的API token验证失败")
            return jsonify(APIResponseBuilder.error_response(
                "Invalid API token", 403
            )), 403
        
        app.logger.info(f"用户 {user_id} API token验证通过")
        # 将user_id作为第一个参数传递给被装饰的函数
        return f(user_id, *args, **kwargs)
    
    return decorated_function
