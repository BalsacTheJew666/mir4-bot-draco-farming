import quest.quest_handle

import ctypes
import struct
import threading
import time
import queue
import hashlib
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, List, Tuple, Callable

try:
    import win32api
    import win32con
    import win32gui
    import win32process
except ImportError:
    win32api = None
    win32con = None
    win32gui = None
    win32process = None

try:
    import pymem
    import pymem.process
except ImportError:
    pymem = None


class EngineState(Enum):
    IDLE = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    ERROR = auto()


@dataclass
class EngineConfig:
    process_name: str = "MIR4Client.exe"
    window_title: str = "MIR4"
    scan_interval: float = 0.1
    memory_buffer_size: int = 4096
    enable_logging: bool = True
    anti_detection: bool = True
    hwid_spoof: bool = True


class GameEngine:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.state = EngineState.IDLE
        self.config = EngineConfig()
        self._process_handle = None
        self._base_address = 0
        self._modules = {}
        self._hooks = []
        self._callbacks = {}
        self._thread_pool = []
        self._event_queue = queue.Queue()
        self._memory_cache = {}
        self._pattern_cache = {}
        self._offset_table = self._load_offset_table()
        
    def _load_offset_table(self) -> Dict[str, int]:
        return {
            "player_base": 0x02A8F4C0,
            "player_health": 0x1A4,
            "player_mana": 0x1A8,
            "player_stamina": 0x1AC,
            "player_position_x": 0x1B0,
            "player_position_y": 0x1B4,
            "player_position_z": 0x1B8,
            "darksteel_count": 0x2C4,
            "inventory_base": 0x02B1C8A0,
            "entity_list": 0x02A9D100,
            "mining_state": 0x3F8,
            "quest_manager": 0x02AC5E40,
            "network_manager": 0x02AE7B20,
        }
    
    def attach(self, process_name: Optional[str] = None) -> bool:
        if process_name:
            self.config.process_name = process_name
        self.state = EngineState.INITIALIZING
        
        try:
            self._scan_for_process()
            self._resolve_base_address()
            self._enumerate_modules()
            self._apply_hooks()
            self.state = EngineState.RUNNING
            return True
        except Exception as e:
            self.state = EngineState.ERROR
            raise RuntimeError(f"Failed to attach: {str(e)}")
    
    def _scan_for_process(self):
        import subprocess
        result = subprocess.run(
            ['tasklist', '/FI', f'IMAGENAME eq {self.config.process_name}'],
            capture_output=True, text=True
        )
        if self.config.process_name not in result.stdout:
            raise ProcessLookupError("MIR4 process not found")
        
        lines = result.stdout.strip().split('\n')
        for line in lines[3:]:
            parts = line.split()
            if len(parts) >= 2:
                self._process_handle = int(parts[1])
                break
    
    def _resolve_base_address(self):
        if pymem:
            pm = pymem.Pymem(self.config.process_name)
            self._base_address = pm.base_address
        else:
            self._base_address = 0x00400000
    
    def _enumerate_modules(self):
        self._modules = {
            "MIR4Client.exe": self._base_address,
            "UnityPlayer.dll": self._base_address + 0x10000000,
            "GameAssembly.dll": self._base_address + 0x20000000,
            "mono-2.0-bdwgc.dll": self._base_address + 0x30000000,
        }
    
    def _apply_hooks(self):
        hook_targets = [
            ("SendPacket", 0x1A5F40),
            ("RecvPacket", 0x1A6280),
            ("UpdatePosition", 0x2B8C10),
            ("ProcessMining", 0x3C4A20),
        ]
        for name, offset in hook_targets:
            self._hooks.append({
                "name": name,
                "address": self._base_address + offset,
                "original_bytes": b'\x00' * 16,
                "active": False
            })
    
    def read_memory(self, address: int, size: int) -> bytes:
        if address in self._memory_cache:
            return self._memory_cache[address]
        
        buffer = (ctypes.c_char * size)()
        bytes_read = ctypes.c_size_t()
        
        kernel32 = ctypes.windll.kernel32
        kernel32.ReadProcessMemory(
            self._process_handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        
        result = bytes(buffer)
        self._memory_cache[address] = result
        return result
    
    def write_memory(self, address: int, data: bytes) -> bool:
        bytes_written = ctypes.c_size_t()
        kernel32 = ctypes.windll.kernel32
        
        result = kernel32.WriteProcessMemory(
            self._process_handle,
            ctypes.c_void_p(address),
            data,
            len(data),
            ctypes.byref(bytes_written)
        )
        
        if address in self._memory_cache:
            del self._memory_cache[address]
        
        return bool(result)
    
    def pattern_scan(self, pattern: str, module: str = "MIR4Client.exe") -> int:
        cache_key = f"{module}:{pattern}"
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]
        
        pattern_bytes = bytes.fromhex(pattern.replace(" ", "").replace("?", "00"))
        mask = "".join("x" if c != "?" else "?" for c in pattern.split())
        
        base = self._modules.get(module, self._base_address)
        scan_size = 0x1000000
        
        for offset in range(0, scan_size, 0x1000):
            chunk = self.read_memory(base + offset, 0x1000)
            idx = chunk.find(pattern_bytes)
            if idx != -1:
                result = base + offset + idx
                self._pattern_cache[cache_key] = result
                return result
        
        return 0
    
    def get_player_position(self) -> Tuple[float, float, float]:
        player_base = self._base_address + self._offset_table["player_base"]
        x = struct.unpack('f', self.read_memory(player_base + self._offset_table["player_position_x"], 4))[0]
        y = struct.unpack('f', self.read_memory(player_base + self._offset_table["player_position_y"], 4))[0]
        z = struct.unpack('f', self.read_memory(player_base + self._offset_table["player_position_z"], 4))[0]
        return (x, y, z)
    
    def set_player_position(self, x: float, y: float, z: float) -> bool:
        player_base = self._base_address + self._offset_table["player_base"]
        success = True
        success &= self.write_memory(player_base + self._offset_table["player_position_x"], struct.pack('f', x))
        success &= self.write_memory(player_base + self._offset_table["player_position_y"], struct.pack('f', y))
        success &= self.write_memory(player_base + self._offset_table["player_position_z"], struct.pack('f', z))
        return success
    
    def get_darksteel_count(self) -> int:
        player_base = self._base_address + self._offset_table["player_base"]
        data = self.read_memory(player_base + self._offset_table["darksteel_count"], 4)
        return struct.unpack('I', data)[0]
    
    def detach(self):
        for hook in self._hooks:
            if hook["active"]:
                self.write_memory(hook["address"], hook["original_bytes"])
                hook["active"] = False
        
        self._memory_cache.clear()
        self._pattern_cache.clear()
        self._process_handle = None
        self.state = EngineState.IDLE
    
    def register_callback(self, event: str, callback: Callable):
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def emit_event(self, event: str, *args, **kwargs):
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception:
                    pass
