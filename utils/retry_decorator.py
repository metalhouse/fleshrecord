# utils/retry_decorator.py
import time
import functools
import requests
from typing import Callable, Type, Tuple

def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (requests.RequestException,)
):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(
                            f"第 {attempt + 1} 次尝试失败: {e}, {delay}秒后重试"
                        )
                        time.sleep(delay * (2 ** attempt))  # 指数退避
                    else:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"所有 {max_attempts} 次尝试均失败")
            
            raise last_exception
        return wrapper
    return decorator