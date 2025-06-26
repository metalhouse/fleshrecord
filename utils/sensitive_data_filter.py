from typing import Dict, Any, List, Union
import re


class SensitiveDataFilter:
    """敏感数据过滤器"""
    
    # 敏感字段列表
    SENSITIVE_FIELDS = {
        'amount', 'foreign_amount', 'salary', 'balance', 'total',
        'password', 'token', 'key', 'secret', 'authorization',
        'cookie', 'session', 'credit_card', 'bank_account'
    }
    
    # 敏感头信息列表
    SENSITIVE_HEADERS = {
        'authorization', 'cookie', 'x-api-key', 'x-auth-token',
        'bearer', 'session', 'csrf-token'
    }
    
    @classmethod
    def filter_dict(cls, data: Dict[str, Any], filter_value: str = '[FILTERED]') -> Dict[str, Any]:
        """过滤字典中的敏感信息
        
        Args:
            data: 要过滤的字典数据
            filter_value: 替换敏感信息的值
            
        Returns:
            Dict[str, Any]: 过滤后的字典
        """
        if not isinstance(data, dict):
            return data
            
        filtered_data = {}
        for key, value in data.items():
            if cls._is_sensitive_field(key):
                filtered_data[key] = filter_value
            elif isinstance(value, dict):
                filtered_data[key] = cls.filter_dict(value, filter_value)
            elif isinstance(value, list):
                filtered_data[key] = cls.filter_list(value, filter_value)
            else:
                filtered_data[key] = value
                
        return filtered_data
    
    @classmethod
    def filter_list(cls, data: List[Any], filter_value: str = '[FILTERED]') -> List[Any]:
        """过滤列表中的敏感信息
        
        Args:
            data: 要过滤的列表数据
            filter_value: 替换敏感信息的值
            
        Returns:
            List[Any]: 过滤后的列表
        """
        if not isinstance(data, list):
            return data
            
        filtered_list = []
        for item in data:
            if isinstance(item, dict):
                filtered_list.append(cls.filter_dict(item, filter_value))
            elif isinstance(item, list):
                filtered_list.append(cls.filter_list(item, filter_value))
            else:
                filtered_list.append(item)
                
        return filtered_list
    
    @classmethod
    def filter_headers(cls, headers: Dict[str, str], filter_value: str = '[FILTERED]') -> Dict[str, str]:
        """过滤HTTP头中的敏感信息
        
        Args:
            headers: HTTP头字典
            filter_value: 替换敏感信息的值
            
        Returns:
            Dict[str, str]: 过滤后的HTTP头
        """
        filtered_headers = {}
        for key, value in headers.items():
            if key.lower() in cls.SENSITIVE_HEADERS:
                filtered_headers[key] = filter_value
            else:
                filtered_headers[key] = value
                
        return filtered_headers
    
    @classmethod
    def filter_message(cls, message: str, filter_value: str = '[FILTERED]') -> str:
        """过滤消息文本中的敏感信息
        
        Args:
            message: 要过滤的消息文本
            filter_value: 替换敏感信息的值
            
        Returns:
            str: 过滤后的消息文本
        """
        # 过滤金额信息（支持各种货币格式）
        amount_patterns = [
            r'费用：[\d,.]+(\.[\d]+)?',  # 费用：123.45
            r'金额：[\d,.]+(\.[\d]+)?',  # 金额：123.45
            r'余额：[\d,.]+(\.[\d]+)?',  # 余额：123.45
            r'工资：[\d,.]+(\.[\d]+)?',  # 工资：123.45
            r'¥[\d,.]+(\.[\d]+)?',     # ¥123.45
            r'￥[\d,.]+(\.[\d]+)?',     # ￥123.45
            r'\$[\d,.]+(\.[\d]+)?',     # $123.45
            r'€[\d,.]+(\.[\d]+)?',     # €123.45
        ]
        
        filtered_message = message
        for pattern in amount_patterns:
            if '费用：' in pattern:
                filtered_message = re.sub(pattern, f'费用：{filter_value}', filtered_message)
            elif '金额：' in pattern:
                filtered_message = re.sub(pattern, f'金额：{filter_value}', filtered_message)
            elif '余额：' in pattern:
                filtered_message = re.sub(pattern, f'余额：{filter_value}', filtered_message)
            elif '工资：' in pattern:
                filtered_message = re.sub(pattern, f'工资：{filter_value}', filtered_message)
            else:
                filtered_message = re.sub(pattern, filter_value, filtered_message)
                
        return filtered_message
    
    @classmethod
    def _is_sensitive_field(cls, field_name: str) -> bool:
        """判断字段是否为敏感字段
        
        Args:
            field_name: 字段名
            
        Returns:
            bool: 是否为敏感字段
        """
        field_lower = field_name.lower()
        
        # 精确匹配
        if field_lower in cls.SENSITIVE_FIELDS:
            return True
            
        # 模糊匹配
        sensitive_keywords = ['amount', 'balance', 'salary', 'password', 'token', 'key', 'secret']
        for keyword in sensitive_keywords:
            if keyword in field_lower:
                return True
                
        return False