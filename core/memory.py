import ctypes
import struct
import threading
import mmap
import os
from typing import Optional, List, Dict, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum

try:
    import numpy as np
except ImportError:
    np = None

try:
    import pymem
    import pymem.pattern
    import pymem.memory
except ImportError:
    pymem = None


class MemoryProtection(Enum):
    PAGE_NOACCESS = 0x01
    PAGE_READONLY = 0x02
    PAGE_READWRITE = 0x04
    PAGE_WRITECOPY = 0x08
    PAGE_EXECUTE = 0x10
    PAGE_EXECUTE_READ = 0x20
    PAGE_EXECUTE_READWRITE = 0x40


@dataclass
class MemoryRegion:
    base_address: int
    size: int
    protection: MemoryProtection
    state: int
    type_: int


class MemoryReader:
    def __init__(self, process_handle: int):
        self._handle = process_handle
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._buffer_pool = []
        self._max_cache_size = 1024
        
    def read_bytes(self, address: int, size: int) -> bytes:
        with self._cache_lock:
            cache_key = (address, size)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        buffer = (ctypes.c_char * size)()
        bytes_read = ctypes.c_size_t()
        
        kernel32 = ctypes.windll.kernel32
        success = kernel32.ReadProcessMemory(
            self._handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        
        if not success:
            raise MemoryError(f"Failed to read memory at {hex(address)}")
        
        result = bytes(buffer)
        
        with self._cache_lock:
            if len(self._cache) < self._max_cache_size:
                self._cache[cache_key] = result
        
        return result
    
    def read_int(self, address: int) -> int:
        data = self.read_bytes(address, 4)
        return struct.unpack('<i', data)[0]
    
    def read_uint(self, address: int) -> int:
        data = self.read_bytes(address, 4)
        return struct.unpack('<I', data)[0]
    
    def read_int64(self, address: int) -> int:
        data = self.read_bytes(address, 8)
        return struct.unpack('<q', data)[0]
    
    def read_float(self, address: int) -> float:
        data = self.read_bytes(address, 4)
        return struct.unpack('<f', data)[0]
    
    def read_double(self, address: int) -> float:
        data = self.read_bytes(address, 8)
        return struct.unpack('<d', data)[0]
    
    def read_string(self, address: int, max_length: int = 256, encoding: str = 'utf-8') -> str:
        data = self.read_bytes(address, max_length)
        null_pos = data.find(b'\x00')
        if null_pos != -1:
            data = data[:null_pos]
        return data.decode(encoding, errors='ignore')
    
    def read_pointer(self, address: int, offsets: List[int]) -> int:
        current = self.read_uint(address)
        for offset in offsets[:-1]:
            current = self.read_uint(current + offset)
        return current + offsets[-1] if offsets else current
    
    def clear_cache(self):
        with self._cache_lock:
            self._cache.clear()


class MemoryWriter:
    def __init__(self, process_handle: int):
        self._handle = process_handle
        self._write_queue = []
        self._batch_mode = False
        
    def write_bytes(self, address: int, data: bytes) -> bool:
        if self._batch_mode:
            self._write_queue.append((address, data))
            return True
        
        bytes_written = ctypes.c_size_t()
        kernel32 = ctypes.windll.kernel32
        
        old_protect = ctypes.c_ulong()
        kernel32.VirtualProtectEx(
            self._handle,
            ctypes.c_void_p(address),
            len(data),
            MemoryProtection.PAGE_EXECUTE_READWRITE.value,
            ctypes.byref(old_protect)
        )
        
        success = kernel32.WriteProcessMemory(
            self._handle,
            ctypes.c_void_p(address),
            data,
            len(data),
            ctypes.byref(bytes_written)
        )
        
        kernel32.VirtualProtectEx(
            self._handle,
            ctypes.c_void_p(address),
            len(data),
            old_protect.value,
            ctypes.byref(old_protect)
        )
        
        return bool(success)
    
    def write_int(self, address: int, value: int) -> bool:
        return self.write_bytes(address, struct.pack('<i', value))
    
    def write_uint(self, address: int, value: int) -> bool:
        return self.write_bytes(address, struct.pack('<I', value))
    
    def write_float(self, address: int, value: float) -> bool:
        return self.write_bytes(address, struct.pack('<f', value))
    
    def write_double(self, address: int, value: float) -> bool:
        return self.write_bytes(address, struct.pack('<d', value))
    
    def begin_batch(self):
        self._batch_mode = True
        self._write_queue.clear()
    
    def commit_batch(self) -> bool:
        self._batch_mode = False
        success = True
        for address, data in self._write_queue:
            success &= self.write_bytes(address, data)
        self._write_queue.clear()
        return success
    
    def nop_bytes(self, address: int, count: int) -> bool:
        return self.write_bytes(address, b'\x90' * count)


class MemoryScanner:
    def __init__(self, process_handle: int):
        self._handle = process_handle
        self._regions = []
        self._scan_results = []
        
    def enumerate_regions(self) -> List[MemoryRegion]:
        self._regions.clear()
        
        kernel32 = ctypes.windll.kernel32
        
        class MEMORY_BASIC_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", ctypes.c_ulong),
                ("RegionSize", ctypes.c_size_t),
                ("State", ctypes.c_ulong),
                ("Protect", ctypes.c_ulong),
                ("Type", ctypes.c_ulong),
            ]
        
        mbi = MEMORY_BASIC_INFORMATION()
        address = 0
        
        while address < 0x7FFFFFFF:
            result = kernel32.VirtualQueryEx(
                self._handle,
                ctypes.c_void_p(address),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi)
            )
            
            if result == 0:
                break
            
            if mbi.State == 0x1000:
                region = MemoryRegion(
                    base_address=mbi.BaseAddress,
                    size=mbi.RegionSize,
                    protection=MemoryProtection(mbi.Protect & 0xFF),
                    state=mbi.State,
                    type_=mbi.Type
                )
                self._regions.append(region)
            
            address = mbi.BaseAddress + mbi.RegionSize
        
        return self._regions
    
    def aob_scan(self, pattern: str, start: int = 0, end: int = 0x7FFFFFFF) -> List[int]:
        results = []
        pattern_bytes = []
        mask = []
        
        for byte_str in pattern.split():
            if byte_str == "??" or byte_str == "?":
                pattern_bytes.append(0)
                mask.append(False)
            else:
                pattern_bytes.append(int(byte_str, 16))
                mask.append(True)
        
        reader = MemoryReader(self._handle)
        
        for region in self._regions:
            if region.base_address < start or region.base_address > end:
                continue
            
            try:
                data = reader.read_bytes(region.base_address, region.size)
                
                for i in range(len(data) - len(pattern_bytes)):
                    match = True
                    for j, (pb, m) in enumerate(zip(pattern_bytes, mask)):
                        if m and data[i + j] != pb:
                            match = False
                            break
                    
                    if match:
                        results.append(region.base_address + i)
            except:
                continue
        
        self._scan_results = results
        return results
    
    def value_scan(self, value: Any, value_type: str = 'int') -> List[int]:
        results = []
        reader = MemoryReader(self._handle)
        
        if value_type == 'int':
            target = struct.pack('<i', value)
        elif value_type == 'float':
            target = struct.pack('<f', value)
        elif value_type == 'double':
            target = struct.pack('<d', value)
        else:
            target = value.encode() if isinstance(value, str) else bytes(value)
        
        for region in self._regions:
            try:
                data = reader.read_bytes(region.base_address, region.size)
                offset = 0
                while True:
                    idx = data.find(target, offset)
                    if idx == -1:
                        break
                    results.append(region.base_address + idx)
                    offset = idx + 1
            except:
                continue
        
        self._scan_results = results
        return results
    
    def filter_results(self, new_value: Any, value_type: str = 'int') -> List[int]:
        reader = MemoryReader(self._handle)
        filtered = []
        
        for address in self._scan_results:
            try:
                if value_type == 'int':
                    current = reader.read_int(address)
                elif value_type == 'float':
                    current = reader.read_float(address)
                else:
                    current = reader.read_bytes(address, len(new_value))
                
                if current == new_value:
                    filtered.append(address)
            except:
                continue
        
        self._scan_results = filtered
        return filtered
