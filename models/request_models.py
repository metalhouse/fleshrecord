# models/request_models.py
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

class DifyWebhookRequest(BaseModel):
    api_endpoint: str
    method: str = "GET"
    query_parameters: Optional[dict] = {}
    
    @field_validator('api_endpoint')
    def validate_endpoint(cls, v):
        allowed_endpoints = ['/budgets', '/transactions']
        if v not in allowed_endpoints:
            raise ValueError(f'不支持的端点: {v}')
        return v
    
    @field_validator('method')
    def validate_method(cls, v):
        if v.upper() != 'GET':
            raise ValueError('只支持GET方法')
        return v.upper()

class BudgetQueryParams(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    budget_id: Optional[str] = None
    include: str = "spent"
    
    @field_validator('start', 'end')
    def validate_date_format(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('日期格式应为 YYYY-MM-DD')
        return v


class TransactionRequest(BaseModel):
    """交易请求模型"""
    amount: float
    description: str
    date: str
    source_account: str
    destination_account: Optional[str] = None
    category: Optional[str] = None
    budget: Optional[str] = None
    tags: Optional[List[str]] = None
    
    @field_validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('金额必须大于0')
        return v
    
    @field_validator('date')
    def validate_date(cls, v):
        # 支持带时间的日期格式，如'2025-06-26T20:00:00+08:00'
        try:
            # 尝试解析带时间的格式
            parsed_date = datetime.fromisoformat(v)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            try:
                # 尝试解析不带时间的格式
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('日期格式应为 YYYY-MM-DD 或包含时间的ISO格式')
        return v