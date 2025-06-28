from typing import Dict, Any, List, Optional, Tuple, Union
from flask import request, jsonify, current_app as app
from werkzeug.exceptions import abort
from decimal import Decimal, InvalidOperation
import json
import hmac
import hashlib
from pydantic import ValidationError

from utils.response_builder import APIResponseBuilder
from utils.metrics import track_performance
from utils.sensitive_data_filter import SensitiveDataFilter
from services.firefly_service import FireflyService
from models.request_models import DifyWebhookRequest


class WebhookHandler:
    """处理Webhook请求的专用处理器"""
    
    def __init__(self, firefly_service: FireflyService, config: Any):
        self.firefly_service = firefly_service
        self.config = config
    
    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        """验证Webhook签名
        
        Args:
            payload: 原始请求体
            signature_header: 签名头信息
            
        Returns:
            bool: 签名是否有效
        """
        if not signature_header:
            app.logger.error("缺少Signature请求头")
            return False
        
        try:
            # 解析签名组件
            signature_parts = dict(
                part.split('=') for part in signature_header.split(',')
            )
            if 'v1' not in signature_parts or 't' not in signature_parts:
                app.logger.error("签名格式不正确，缺少必要组件")
                return False
            
            received_signature = signature_parts['v1']
            timestamp = signature_parts['t']
            
            # 计算签名
            return self._compute_signature_match(
                payload, timestamp, received_signature
            )
            
        except Exception as e:
            app.logger.error(f"签名验证过程中发生错误: {e}")
            return False
    
    def _compute_signature_match(self, payload: bytes, timestamp: str, 
                               received_signature: str) -> bool:
        """计算并比较签名"""
        # 将时间戳与请求体组合后计算签名
        signed_payload = f'{timestamp}.'.encode('utf-8') + payload
        
        # 使用主要密钥计算签名
        computed_signature = hmac.new(
            key=self.config.get('webhook_secret', '').encode('utf-8'),
            msg=signed_payload,
            digestmod=hashlib.sha3_256
        ).hexdigest()
        
        # 使用更新密钥计算签名
        computed_signature_update = hmac.new(
            key=self.config.get('webhook_secret_update', '').encode('utf-8'),
            msg=signed_payload,
            digestmod=hashlib.sha3_256
        ).hexdigest()
        
        return (hmac.compare_digest(computed_signature, received_signature) or 
                hmac.compare_digest(computed_signature_update, received_signature))
    
    def validate_request_headers(self) -> None:
        """验证请求头"""
        signature = request.headers.get('Signature')
        if not signature:
            app.logger.warning("缺少Signature请求头")
            abort(400, "Signature header is required")
        
        if not request.is_json:
            abort(415, "Content-Type must be application/json")
        
        return signature
    
    def validate_webhook_payload(self, data: Dict[str, Any]) -> None:
        """验证Webhook载荷数据
        
        Args:
            data: 请求数据
            
        Raises:
            HTTPException: 当验证失败时
        """
        # 验证必要字段
        required_fields = ['trigger', 'content']
        for field in required_fields:
            if field not in data:
                abort(400, f"Missing required field: {field}")
        
        # 验证trigger值
        valid_triggers = ['STORE_TRANSACTION', 'UPDATE_TRANSACTION']
        if data['trigger'] not in valid_triggers:
            abort(400, f"Invalid trigger value. Must be one of: {valid_triggers}")
        
        # 验证content结构
        content = data['content']
        if 'transactions' not in content or not isinstance(content['transactions'], list):
            abort(400, "Content must contain 'transactions' list")
        
        # 验证交易数据
        transactions = content['transactions']
        if not transactions:
            app.logger.warning("No transactions found in payload.")
            abort(400, "At least one transaction is required")
        
        # 验证第一个交易的数据格式
        self._validate_transaction_data(transactions[0])
    
    def _validate_transaction_data(self, transaction: Dict[str, Any]) -> None:
        """验证单个交易数据"""
        # 验证金额格式
        amount = transaction.get('amount')
        if amount is not None:
            try:
                float(amount)
            except (ValueError, TypeError):
                abort(400, "Amount must be a number")
        
        # 验证描述长度
        description = transaction.get('description', '')
        if len(description) > 255:
            abort(400, "Description too long (max 255 characters)")
    
    def log_safe_request_info(self) -> None:
        """安全地记录请求信息（过滤敏感数据）"""
        # 安全记录请求头（过滤敏感信息）
        safe_headers = {
            k: '[FILTERED]' if k.lower() in ['authorization', 'cookie'] else v 
            for k, v in request.headers.items()
        }
        app.logger.info(f"Request headers: {safe_headers}")
        
        # 安全记录请求体
        if request.is_json:
            data = request.get_json()
            safe_data = self._create_safe_data_log(data)
            app.logger.info(f"Received data: {json.dumps(safe_data, ensure_ascii=False)}")
    
    def _create_safe_data_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建安全的数据日志（过滤敏感信息）
        
        Args:
            data: 原始数据
            
        Returns:
            Dict[str, Any]: 过滤后的数据
        """
        # 使用统一的敏感数据过滤器
        safe_data = SensitiveDataFilter.filter_dict(data)
        
        # 截断长描述
        if 'content' in safe_data and 'transactions' in safe_data['content']:
            for t in safe_data['content']['transactions']:
                if 'description' in t and len(str(t['description'])) > 50:
                    t['description'] = str(t['description'])[:50] + '...'
                    
        return safe_data
    
    def extract_transaction_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从请求数据中提取交易信息
        
        Args:
            data: Webhook请求数据
            
        Returns:
            Dict[str, Any]: 提取的交易信息
        """
        content = data.get('content', {})
        transactions = content.get('transactions', [])
        
        if not transactions:
            raise ValueError("No transactions found in payload")
        
        transaction = transactions[0]
        # 确保金额是数字类型
        amount = transaction.get('amount', 0)
        try:
            amount = float(amount) if amount is not None else 0.0
        except (ValueError, TypeError):
            amount = 0.0
            
        return {
            'trigger': data.get('trigger', ''),
            'description': transaction.get('description', '无描述'),
            'amount': amount,
            'category_name': transaction.get('category_name', '无分类'),
            'budget_name': transaction.get('budget_name', '无预算')
        }
    
    def build_notification_message(self, transaction_info: Dict[str, Any]) -> str:
        """构建通知消息
        
        Args:
            transaction_info: 交易信息
            
        Returns:
            str: 格式化的消息文本
        """
        trigger = transaction_info['trigger']
        description = transaction_info['description']
        amount = transaction_info['amount']
        category_name = transaction_info['category_name']
        budget_name = transaction_info['budget_name']
        
        if trigger == "UPDATE_TRANSACTION":
            message = f"您更新了一笔交易：{description}, 费用：{amount}，分类：{category_name}，预算：{budget_name}。"
        elif trigger == "STORE_TRANSACTION":
            message = f"您新增了一笔交易：{description}, 费用：{amount}，分类：{category_name}，预算：{budget_name}。"
        else:
            message = f"交易操作：{description}, 费用：{amount}，分类：{category_name}，预算：{budget_name}。"
        
        return message
    
    def build_safe_notification_message(self, transaction_info: Dict[str, Any]) -> str:
        """构建安全的通知消息（隐藏敏感信息用于日志）
        
        Args:
            transaction_info: 交易信息
            
        Returns:
            str: 格式化的安全消息文本
        """
        # 先构建完整消息，再使用过滤器过滤敏感信息
        message = self.build_notification_message(transaction_info)
        return SensitiveDataFilter.filter_message(message)
    
    @track_performance('webhook_request')
    def handle_webhook_request(self) -> Tuple[Union[str, Dict[str, Any]], int]:
        """处理需要X-User-ID验证的Webhook请求（如Dify等第三方服务）
        
        Returns:
            Tuple[Union[str, Dict[str, Any]], int]: (响应内容, 状态码)
        """
        return self.process_webhook_event()
    
    def handle_firefly_webhook_request(self) -> Tuple[Union[str, Dict[str, Any]], int]:
        """处理FireFly III的Webhook请求（跳过署名验证，使用token验证）
        
        Returns:
            Tuple[Union[str, Dict[str, Any]], int]: (响应内容, 状态码)
        """
        return self.process_webhook_event(skip_signature=True)
    
    def process_webhook_event(self, skip_signature: bool = False) -> Tuple[Union[str, Dict[str, Any]], int]:
        """处理Webhook请求的核心逻辑
        
        Args:
            skip_signature: 是否跳过签名验证
            
        Returns:
            Tuple[Union[str, Dict[str, Any]], int]: (响应内容, 状态码)
        """
        try:
            # 获取请求数据
            raw_payload = request.get_data()
            data = request.get_json()
            
            if not skip_signature:
                # 验证请求头
                signature = self.validate_request_headers()
                
                # 验证签名
                if not self.verify_signature(raw_payload, signature):
                    app.logger.error("Webhook签名验证失败")
                    return APIResponseBuilder.error_response(
                    "Invalid signature", 
                    code=401
                )
            
            # 验证载荷数据
            self.validate_webhook_payload(data)
            
            # 安全地记录请求信息
            self.log_safe_request_info()
            
            # 提取交易信息
            transaction_info = self.extract_transaction_info(data)
            
            # 构建通知消息
            message = self.build_notification_message(transaction_info)
            # 构建安全的日志消息（过滤敏感信息）
            safe_message = self.build_safe_notification_message(transaction_info)
            
            app.logger.info(f"Webhook处理成功: {safe_message}")
            
            return APIResponseBuilder.success_response(
                data={'message': message}
            )
            
        except ValidationError as ve:
            app.logger.error(f"数据验证错误: {ve}")
            return APIResponseBuilder.error_response(
                f"Validation error: {str(ve)}",
                status_code=400
            )
        
        except ValueError as e:
            app.logger.error(f"数据处理错误: {e}")
            return APIResponseBuilder.error_response(
                str(e),
                status_code=400
            )
        
        except Exception as e:
            app.logger.error(f"Webhook处理过程中发生未知错误: {e}")
            return APIResponseBuilder.error_response(
                "Internal server error",
                code=500
            )