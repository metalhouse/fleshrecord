import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firefly_service import FireflyService
from utils.response_builder import APIResponseBuilder


class TestFireflyService(unittest.TestCase):
    def setUp(self):
        """测试前的设置"""
        self.api_url = "https://firefly.example.com/api/v1"
        self.access_token = "test_token"
        self.mock_logger = Mock()
        self.service = FireflyService(self.api_url, self.access_token, self.mock_logger)
    
    @patch('requests.get')
    def test_get_budget_limits_success(self, mock_get):
        """测试成功获取预算限制"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'type': 'budget_limits', 'id': '1', 'attributes': {'name': 'Test Budget'}}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # 执行测试
        result = self.service.get_budget_limits('1')
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertIn('data', result)
        mock_get.assert_called_once()
    
    @patch('requests.post')
    def test_add_transaction_success(self, mock_post):
        """测试成功添加交易"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {'type': 'transactions', 'id': '123', 'attributes': {'description': 'Test Transaction'}}
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # 测试数据
        transaction_data = {
            'description': 'Test Transaction',
            'amount': '100.00',
            'type': 'withdrawal'
        }
        
        # 执行测试
        result = self.service.add_transaction(transaction_data)
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], '交易添加成功')
        mock_post.assert_called_once()
    
    @patch('requests.get')
    def test_get_transactions_success(self, mock_get):
        """测试成功获取交易记录"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'type': 'transactions', 'id': '1', 'attributes': {'description': 'Transaction 1'}},
                {'type': 'transactions', 'id': '2', 'attributes': {'description': 'Transaction 2'}}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_response.apparent_encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        # 执行测试
        result = self.service.get_transactions({'limit': 10})
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(len(result['data']), 2)
        self.assertIn('查询成功', result['message'])
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_budget_limits_http_error(self, mock_get):
        """测试HTTP错误处理"""
        import requests
        mock_get.side_effect = requests.HTTPError("404 Not Found")
        
        # 执行测试
        result = self.service.get_budget_limits('invalid_id')
        
        # 验证结果
        self.assertFalse(result['success'])
        self.assertIn('HTTP错误', result['error'])
    
    @patch('requests.post')
    def test_add_transaction_request_error(self, mock_post):
        """测试网络请求错误处理"""
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")
        
        # 测试数据
        transaction_data = {'description': 'Test Transaction'}
        
        # 执行测试
        result = self.service.add_transaction(transaction_data)
        
        # 验证结果
        self.assertFalse(result['success'])
        self.assertIn('网络请求失败', result['error'])


if __name__ == '__main__':
    unittest.main()