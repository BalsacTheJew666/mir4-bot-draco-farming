import quest.quest_handle

import functools
import threading
import time
from typing import Callable, Optional


class Timer:
    def __init__(self):
        self._start_time: Optional[float] = None
        self._elapsed = 0.0
        self._running = False
    
    def start(self):
        if not self._running:
            self._start_time = time.time()
            self._running = True
    
    def stop(self) -> float:
        if self._running:
            self._elapsed += time.time() - self._start_time
            self._running = False
        return self._elapsed
    
    def reset(self):
        self._elapsed = 0.0
        self._start_time = None
        self._running = False
    
    def get_elapsed(self) -> float:
        if self._running:
            return self._elapsed + (time.time() - self._start_time)
        return self._elapsed
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self._max_calls = max_calls
        self._period = period
        self._calls = []
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        with self._lock:
            now = time.time()
            self._calls = [t for t in self._calls if now - t < self._period]
            
            if len(self._calls) < self._max_calls:
                self._calls.append(now)
                return True
            return False
    
    def wait(self):
        while not self.acquire():
            time.sleep(0.1)
    
    def reset(self):
        with self._lock:
            self._calls.clear()


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
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
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def format_duration(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_number(num: int) -> str:
    if num >= 1000000:
        return f"{num/1000000:.2f}M"
    elif num >= 1000:
        return f"{num/1000:.2f}K"
    return str(num)
