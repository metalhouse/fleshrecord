import requests
import logging
from utils.retry_decorator import retry_on_failure
from utils.response_builder import APIResponseBuilder
from utils.sensitive_data_filter import SensitiveDataFilter

class FireflyService:
    def __init__(self, api_url, access_token, logger=None):
        self.api_url = api_url
        # 确保access_token不包含重复的'Bearer'前缀
        clean_token = access_token.replace('Bearer ', '').strip()
        self.headers = {'Authorization': f'Bearer {clean_token}', 'Accept': 'application/json'}
        self.logger = logger or logging.getLogger(__name__)
    
    def get_budget_limits(self, budget_id, query_params=None):
        """专门处理预算限制查询的服务方法"""
        strategies = [
            self._get_budget_limits_by_id,
            self._get_budget_limits_from_all,
            self._get_available_budgets
        ]
        
        for strategy in strategies:
            try:
                result = strategy(budget_id, query_params)
                if result and result.get('total_limit', 0) > 0:
                    self.logger.info(f"成功获取预算限制: {result}")
                    return result
            except Exception as e:
                self.logger.warning(f"策略 {strategy.__name__} 失败: {e}")
                continue
        
        return {'total_limit': 0, 'current_limit': 0}
    
    @retry_on_failure(max_attempts=3, delay=1.0)
    def _get_budget_limits_by_id(self, budget_id, query_params=None):
        """方法1: 直接通过预算ID获取预算限制"""
        params = {}
        if query_params:
            if query_params.get('start'):
                params['start'] = query_params['start']
            if query_params.get('end'):
                params['end'] = query_params['end']
        
        url = f"{self.api_url}/budgets/{budget_id}/limits"
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json().get('data', [])
        if not data:
            return None
        
        total_limit = sum(float(item.get('attributes', {}).get('amount', 0)) for item in data)
        current_limit = max(float(item.get('attributes', {}).get('amount', 0)) for item in data) if data else 0
        
        return {'total_limit': total_limit, 'current_limit': current_limit}
    
    @retry_on_failure(max_attempts=3, delay=1.0)
    def _get_budget_limits_from_all(self, budget_id, query_params=None):
        """方法2: 从所有预算限制中筛选"""
        params = {}
        if query_params:
            if query_params.get('start'):
                params['start'] = query_params['start']
            if query_params.get('end'):
                params['end'] = query_params['end']
        
        url = f"{self.api_url}/budget_limits"
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json().get('data', [])
        budget_limits = [
            item for item in data 
            if item.get('relationships', {}).get('budget', {}).get('data', {}).get('id') == str(budget_id)
        ]
        
        if not budget_limits:
            return None
        
        total_limit = sum(float(item.get('attributes', {}).get('amount', 0)) for item in budget_limits)
        current_limit = max(float(item.get('attributes', {}).get('amount', 0)) for item in budget_limits) if budget_limits else 0
        
        return {'total_limit': total_limit, 'current_limit': current_limit}
    
    @retry_on_failure(max_attempts=2, delay=0.5)
    def _get_available_budgets(self, budget_id, query_params=None):
        """方法3: 从可用预算中获取"""
        url = f"{self.api_url}/available_budgets"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        data = response.json().get('data', [])
        for budget_data in data:
            if budget_data.get('id') == str(budget_id):
                spent = float(budget_data.get('attributes', {}).get('spent', [{}])[0].get('sum', 0))
                auto_budget = float(budget_data.get('attributes', {}).get('auto_budget_amount', 0))
                fallback_limit = auto_budget * 4 if auto_budget > 0 else 1000
                
                return {'total_limit': fallback_limit, 'current_limit': fallback_limit}
        
        return None
    

    
    @retry_on_failure(max_attempts=3, exceptions=(requests.RequestException,))
    def add_transaction(self, transaction_data) -> dict:
        """添加新的交易记录"""
        try:
            # 处理TransactionRequest对象或字典
            if hasattr(transaction_data, 'description'):
                description = transaction_data.description
            else:
                description = transaction_data.get('description', 'N/A')
            
            self.logger.info(f"添加交易记录: {description}")
            
            # 将TransactionRequest对象转换为字典
            if hasattr(transaction_data, 'model_dump'):
                # Pydantic v2模型
                raw_data = transaction_data.model_dump()
            elif hasattr(transaction_data, 'dict'):
                # Pydantic v1模型
                raw_data = transaction_data.dict()
            else:
                # 已经是字典
                raw_data = transaction_data
            
            # 构建符合Firefly III API格式的请求数据
            # 构建交易数据，包含预算、分类和标签字段
            firefly_transaction = {
                "type": "withdrawal",  # 默认为支出，可根据需要调整
                "date": raw_data.get('date'),
                "amount": str(raw_data.get('amount')),  # Firefly III通常期望字符串格式的金额
                "description": raw_data.get('description'),
                "source_name": raw_data.get('source_account'),
                "destination_name": raw_data.get('destination_account'),
                "category_name": raw_data.get('category'),
                "budget_name": raw_data.get('budget'),
                # 添加标签字段
                "tags": raw_data.get('tags')
            }
            
            # 移除None值
            firefly_transaction = {k: v for k, v in firefly_transaction.items() if v is not None}
            
            # 包装在transactions数组中
            json_data = {
                "transactions": [firefly_transaction]
            }
            
            # 过滤敏感信息后记录
            safe_json_data = SensitiveDataFilter.filter_dict(json_data)
            self.logger.info(f"发送到Firefly III的数据: {safe_json_data}")
            
            response = requests.post(
                f"{self.api_url}/transactions",
                headers=self.headers,
                json=json_data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"交易添加成功: {result.get('data', {}).get('id', 'N/A')}")
            return APIResponseBuilder.success_response(result, "交易添加成功")
            
        except requests.HTTPError as e:
            self.logger.error(f"HTTP错误 - 添加交易失败: {e}")
            return APIResponseBuilder.error_response(f"HTTP错误: {str(e)}", code=e.response.status_code if e.response else 500)
        except requests.RequestException as e:
            self.logger.error(f"请求异常 - 添加交易失败: {e}")
            return APIResponseBuilder.error_response(f"网络请求失败: {str(e)}", code=500)
        except Exception as e:
            self.logger.error(f"未知错误 - 添加交易失败: {e}", exc_info=True)
            return APIResponseBuilder.error_response(f"添加交易时发生错误: {str(e)}", code=500)
    
    @retry_on_failure(max_attempts=3, exceptions=(requests.RequestException,))
    def get_transactions(self, query_params: dict = None) -> dict:
        """查询交易记录"""
        try:
            params = query_params or {}
            self.logger.info(f"查询交易记录，参数: {params}")
            
            # 确保获取所有记录，设置较大的limit或者通过分页获取
            all_transactions = []
            page = 1
            total_records = 0
            
            while True:
                # 设置分页参数
                current_params = params.copy()
                current_params['page'] = page
                current_params['limit'] = 200  # 每页获取200条记录
                
                # 构建完整的请求 URL 用于调试
                full_url = f"{self.api_url}/transactions"
                if page == 1:  # 只在第一页记录详细信息
                    self.logger.info(f"请求 URL: {full_url}")
                    self.logger.info(f"请求参数: {current_params}")
                
                response = requests.get(
                    full_url,
                    headers=self.headers,
                    params=current_params,
                    timeout=30
                )
                
                # 记录实际请求的 URL（包含查询参数）
                if page == 1:
                    self.logger.info(f"实际发送的完整 URL: {response.url}")
                
                response.raise_for_status()
                
                # 处理响应编码问题
                try:
                    response.encoding = response.apparent_encoding
                    result = response.json()
                except UnicodeDecodeError:
                    response.encoding = 'utf-8'
                    result = response.json()
                
                page_transactions = result.get('data', [])
                meta_info = result.get('meta', {})
                pagination_info = meta_info.get('pagination', {})
                total_records = pagination_info.get('total', len(page_transactions))
                current_page = pagination_info.get('current_page', page)
                last_page = pagination_info.get('last_page', page)
                
                all_transactions.extend(page_transactions)
                
                self.logger.info(f"获取第 {current_page} 页，本页 {len(page_transactions)} 条记录，总计 {len(all_transactions)} 条")
                
                # 如果是最后一页或者没有更多记录，退出循环
                if current_page >= last_page or len(page_transactions) == 0:
                    break
                    
                page += 1
            
            transactions_data = all_transactions
            self.logger.info(f"成功查询到 {len(transactions_data)} 条交易记录，API总共 {total_records} 条")
            
            # 如果有category参数，进行客户端过滤
            filtered_data = transactions_data
            category_filter = (query_params or {}).get('category')
            if category_filter:
                filtered_transactions = []
                self.logger.info(f"开始类目过滤，目标类目: {category_filter}")
                for idx, transaction in enumerate(transactions_data):
                    if isinstance(transaction, dict) and 'attributes' in transaction:
                        has_category = False
                        transaction_info = []
                        for split in transaction['attributes'].get('transactions', []):
                            date = split.get('date', 'NO_DATE')
                            description = split.get('description', 'NO_DESC')
                            amount = split.get('amount', 'NO_AMOUNT')
                            category = split.get('category_name', 'NO_CATEGORY')
                            transaction_info.append(f"日期:{date}, 描述:{description}, 金额:{amount}, 类目:{category}")
                            
                            if category == category_filter:
                                has_category = True
                                
                        # 记录每笔交易的详细信息用于调试
                        if idx < 10:  # 只记录前10笔交易避免日志过长
                            self.logger.info(f"交易 {idx+1}: {'; '.join(transaction_info)}")
                            
                        if has_category:
                            filtered_transactions.append(transaction)
                
                filtered_data = filtered_transactions
                #self.logger.info(f"类目过滤后剩余 {len(filtered_data)} 条交易记录（类目: {category_filter}）")
            
            # 调试：统计类目分布
            if transactions_data and len(transactions_data) > 0:
                first_transaction = transactions_data[0]
                #self.logger.info(f"第一条交易记录的结构: {list(first_transaction.keys()) if isinstance(first_transaction, dict) else 'UNKNOWN_TYPE'}")
                if isinstance(first_transaction, dict) and 'attributes' in first_transaction:
                    attributes = first_transaction['attributes']
                    if 'transactions' in attributes and len(attributes['transactions']) > 0:
                        first_split = attributes['transactions'][0]
                        #self.logger.info(f"第一条交易分录的类目: {first_split.get('category_name', 'NO_CATEGORY')}")
                        #self.logger.info(f"第一条交易分录的类型: {first_split.get('type', 'NO_TYPE')}")
                        
                # 统计不同类目的交易数量
                category_counts = {}
                for transaction in transactions_data:
                    if isinstance(transaction, dict) and 'attributes' in transaction:
                        for split in transaction['attributes'].get('transactions', []):
                            category = split.get('category_name', 'NO_CATEGORY')
                            category_counts[category] = category_counts.get(category, 0) + 1
                #self.logger.info(f"API返回的类目分布: {category_counts}")
            
            return {
                'success': True,
                'data': filtered_data,
                'meta': meta_info,
                'total_records': total_records,
                'filtered_count': len(filtered_data),
                'message': f"查询成功，当前页 {len(filtered_data)} 条记录，总共 {total_records} 条记录"
            }
            
        except requests.HTTPError as e:
            self.logger.error(f"HTTP错误 - 查询交易失败: {e}")
            return {
                'success': False,
                'error': f"HTTP错误: {str(e)}",
                'status_code': e.response.status_code if e.response else 500
            }
        except requests.RequestException as e:
            self.logger.error(f"请求异常 - 查询交易失败: {e}")
            return {
                'success': False,
                'error': f"网络请求失败: {str(e)}",
                'status_code': 500
            }
        except Exception as e:
            self.logger.error(f"未知错误 - 查询交易失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"查询交易时发生错误: {str(e)}",
                'status_code': 500
            }