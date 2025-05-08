# File: utils/threading_utils.py
from functools import wraps
import threading

def thread_safe(lock_attr: str, lock_type=threading.RLock):
    """线程安全装饰器工厂（通用实现）
    
    :param lock_attr: 类实例中锁对象的属性名
    :param lock_type: 锁类型，默认为可重入锁 (RLock)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 动态获取或创建锁
            if not hasattr(self, lock_attr):
                setattr(self, lock_attr, lock_type())
            lock = getattr(self, lock_attr)
            with lock:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator