# models/request_models.py
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class DifyWebhookRequest(BaseModel):
    api_endpoint: str
    method: str = "GET"
    query_parameters: Optional[dict] = {}
    
    @validator('api_endpoint')
    def validate_endpoint(cls, v):
        allowed_endpoints = ['/budgets', '/transactions']
        if v not in allowed_endpoints:
            raise ValueError(f'不支持的端点: {v}')
        return v
    
    @validator('method')
    def validate_method(cls, v):
        if v.upper() != 'GET':
            raise ValueError('只支持GET方法')
        return v.upper()

class BudgetQueryParams(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    include: str = "spent"
    
    @validator('start', 'end')
    def validate_date_format(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('日期格式应为 YYYY-MM-DD')
        return v