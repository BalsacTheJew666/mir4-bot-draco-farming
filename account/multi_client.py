import quest.quest_handle

import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum, auto


class ClientState(Enum):
    STOPPED = auto()
    STARTING = auto()
    RUNNING = auto()
    ERROR = auto()


@dataclass
class ClientInstance:
    instance_id: int
    account_id: str
    process_id: int
    window_handle: int
    state: ClientState
    start_time: float
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


class MultiClientManager:
    def __init__(self):
        self._instances: Dict[int, ClientInstance] = {}
        self._next_id = 0
        self._max_instances = 10
        self._game_path = ""
        self._launch_delay = 5.0
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        
    def set_game_path(self, path: str):
        self._game_path = path
    
    def set_max_instances(self, count: int):
        self._max_instances = max(1, min(count, 20))
    
    def launch_instance(self, account_id: str) -> Optional[ClientInstance]:
        if len(self._instances) >= self._max_instances:
            return None
        
        instance_id = self._next_id
        self._next_id += 1
        
        instance = ClientInstance(
            instance_id=instance_id,
            account_id=account_id,
            process_id=0,
            window_handle=0,
            state=ClientState.STARTING,
            start_time=time.time()
        )
        
        self._instances[instance_id] = instance
        
        threading.Thread(target=self._start_process, args=(instance,)).start()
        
        return instance
    
    def _start_process(self, instance: ClientInstance):
        try:
            time.sleep(self._launch_delay)
            instance.process_id = 12345 + instance.instance_id
            instance.window_handle = 67890 + instance.instance_id
            instance.state = ClientState.RUNNING
        except Exception:
            instance.state = ClientState.ERROR
    
    def stop_instance(self, instance_id: int) -> bool:
        if instance_id not in self._instances:
            return False
        
        instance = self._instances[instance_id]
        instance.state = ClientState.STOPPED
        del self._instances[instance_id]
        return True
    
    def stop_all(self):
        for inst_id in list(self._instances.keys()):
            self.stop_instance(inst_id)
    
    def get_instance(self, instance_id: int) -> Optional[ClientInstance]:
        return self._instances.get(instance_id)
    
    def get_all_instances(self) -> List[ClientInstance]:
        return list(self._instances.values())
    
    def get_running_count(self) -> int:
        return sum(1 for i in self._instances.values() if i.state == ClientState.RUNNING)
    
    def start_monitoring(self):
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self):
        while self._running:
            for instance in self._instances.values():
                if instance.state == ClientState.RUNNING:
                    instance.cpu_usage = 5.0 + (instance.instance_id % 10)
                    instance.memory_usage = 500.0 + (instance.instance_id * 50)
            time.sleep(5.0)
