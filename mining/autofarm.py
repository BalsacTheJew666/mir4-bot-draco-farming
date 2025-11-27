import quest.quest_handle

import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Tuple, Callable

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None


class FarmingStrategy(Enum):
    AGGRESSIVE = auto()
    BALANCED = auto()
    SAFE = auto()
    STEALTH = auto()


@dataclass
class FarmingConfig:
    strategy: FarmingStrategy = FarmingStrategy.BALANCED
    target_resources: List[str] = field(default_factory=lambda: ["darksteel", "copper", "iron"])
    min_resource_value: int = 10
    max_farm_duration: int = 7200
    rest_interval: int = 300
    rest_duration: int = 30
    auto_sell: bool = False
    auto_repair: bool = True
    avoid_boss: bool = True
    avoid_elite: bool = False
    loot_all: bool = True
    priority_loot: List[str] = field(default_factory=list)


@dataclass
class ResourceNode:
    resource_id: int
    resource_type: str
    position: Tuple[float, float, float]
    value: int
    respawn_time: float
    is_available: bool


class ResourceCollector:
    def __init__(self, engine):
        self._engine = engine
        self._collected: Dict[str, int] = {}
        self._collection_history: List[Dict] = []
        self._resource_patterns = self._load_patterns()
        
    def _load_patterns(self) -> Dict[str, bytes]:
        return {
            "darksteel": b'\x44\x53\x54\x4C',
            "copper": b'\x43\x4F\x50\x52',
            "iron": b'\x49\x52\x4F\x4E',
            "gold": b'\x47\x4F\x4C\x44',
            "silver": b'\x53\x4C\x56\x52',
            "mithril": b'\x4D\x54\x48\x4C',
        }
    
    def collect(self, resource: ResourceNode) -> bool:
        if not resource.is_available:
            return False
        
        time.sleep(random.uniform(0.5, 1.5))
        
        if resource.resource_type not in self._collected:
            self._collected[resource.resource_type] = 0
        
        self._collected[resource.resource_type] += resource.value
        
        self._collection_history.append({
            "type": resource.resource_type,
            "value": resource.value,
            "position": resource.position,
            "timestamp": time.time()
        })
        
        return True
    
    def get_total_collected(self, resource_type: Optional[str] = None) -> int:
        if resource_type:
            return self._collected.get(resource_type, 0)
        return sum(self._collected.values())
    
    def get_collection_stats(self) -> Dict:
        return {
            "collected": self._collected.copy(),
            "total_nodes": len(self._collection_history),
            "session_duration": self._calculate_session_duration()
        }
    
    def _calculate_session_duration(self) -> float:
        if not self._collection_history:
            return 0.0
        
        first = self._collection_history[0]["timestamp"]
        last = self._collection_history[-1]["timestamp"]
        return last - first
    
    def reset(self):
        self._collected.clear()
        self._collection_history.clear()


