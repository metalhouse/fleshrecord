from typing import Dict, Any, Optional
from flask import current_app as app
import requests


class NotificationHandler:
    """处理通知发送的专用处理器"""
    
    def __init__(self, config: Any):
        self.config = config
    
    def send_webhook_message(self, message: str) -> bool:
        """发送消息到webhook URL
        
        Args:
            message: 要发送的消息内容
            
        Returns:
            bool: 发送是否成功
        """
        if not self.config.WEBHOOK_URL:
            app.logger.error("WEBHOOK_URL未配置")
            return False
        
        if not message.strip():
            app.logger.warning("消息内容为空，跳过发送")
            return False
        
        headers = self._build_headers()
        payload = self._build_payload(message)
        
        try:
            response = requests.post(
                self.config.WEBHOOK_URL, 
                json=payload, 
                headers=headers,
                timeout=30  # 添加超时设置
            )
            
            return self._handle_response(response, message)
            
        except requests.exceptions.Timeout:
            app.logger.error("发送消息超时")
            return False
        except requests.exceptions.ConnectionError:
            app.logger.error("连接Webhook URL失败")
            return False
        except requests.exceptions.RequestException as e:
            app.logger.error(f"发送消息时出错: {e}")
            return False
        except Exception as e:
            app.logger.error(f"发送消息时发生未知错误: {e}")
            return False
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            'Content-Type': 'application/json',
            'User-Agent': 'FleshRecord-Webhook/1.0'
        }
    
    def _build_payload(self, message: str) -> Dict[str, Any]:
        """构建消息载荷
        
        Args:
            message: 消息内容
            
        Returns:
            Dict[str, Any]: 格式化的载荷
        """
        return {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
    
    def _handle_response(self, response: requests.Response, message: str) -> bool:
        """处理响应结果
        
        Args:
            response: HTTP响应对象
            message: 原始消息内容
            
        Returns:
            bool: 处理是否成功
        """
        if response.status_code == 200:
            app.logger.info("消息发送成功")
            app.logger.debug(f"发送的消息内容: {message[:100]}..." if len(message) > 100 else f"发送的消息内容: {message}")
            return True
        else:
            app.logger.error(
                f"消息发送失败，状态码: {response.status_code}, "
                f"响应内容: {response.text[:200]}..."
            )
            return False
    
    def send_transaction_notification(self, transaction_info: Dict[str, Any], 
                                    budget_message: str = "") -> bool:
        """发送交易通知
        
        Args:
            transaction_info: 交易信息
            budget_message: 预算信息消息
            
        Returns:
            bool: 发送是否成功
        """
        # 构建基本交易消息
        base_message = self._build_transaction_message(transaction_info)
        
        # 组合完整消息
        full_message = base_message + budget_message
        
        app.logger.info(f"构造消息内容: {full_message}")
        
        return self.send_webhook_message(full_message)
    
    def _build_transaction_message(self, transaction_info: Dict[str, Any]) -> str:
        """构建交易消息
        
        Args:
            transaction_info: 交易信息
            
        Returns:
            str: 格式化的交易消息
        """
        trigger = transaction_info.get('trigger', '')
        description = transaction_info.get('description', '无描述')
        amount = transaction_info.get('amount', '0')
        category_name = transaction_info.get('category_name', '无分类')
        budget_name = transaction_info.get('budget_name', '无预算')
        
        if trigger == "UPDATE_TRANSACTION":
            message = (
                f"您更新了一笔交易：{description}, "
                f"费用：{amount}，分类：{category_name}，预算：{budget_name}。"
            )
        elif trigger == "STORE_TRANSACTION":
            message = (
                f"您新增了一笔交易：{description}, "
                f"费用：{amount}，分类：{category_name}，预算：{budget_name}。"
            )
        else:
            message = (
                f"交易操作：{description}, "
                f"费用：{amount}，分类：{category_name}，预算：{budget_name}。"
            )
        
        return message