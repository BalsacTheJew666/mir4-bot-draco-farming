import os
import time
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class LogLevel(Enum):
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


class Logger:
    def __init__(self, name: str = "MIR4Bot", log_file: Optional[str] = None):
        self._name = name
        self._log_file = log_file or f"logs/{name}_{datetime.now().strftime('%Y%m%d')}.log"
        self._level = LogLevel.INFO
        self._console_output = True
        self._file_output = True
        self._buffer = []
        self._max_buffer = 100
        
        os.makedirs("logs", exist_ok=True)
    
    def set_level(self, level: LogLevel):
        self._level = level
    
    def _format_message(self, level: LogLevel, message: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level.name}] [{self._name}] {message}"
    
    def _write(self, level: LogLevel, message: str):
        if level.value < self._level.value:
            return
        
        formatted = self._format_message(level, message)
        
        if self._console_output:
            print(formatted)
        
        if self._file_output:
            self._buffer.append(formatted)
            if len(self._buffer) >= self._max_buffer:
                self._flush()
    
    def _flush(self):
        if not self._buffer:
            return
        
        with open(self._log_file, 'a', encoding='utf-8') as f:
            for line in self._buffer:
                f.write(line + '\n')
        self._buffer.clear()
    
    def debug(self, message: str):
        self._write(LogLevel.DEBUG, message)
    
    def info(self, message: str):
        self._write(LogLevel.INFO, message)
    
    def warning(self, message: str):
        self._write(LogLevel.WARNING, message)
    
    def error(self, message: str):
        self._write(LogLevel.ERROR, message)
    
    def critical(self, message: str):
        self._write(LogLevel.CRITICAL, message)
    
    def close(self):
        self._flush()
