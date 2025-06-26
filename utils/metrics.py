# utils/metrics.py
import time
from functools import wraps
from collections import defaultdict, deque
from threading import Lock

class SimpleMetrics:
    def __init__(self):
        self._counters = defaultdict(int)
        self._timings = defaultdict(list)
        self._lock = Lock()
    
    def increment(self, metric_name: str, value: int = 1):
        with self._lock:
            self._counters[metric_name] += value
    
    def timing(self, metric_name: str, duration: float):
        with self._lock:
            self._timings[metric_name].append(duration)
            # 只保留最近100个记录
            if len(self._timings[metric_name]) > 100:
                self._timings[metric_name].pop(0)
    
    def get_stats(self):
        with self._lock:
            stats = {
                'counters': dict(self._counters),
                'timings': {}
            }
            
            for name, times in self._timings.items():
                if times:
                    stats['timings'][name] = {
                        'avg': sum(times) / len(times),
                        'count': len(times),
                        'min': min(times),
                        'max': max(times)
                    }
            
            return stats

metrics = SimpleMetrics()

def track_performance(metric_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                metrics.increment(f"{metric_name}.success")
                return result
            except Exception as e:
                metrics.increment(f"{metric_name}.error")
                raise
            finally:
                duration = time.time() - start_time
                metrics.timing(metric_name, duration)
        return wrapper
    return decorator