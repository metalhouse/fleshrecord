from typing import Dict, Any, Optional, Tuple, Union
from flask import request, jsonify, current_app as app
from pydantic import ValidationError
import uuid

from utils.response_builder import APIResponseBuilder
from utils.metrics import track_performance
from services.firefly_service import FireflyService
from models.request_models import TransactionRequest


class TransactionHandler:
    """处理交易相关请求的专用处理器"""
    
    def __init__(self, firefly_service: FireflyService):
        self.firefly_service = firefly_service
    
    @track_performance('add_transaction')
    def add_transaction_endpoint(self) -> Tuple[Dict[str, Any], int]:
        """添加交易的API端点处理器
        
        Returns:
            Tuple[Dict[str, Any], int]: (response_data, status_code)
        """
        transaction_id = str(uuid.uuid4())[:8]
        app.logger.info(f"开始处理交易请求 [ID: {transaction_id}]")
        
        try:
            # 验证请求格式
            if not request.is_json:
                app.logger.warning(f"[{transaction_id}] 请求不是JSON格式")
                return jsonify(APIResponseBuilder.error_response(
                    "请求必须是JSON格式", 400
                )), 400
            
            # 验证请求数据
            transaction_data = self._validate_transaction_data(transaction_id)
            if isinstance(transaction_data, tuple):
                return transaction_data  # 返回错误响应
            
            # 记录安全的请求信息
            self._log_transaction_info(transaction_data, transaction_id)
            
            # 调用Firefly服务创建交易
            result = self.firefly_service.add_transaction(transaction_data)
            
            if result:
                app.logger.info(
                    f"[{transaction_id}] 交易创建成功: amount={transaction_data.amount}, "
                    f"description={transaction_data.description}"
                )
                return jsonify(APIResponseBuilder.success_response(
                    "交易创建成功", result
                )), 201
            else:
                app.logger.error(f"[{transaction_id}] 交易创建失败")
                return jsonify(APIResponseBuilder.error_response(
                    "交易创建失败", 500
                )), 500
                
        except Exception as e:
            app.logger.error(
                f"[{transaction_id}] 处理交易请求时发生错误: {e}", 
                exc_info=True
            )
            return jsonify(APIResponseBuilder.error_response(
                "处理交易请求失败", 500
            )), 500
    
    def _validate_transaction_data(self, transaction_id: str) -> Union[TransactionRequest, Tuple[Dict[str, Any], int]]:
        """验证交易请求数据
        
        Args:
            transaction_id: 交易ID
            
        Returns:
            Union[TransactionRequest, Tuple[Dict[str, Any], int]]: 验证成功返回数据对象，失败返回错误响应
        """
        try:
            data = request.get_json()
            # 处理嵌套的transactions数组结构
            if 'transactions' in data and isinstance(data['transactions'], list) and len(data['transactions']) > 0:
                transaction_dict = data['transactions'][0]
                # 映射字段名差异
                # 支持多种可能的目标账户字段名映射
                # 支持多种可能的目标账户字段名变体
                target_fields = ['destination_name', 'destination', 'dest_account', 'destination_bank', 'dest_bank', 'target_account', 'to_account']
                for field in target_fields:
                    if field in transaction_dict and 'destination_account' not in transaction_dict:
                        transaction_dict['destination_account'] = transaction_dict[field]
                        break
                
                # 添加预算名称、分类名称和标签字段的映射
                # 处理预算名称映射
                if 'budget_name' in transaction_dict and 'budget' not in transaction_dict:
                    transaction_dict['budget'] = transaction_dict['budget_name']
                # 处理分类名称映射
                if 'category_name' in transaction_dict and 'category' not in transaction_dict:
                    transaction_dict['category'] = transaction_dict['category_name']
                # 处理标签字段
                if 'tags' in transaction_dict and isinstance(transaction_dict['tags'], str):
                    # 将逗号分隔的标签字符串转换为列表
                    transaction_dict['tags'] = [tag.strip() for tag in transaction_dict['tags'].split(',')] if transaction_dict['tags'] else []
                if 'source_name' in transaction_dict and 'source_account' not in transaction_dict:
                    transaction_dict['source_account'] = transaction_dict['source_name']
                transaction_data = TransactionRequest(**transaction_dict)
            else:
                transaction_dict = data
                # 支持多种可能的目标账户字段名变体
                # 添加预算名称和分类名称的字段映射
                target_fields = ['destination_name', 'destination', 'dest_account', 'destination_bank', 'dest_bank', 'target_account', 'to_account']
                # 处理预算名称映射
                if 'budget_name' in transaction_dict and 'budget' not in transaction_dict:
                    transaction_dict['budget'] = transaction_dict['budget_name']
                # 处理分类名称映射
                if 'category_name' in transaction_dict and 'category' not in transaction_dict:
                    transaction_dict['category'] = transaction_dict['category_name']
                # 处理标签字段
                if 'tags' in transaction_dict and isinstance(transaction_dict['tags'], str):
                    # 如果tags是字符串格式，尝试分割为列表
                    transaction_dict['tags'] = [tag.strip() for tag in transaction_dict['tags'].split(',')]
                for field in target_fields:
                    if field in transaction_dict and 'destination_account' not in transaction_dict:
                        transaction_dict['destination_account'] = transaction_dict[field]
                        break
                if 'source_name' in transaction_dict and 'source_account' not in transaction_dict:
                    transaction_dict['source_account'] = transaction_dict['source_name']
                transaction_data = TransactionRequest(**transaction_dict)
            return transaction_data
        except ValidationError as e:
            app.logger.warning(f"[{transaction_id}] 交易数据验证失败: {e}")
            error_details = self._format_validation_errors(e.errors())
            return jsonify(APIResponseBuilder.error_response(
                f"交易数据验证失败: {error_details}", 400
            )), 400
        except Exception as e:
            app.logger.error(f"[{transaction_id}] 解析交易数据失败: {e}")
            return jsonify(APIResponseBuilder.error_response(
                "无效的交易数据格式", 400
            )), 400
    
    def _format_validation_errors(self, errors: list) -> str:
        """格式化验证错误信息
        
        Args:
            errors: Pydantic验证错误列表
            
        Returns:
            str: 格式化的错误信息
        """
        error_messages = []
        for error in errors[:3]:  # 只显示前3个错误
            field = '.'.join(str(loc) for loc in error['loc'])
            message = error['msg']
            error_messages.append(f"{field}: {message}")
        
        if len(errors) > 3:
            error_messages.append("...以及其他错误")
        
        return "; ".join(error_messages)
    
    def _log_transaction_info(self, transaction_data: TransactionRequest, transaction_id: str) -> None:
        """记录交易信息（安全方式）
        
        Args:
            transaction_data: 交易数据
            transaction_id: 交易ID
        """
        # 只记录非敏感信息
        safe_info = {
            'amount': str(transaction_data.amount),
            'description': (transaction_data.description[:50] + "..." if transaction_data.description and len(transaction_data.description) > 50 else transaction_data.description) if transaction_data.description else 'N/A',
            'source_account': (transaction_data.source_account[:10] + "..." if transaction_data.source_account and len(transaction_data.source_account) > 10 else transaction_data.source_account) if transaction_data.source_account else 'N/A',
            'destination_account': (transaction_data.destination_account[:10] + "..." if transaction_data.destination_account and len(transaction_data.destination_account) > 10 else transaction_data.destination_account) if transaction_data.destination_account else 'N/A',
            'category': (getattr(transaction_data, 'category', 'N/A')[:30] if getattr(transaction_data, 'category', None) else 'N/A'),
            'budget': (getattr(transaction_data, 'budget', 'N/A')[:30] if getattr(transaction_data, 'budget', None) else 'N/A')
        }
        
        app.logger.info(
            f"[{transaction_id}] 交易数据验证成功: {safe_info}"
        )
    
    def extract_transaction_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从Webhook数据中提取交易信息
        
        Args:
            data: Webhook数据
            
        Returns:
            Dict[str, Any]: 提取的交易信息
        """
        content = data.get('content', {})
        attributes = content.get('attributes', {})
        transactions = attributes.get('transactions', [])
        
        if not transactions:
            app.logger.warning("Webhook数据中未找到交易信息")
            return {}
        
        # 取第一个交易记录
        transaction = transactions[0]
        transaction_attrs = transaction.get('attributes', {})
        
        # 提取基本信息
        transaction_info = {
            'trigger': data.get('trigger', ''),
            'description': transaction_attrs.get('description', ''),
            'amount': transaction_attrs.get('amount', '0'),
            'currency_symbol': transaction_attrs.get('currency_symbol', ''),
            'date': transaction_attrs.get('date', '')
        }
        
        # 提取分类信息
        category = transaction_attrs.get('category')
        if category:
            transaction_info['category_name'] = category.get('name', '无分类')
        else:
            transaction_info['category_name'] = '无分类'
        
        # 提取预算信息（从分类中获取）
        if category and 'budget' in category:
            budget = category['budget']
            transaction_info['budget_name'] = budget.get('name', '无预算')
        else:
            transaction_info['budget_name'] = '无预算'
        
        return transaction_info
    
    def validate_transaction_webhook_data(self, data: Dict[str, Any]) -> Optional[str]:
        """验证交易Webhook数据的完整性
        
        Args:
            data: Webhook数据
            
        Returns:
            Optional[str]: 如果验证失败，返回错误信息；成功返回None
        """
        # 检查基本结构
        if 'content' not in data:
            return "缺少content字段"
        
        content = data['content']
        if 'attributes' not in content:
            return "缺少content.attributes字段"
        
        attributes = content['attributes']
        if 'transactions' not in attributes:
            return "缺少交易数据"
        
        transactions = attributes['transactions']
        if not isinstance(transactions, list) or len(transactions) == 0:
            return "交易数据为空或格式错误"
        
        # 检查第一个交易的基本字段
        transaction = transactions[0]
        if 'attributes' not in transaction:
            return "交易记录缺少attributes字段"
        
        transaction_attrs = transaction['attributes']
        required_fields = ['description', 'amount']
        
        for field in required_fields:
            if field not in transaction_attrs:
                return f"交易记录缺少必需字段: {field}"
        
        # 验证数据格式
        description = transaction_attrs.get('description', '')
        if not isinstance(description, str):
            return "描述字段必须是字符串"
        
        if len(description) > 500:
            return "描述字段长度不能超过500字符"
        
        try:
            amount = float(transaction_attrs.get('amount', '0'))
            if amount <= 0:
                return "金额必须大于0"
        except (ValueError, TypeError):
            return "金额格式错误"
        
        return None  # 验证通过
    
    def get_transaction_summary(self, transaction_info: Dict[str, Any]) -> Dict[str, str]:
        """获取交易摘要信息
        
        Args:
            transaction_info: 交易信息
            
        Returns:
            Dict[str, str]: 交易摘要
        """
        return {
            'action': transaction_info.get('trigger', 'UNKNOWN'),
            'description': transaction_info.get('description', '无描述')[:100],
            'amount': str(transaction_info.get('amount', '0')),
            'category': transaction_info.get('category_name', '无分类'),
            'budget': transaction_info.get('budget_name', '无预算'),
            'currency': transaction_info.get('currency_symbol', '')
        }