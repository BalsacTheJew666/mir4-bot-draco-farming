import ctypes
import hashlib
import os
import platform
import random
import string
import subprocess
import uuid
from typing import Optional, Dict, List
from dataclasses import dataclass

try:
    import wmi
except ImportError:
    wmi = None

try:
    import winreg
except ImportError:
    winreg = None


@dataclass
class HardwareInfo:
    cpu_id: str
    motherboard_serial: str
    disk_serial: str
    mac_address: str
    bios_serial: str
    gpu_id: str
    ram_serial: str


class HWIDSpoofer:
    def __init__(self):
        self._original_hwid: Optional[HardwareInfo] = None
        self._spoofed_hwid: Optional[HardwareInfo] = None
        self._active = False
        self._registry_keys_modified: List[str] = []
        
    def get_current_hwid(self) -> HardwareInfo:
        return HardwareInfo(
            cpu_id=self._get_cpu_id(),
            motherboard_serial=self._get_motherboard_serial(),
            disk_serial=self._get_disk_serial(),
            mac_address=self._get_mac_address(),
            bios_serial=self._get_bios_serial(),
            gpu_id=self._get_gpu_id(),
            ram_serial=self._get_ram_serial()
        )
    
    def _get_cpu_id(self) -> str:
        try:
            if wmi:
                c = wmi.WMI()
                for cpu in c.Win32_Processor():
                    return cpu.ProcessorId.strip()
        except:
            pass
        
        result = subprocess.run(
            ['wmic', 'cpu', 'get', 'processorid'],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            return lines[1].strip()
        return ""
    
    def _get_motherboard_serial(self) -> str:
        try:
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'serialnumber'],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
        except:
            pass
        return ""
    
    def _get_disk_serial(self) -> str:
        try:
            result = subprocess.run(
                ['wmic', 'diskdrive', 'get', 'serialnumber'],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
        except:
            pass
        return ""
    
    def _get_mac_address(self) -> str:
        try:
            mac = uuid.getnode()
            return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        except:
            return ""
    
    def _get_bios_serial(self) -> str:
        try:
            result = subprocess.run(
                ['wmic', 'bios', 'get', 'serialnumber'],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
        except:
            pass
        return ""
    
    def _get_gpu_id(self) -> str:
        try:
            if wmi:
                c = wmi.WMI()
                for gpu in c.Win32_VideoController():
                    return gpu.PNPDeviceID
        except:
            pass
        return ""
    
    def _get_ram_serial(self) -> str:
        try:
            result = subprocess.run(
                ['wmic', 'memorychip', 'get', 'serialnumber'],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
        except:
            pass
        return ""
    
    def generate_random_hwid(self) -> HardwareInfo:
        return HardwareInfo(
            cpu_id=self._generate_random_string(16, hex_only=True),
            motherboard_serial=self._generate_random_string(20),
            disk_serial=self._generate_random_string(20),
            mac_address=self._generate_random_mac(),
            bios_serial=self._generate_random_string(22),
            gpu_id=f"PCI\\VEN_{random.randint(1000,9999)}&DEV_{random.randint(1000,9999)}",
            ram_serial=self._generate_random_string(16)
        )
    
    def _generate_random_string(self, length: int, hex_only: bool = False) -> str:
        if hex_only:
            return ''.join(random.choices('0123456789ABCDEF', k=length))
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    def _generate_random_mac(self) -> str:
        return ':'.join('%02X' % random.randint(0, 255) for _ in range(6))
    
    def spoof(self, custom_hwid: Optional[HardwareInfo] = None) -> bool:
        self._original_hwid = self.get_current_hwid()
        self._spoofed_hwid = custom_hwid or self.generate_random_hwid()
        
        try:
            self._spoof_registry()
            self._spoof_wmi()
            self._active = True
            return True
        except Exception:
            return False
    
    def _spoof_registry(self):
        if not winreg:
            return
        
        keys_to_modify = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", "MachineGuid"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\IDConfigDB\Hardware Profiles\0001", "HwProfileGuid"),
        ]
        
        for hkey, subkey, value_name in keys_to_modify:
            try:
                key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
                original_value, _ = winreg.QueryValueEx(key, value_name)
                winreg.CloseKey(key)
                self._registry_keys_modified.append((hkey, subkey, value_name, original_value))
            except:
                continue
    
    def _spoof_wmi(self):
        pass
    
    def restore(self) -> bool:
        if not self._active:
            return True
        
        if winreg:
            for hkey, subkey, value_name, original_value in self._registry_keys_modified:
                try:
                    key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_WRITE)
                    winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, original_value)
                    winreg.CloseKey(key)
                except:
                    continue
        
        self._registry_keys_modified.clear()
        self._active = False
        return True


class MachineIdentifier:
    def __init__(self):
        self._cache: Dict[str, str] = {}
        
    def get_machine_id(self) -> str:
        if 'machine_id' in self._cache:
            return self._cache['machine_id']
        
        components = [
            platform.node(),
            platform.machine(),
            platform.processor(),
            str(uuid.getnode()),
        ]
        
        combined = '|'.join(components)
        machine_id = hashlib.sha256(combined.encode()).hexdigest()
        
        self._cache['machine_id'] = machine_id
        return machine_id
    
    def get_hardware_hash(self) -> str:
        spoofer = HWIDSpoofer()
        hwid = spoofer.get_current_hwid()
        
        components = [
            hwid.cpu_id,
            hwid.motherboard_serial,
            hwid.disk_serial,
            hwid.mac_address,
        ]
        
        combined = '|'.join(components)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def verify_machine(self, expected_hash: str) -> bool:
        current_hash = self.get_hardware_hash()
        return current_hash == expected_hash


class HardwareFingerprint:
    def __init__(self):
        self._fingerprint_data: Dict[str, str] = {}
        
    def collect(self) -> Dict[str, str]:
        self._fingerprint_data = {
            'os': platform.system(),
            'os_version': platform.version(),
            'os_release': platform.release(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'hostname': platform.node(),
            'python_version': platform.python_version(),
        }
        
        spoofer = HWIDSpoofer()
        hwid = spoofer.get_current_hwid()
        
        self._fingerprint_data.update({
            'cpu_id': hwid.cpu_id,
            'motherboard': hwid.motherboard_serial,
            'disk': hwid.disk_serial,
            'mac': hwid.mac_address,
            'bios': hwid.bios_serial,
            'gpu': hwid.gpu_id,
        })
        
        return self._fingerprint_data
    
    def generate_hash(self) -> str:
        if not self._fingerprint_data:
            self.collect()
        
        sorted_data = sorted(self._fingerprint_data.items())
        combined = '|'.join(f"{k}:{v}" for k, v in sorted_data)
        return hashlib.sha512(combined.encode()).hexdigest()
    
    def export(self, file_path: str):
        import json
        with open(file_path, 'w') as f:
            json.dump(self._fingerprint_data, f, indent=2)
    
    def compare(self, other_fingerprint: Dict[str, str]) -> float:
        if not self._fingerprint_data:
            self.collect()
        
        matches = 0
        total = len(self._fingerprint_data)
        
        for key, value in self._fingerprint_data.items():
            if key in other_fingerprint and other_fingerprint[key] == value:
                matches += 1
        
        return matches / total if total > 0 else 0.0
