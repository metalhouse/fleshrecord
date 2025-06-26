# utils/response_builder.py
from typing import Dict, Any, List
from datetime import datetime

class APIResponseBuilder:
    @staticmethod
    def success_response(data: Any, message: str = "操作成功") -> Dict[str, Any]:
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def error_response(error: str, code: int = 500) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": error,
            "code": code,
            "timestamp": datetime.now().isoformat()
        }