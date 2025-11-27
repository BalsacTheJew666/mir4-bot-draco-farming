import ctypes
import os
import sys
import subprocess
import threading
import time
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import psutil
except ImportError:
    psutil = None

try:
    import win32api
    import win32con
    import win32process
    import win32security
except ImportError:
    win32api = None
    win32con = None
    win32process = None
    win32security = None


class ProcessState(Enum):
    NOT_FOUND = 0
    RUNNING = 1
    SUSPENDED = 2
    TERMINATED = 3


@dataclass
class ProcessInfo:
    pid: int
    name: str
    path: str
    base_address: int
    window_handle: int
    state: ProcessState


@dataclass
class ModuleInfo:
    name: str
    base_address: int
    size: int
    path: str


class ProcessManager:
    def __init__(self):
        self._processes: Dict[int, ProcessInfo] = {}
        self._target_process: Optional[ProcessInfo] = None
        self._handle: Optional[int] = None
        self._modules: List[ModuleInfo] = []
        self._refresh_interval = 1.0
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        
    def find_process(self, name: str) -> Optional[ProcessInfo]:
        if psutil:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'].lower() == name.lower():
                        info = ProcessInfo(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            path=proc.info['exe'] or "",
                            base_address=0,
                            window_handle=0,
                            state=ProcessState.RUNNING
                        )
                        self._processes[info.pid] = info
                        return info
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        else:
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {name}', '/FO', 'CSV'],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].replace('"', '').split(',')
                if len(parts) >= 2:
                    info = ProcessInfo(
                        pid=int(parts[1]),
                        name=parts[0],
                        path="",
                        base_address=0,
                        window_handle=0,
                        state=ProcessState.RUNNING
                    )
                    self._processes[info.pid] = info
                    return info
        
        return None
    
    def attach(self, pid: int) -> bool:
        PROCESS_ALL_ACCESS = 0x1F0FFF
        
        kernel32 = ctypes.windll.kernel32
        self._handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        
        if self._handle:
            self._target_process = self._processes.get(pid)
            self._enumerate_modules()
            return True
        
        return False
    
    def _enumerate_modules(self):
        if not self._handle:
            return
        
        self._modules.clear()
        
        class MODULEENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_ulong),
                ("th32ModuleID", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong),
                ("GlsblcntUsage", ctypes.c_ulong),
                ("ProccntUsage", ctypes.c_ulong),
                ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", ctypes.c_ulong),
                ("hModule", ctypes.c_void_p),
                ("szModule", ctypes.c_char * 256),
                ("szExePath", ctypes.c_char * 260),
            ]
        
        kernel32 = ctypes.windll.kernel32
        TH32CS_SNAPMODULE = 0x00000008
        TH32CS_SNAPMODULE32 = 0x00000010
        
        snapshot = kernel32.CreateToolhelp32Snapshot(
            TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
            self._target_process.pid if self._target_process else 0
        )
        
        if snapshot == -1:
            return
        
        me32 = MODULEENTRY32()
        me32.dwSize = ctypes.sizeof(MODULEENTRY32)
        
        if kernel32.Module32First(snapshot, ctypes.byref(me32)):
            while True:
                module = ModuleInfo(
                    name=me32.szModule.decode('utf-8', errors='ignore'),
                    base_address=me32.modBaseAddr,
                    size=me32.modBaseSize,
                    path=me32.szExePath.decode('utf-8', errors='ignore')
                )
                self._modules.append(module)
                
                if not kernel32.Module32Next(snapshot, ctypes.byref(me32)):
                    break
        
        kernel32.CloseHandle(snapshot)
    
    def get_module(self, name: str) -> Optional[ModuleInfo]:
        for module in self._modules:
            if module.name.lower() == name.lower():
                return module
        return None
    
    def suspend(self) -> bool:
        if not self._target_process:
            return False
        
        ntdll = ctypes.windll.ntdll
        result = ntdll.NtSuspendProcess(self._handle)
        
        if result == 0:
            self._target_process.state = ProcessState.SUSPENDED
            return True
        return False
    
    def resume(self) -> bool:
        if not self._target_process:
            return False
        
        ntdll = ctypes.windll.ntdll
        result = ntdll.NtResumeProcess(self._handle)
        
        if result == 0:
            self._target_process.state = ProcessState.RUNNING
            return True
        return False
    
    def terminate(self) -> bool:
        if not self._handle:
            return False
        
        kernel32 = ctypes.windll.kernel32
        result = kernel32.TerminateProcess(self._handle, 0)
        
        if result:
            self._target_process.state = ProcessState.TERMINATED
            return True
        return False
    
    def detach(self):
        if self._handle:
            kernel32 = ctypes.windll.kernel32
            kernel32.CloseHandle(self._handle)
            self._handle = None
        
        self._target_process = None
        self._modules.clear()
    
    def start_monitor(self, callback=None):
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(callback,))
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def stop_monitor(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self, callback):
        while self._running:
            if self._target_process:
                if psutil:
                    try:
                        proc = psutil.Process(self._target_process.pid)
                        if not proc.is_running():
                            self._target_process.state = ProcessState.TERMINATED
                            if callback:
                                callback("process_terminated", self._target_process)
                    except psutil.NoSuchProcess:
                        self._target_process.state = ProcessState.NOT_FOUND
                        if callback:
                            callback("process_not_found", self._target_process)
            
            time.sleep(self._refresh_interval)