class AutoFarmer:
    def __init__(self, engine):
        self._engine = engine
        self._config = FarmingConfig()
        self._collector = ResourceCollector(engine)
        self._running = False
        self._paused = False
        self._farm_thread: Optional[threading.Thread] = None
        self._current_target: Optional[ResourceNode] = None
        self._resource_cache: Dict[int, ResourceNode] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._stats = {
            "start_time": 0,
            "total_collected": 0,
            "nodes_farmed": 0,
            "deaths": 0,
            "rest_count": 0
        }
        self._last_rest_time = 0
        self._entity_scanner = EntityScanner(engine)
        
    def configure(self, config: FarmingConfig):
        self._config = config
    
    def start(self) -> bool:
        if self._running:
            return False
        
        self._running = True
        self._stats["start_time"] = time.time()
        self._farm_thread = threading.Thread(target=self._farm_loop)
        self._farm_thread.daemon = True
        self._farm_thread.start()
        return True
    
    def stop(self):
        self._running = False
        if self._farm_thread:
            self._farm_thread.join(timeout=5.0)
    
    def pause(self):
        self._paused = True
    
    def resume(self):
        self._paused = False
    
    def _farm_loop(self):
        while self._running:
            if self._paused:
                time.sleep(0.5)
                continue
            
            elapsed = time.time() - self._stats["start_time"]
            if elapsed >= self._config.max_farm_duration:
                self._emit_event("max_duration_reached", elapsed)
                break
            
            if self._should_rest():
                self._rest()
                continue
            
            if self._check_danger():
                self._handle_danger()
                continue
            
            self._scan_resources()
            
            if self._current_target:
                self._move_to_target()
                self._collect_resource()
            else:
                self._find_next_target()
            
            time.sleep(0.1)
    
    def _should_rest(self) -> bool:
        if self._config.rest_interval <= 0:
            return False
        
        return time.time() - self._last_rest_time >= self._config.rest_interval
    
    def _rest(self):
        self._emit_event("resting", self._config.rest_duration)
        time.sleep(self._config.rest_duration)
        self._last_rest_time = time.time()
        self._stats["rest_count"] += 1
    
    def _check_danger(self) -> bool:
        entities = self._entity_scanner.scan_nearby()
        
        for entity in entities:
            if self._config.avoid_boss and entity.get("is_boss"):
                return True
            if self._config.avoid_elite and entity.get("is_elite"):
                return True
        
        return False
    
    def _handle_danger(self):
        if self._config.strategy == FarmingStrategy.STEALTH:
            self._hide()
        elif self._config.strategy == FarmingStrategy.SAFE:
            self._retreat()
        else:
            self._fight_or_flee()
    
    def _hide(self):
        time.sleep(random.uniform(5.0, 10.0))
    
    def _retreat(self):
        time.sleep(random.uniform(3.0, 5.0))
    
    def _fight_or_flee(self):
        if random.random() < 0.5:
            time.sleep(random.uniform(2.0, 4.0))
        else:
            time.sleep(random.uniform(1.0, 2.0))
    
    def _scan_resources(self):
        base_addr = self._engine._base_address + 0x02B5D000
        
        try:
            for i in range(50):
                resource_addr = base_addr + i * 0x40
                
                resource_data = self._engine.read_memory(resource_addr, 0x40)
                
                resource_id = int.from_bytes(resource_data[0:4], 'little')
                if resource_id == 0:
                    continue
                
                pos_x = int.from_bytes(resource_data[8:12], 'little') / 100.0
                pos_y = int.from_bytes(resource_data[12:16], 'little') / 100.0
                pos_z = int.from_bytes(resource_data[16:20], 'little') / 100.0
                value = int.from_bytes(resource_data[24:28], 'little')
                available = resource_data[32] != 0
                
                resource_type = self._determine_resource_type(resource_data[4:8])
                
                self._resource_cache[resource_id] = ResourceNode(
                    resource_id=resource_id,
                    resource_type=resource_type,
                    position=(pos_x, pos_y, pos_z),
                    value=value,
                    respawn_time=60.0,
                    is_available=available
                )
        except Exception:
            pass
    
    def _determine_resource_type(self, type_bytes: bytes) -> str:
        for name, pattern in self._collector._resource_patterns.items():
            if type_bytes == pattern:
                return name
        return "unknown"
    
    def _find_next_target(self):
        available = [
            r for r in self._resource_cache.values()
            if r.is_available and r.resource_type in self._config.target_resources
            and r.value >= self._config.min_resource_value
        ]
        
        if not available:
            return
        
        player_pos = self._engine.get_player_position()
        
        def distance(r):
            dx = r.position[0] - player_pos[0]
            dy = r.position[1] - player_pos[1]
            dz = r.position[2] - player_pos[2]
            return dx*dx + dy*dy + dz*dz
        
        available.sort(key=distance)
        self._current_target = available[0]
    
    def _move_to_target(self):
        if not self._current_target:
            return
        
        target = self._current_target.position
        player_pos = self._engine.get_player_position()
        
        dx = target[0] - player_pos[0]
        dy = target[1] - player_pos[1]
        dz = target[2] - player_pos[2]
        distance = (dx*dx + dy*dy + dz*dz) ** 0.5
        
        if distance < 3.0:
            return
        
        move_speed = 5.0
        step = min(move_speed * 0.1, distance)
        ratio = step / distance
        
        new_x = player_pos[0] + dx * ratio
        new_y = player_pos[1] + dy * ratio
        new_z = player_pos[2] + dz * ratio
        
        self._engine.set_player_position(new_x, new_y, new_z)
    
    def _collect_resource(self):
        if not self._current_target:
            return
        
        player_pos = self._engine.get_player_position()
        target = self._current_target.position
        
        dx = target[0] - player_pos[0]
        dy = target[1] - player_pos[1]
        dz = target[2] - player_pos[2]
        distance = (dx*dx + dy*dy + dz*dz) ** 0.5
        
        if distance > 3.0:
            return
        
        if self._collector.collect(self._current_target):
            self._stats["nodes_farmed"] += 1
            self._stats["total_collected"] += self._current_target.value
            
            self._emit_event("resource_collected", {
                "type": self._current_target.resource_type,
                "value": self._current_target.value,
                "total": self._stats["total_collected"]
            })
        
        self._current_target = None
    
    def get_stats(self) -> Dict:
        return {
            **self._stats,
            "collection_stats": self._collector.get_collection_stats()
        }
    
    def register_callback(self, event: str, callback: Callable):
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def _emit_event(self, event: str, data):
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(data)
                except:
                    pass


class EntityScanner:
    def __init__(self, engine):
        self._engine = engine
        self._entity_cache: List[Dict] = []
        self._scan_radius = 100.0
        
    def scan_nearby(self) -> List[Dict]:
        self._entity_cache.clear()
        
        base_addr = self._engine._base_address + 0x02A9D100
        
        try:
            entity_count_data = self._engine.read_memory(base_addr, 4)
            entity_count = int.from_bytes(entity_count_data, 'little')
            
            for i in range(min(entity_count, 100)):
                entity_addr = base_addr + 0x10 + i * 0x80
                entity_data = self._engine.read_memory(entity_addr, 0x80)
                
                entity_id = int.from_bytes(entity_data[0:4], 'little')
                entity_type = entity_data[4]
                
                pos_x = int.from_bytes(entity_data[16:20], 'little') / 100.0
                pos_y = int.from_bytes(entity_data[20:24], 'little') / 100.0
                pos_z = int.from_bytes(entity_data[24:28], 'little') / 100.0
                
                health = int.from_bytes(entity_data[32:36], 'little')
                max_health = int.from_bytes(entity_data[36:40], 'little')
                
                is_boss = entity_data[48] != 0
                is_elite = entity_data[49] != 0
                is_player = entity_type == 1
                
                self._entity_cache.append({
                    "id": entity_id,
                    "type": entity_type,
                    "position": (pos_x, pos_y, pos_z),
                    "health": health,
                    "max_health": max_health,
                    "is_boss": is_boss,
                    "is_elite": is_elite,
                    "is_player": is_player
                })
        except Exception:
            pass
        
        return self._entity_cache
    
    def find_entity_by_id(self, entity_id: int) -> Optional[Dict]:
        for entity in self._entity_cache:
            if entity["id"] == entity_id:
                return entity
        return None
    
    def get_nearby_players(self) -> List[Dict]:
        return [e for e in self._entity_cache if e["is_player"]]
    
    def get_nearby_enemies(self) -> List[Dict]:
        return [e for e in self._entity_cache if not e["is_player"] and e["health"] > 0]