class ProcessHook:
    def __init__(self, process_handle: int):
        self._handle = process_handle
        self._hooks: Dict[int, bytes] = {}
        self._trampolines: Dict[int, int] = {}
        
    def install_hook(self, address: int, hook_function: bytes) -> bool:
        kernel32 = ctypes.windll.kernel32
        
        original_bytes = (ctypes.c_char * 16)()
        bytes_read = ctypes.c_size_t()
        
        kernel32.ReadProcessMemory(
            self._handle,
            ctypes.c_void_p(address),
            original_bytes,
            16,
            ctypes.byref(bytes_read)
        )
        
        self._hooks[address] = bytes(original_bytes)
        
        trampoline = kernel32.VirtualAllocEx(
            self._handle,
            None,
            4096,
            0x3000,
            0x40
        )
        
        if not trampoline:
            return False
        
        self._trampolines[address] = trampoline
        
        jmp_bytes = b'\xE9' + (hook_function - address - 5).to_bytes(4, 'little', signed=True)
        
        bytes_written = ctypes.c_size_t()
        kernel32.WriteProcessMemory(
            self._handle,
            ctypes.c_void_p(address),
            jmp_bytes,
            5,
            ctypes.byref(bytes_written)
        )
        
        return True
    
    def remove_hook(self, address: int) -> bool:
        if address not in self._hooks:
            return False
        
        kernel32 = ctypes.windll.kernel32
        
        original = self._hooks[address]
        bytes_written = ctypes.c_size_t()
        
        kernel32.WriteProcessMemory(
            self._handle,
            ctypes.c_void_p(address),
            original,
            len(original),
            ctypes.byref(bytes_written)
        )
        
        if address in self._trampolines:
            kernel32.VirtualFreeEx(
                self._handle,
                ctypes.c_void_p(self._trampolines[address]),
                0,
                0x8000
            )
            del self._trampolines[address]
        
        del self._hooks[address]
        return True
    
    def remove_all_hooks(self):
        for address in list(self._hooks.keys()):
            self.remove_hook(address)


class ProcessInjector:
    def __init__(self, process_handle: int):
        self._handle = process_handle
        self._injected_dlls: List[str] = []
        
    def inject_dll(self, dll_path: str) -> bool:
        if not os.path.exists(dll_path):
            return False
        
        kernel32 = ctypes.windll.kernel32
        
        dll_path_bytes = dll_path.encode('utf-8') + b'\x00'
        
        remote_memory = kernel32.VirtualAllocEx(
            self._handle,
            None,
            len(dll_path_bytes),
            0x3000,
            0x04
        )
        
        if not remote_memory:
            return False
        
        bytes_written = ctypes.c_size_t()
        kernel32.WriteProcessMemory(
            self._handle,
            ctypes.c_void_p(remote_memory),
            dll_path_bytes,
            len(dll_path_bytes),
            ctypes.byref(bytes_written)
        )
        
        load_library = kernel32.GetProcAddress(
            kernel32.GetModuleHandleA(b"kernel32.dll"),
            b"LoadLibraryA"
        )
        
        thread_handle = kernel32.CreateRemoteThread(
            self._handle,
            None,
            0,
            load_library,
            remote_memory,
            0,
            None
        )
        
        if thread_handle:
            kernel32.WaitForSingleObject(thread_handle, 0xFFFFFFFF)
            kernel32.CloseHandle(thread_handle)
            self._injected_dlls.append(dll_path)
            return True
        
        return False
    
    def inject_shellcode(self, shellcode: bytes) -> bool:
        kernel32 = ctypes.windll.kernel32
        
        remote_memory = kernel32.VirtualAllocEx(
            self._handle,
            None,
            len(shellcode),
            0x3000,
            0x40
        )
        
        if not remote_memory:
            return False
        
        bytes_written = ctypes.c_size_t()
        kernel32.WriteProcessMemory(
            self._handle,
            ctypes.c_void_p(remote_memory),
            shellcode,
            len(shellcode),
            ctypes.byref(bytes_written)
        )
        
        thread_handle = kernel32.CreateRemoteThread(
            self._handle,
            None,
            0,
            remote_memory,
            None,
            0,
            None
        )
        
        if thread_handle:
            kernel32.CloseHandle(thread_handle)
            return True
        
        return False
