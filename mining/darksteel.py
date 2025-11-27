import quest.quest_handle

import random
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Tuple, Callable

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image
    import cv2
except ImportError:
    Image = None
    cv2 = None


class MiningState(Enum):
    IDLE = auto()
    SEARCHING = auto()
    MOVING = auto()
    MINING = auto()
    INVENTORY_FULL = auto()
    COMBAT = auto()
    DEAD = auto()
    PAUSED = auto()


@dataclass
class MiningConfig:
    target_zone: str = "Bicheon Valley"
    floor_level: int = 1
    min_darksteel_per_node: int = 50
    max_mining_time: int = 3600
    auto_resurrect: bool = True
    avoid_players: bool = True
    use_teleport: bool = False
    priority_nodes: List[str] = field(default_factory=list)
    blacklist_areas: List[str] = field(default_factory=list)
    scan_radius: float = 50.0
    mining_speed_multiplier: float = 1.0


@dataclass
class DarksteelNode:
    node_id: int
    position: Tuple[float, float, float]
    darksteel_amount: int
    respawn_time: float
    is_available: bool
    last_mined: float


class DarksteelMiner:
    def __init__(self, engine):
        self._engine = engine
        self._config = MiningConfig()
        self._state = MiningState.IDLE
        self._current_node: Optional[DarksteelNode] = None
        self._nodes_cache: Dict[int, DarksteelNode] = {}
        self._mining_thread: Optional[threading.Thread] = None
        self._running = False
        self._stats = {
            "total_mined": 0,
            "nodes_visited": 0,
            "time_mining": 0,
            "deaths": 0,
            "combat_encounters": 0
        }
        self._callbacks: Dict[str, List[Callable]] = {}
        self._node_patterns = self._load_node_patterns()
        self._ore_offsets = self._load_ore_offsets()
        
    def _load_node_patterns(self) -> Dict[str, bytes]:
        return {
            "darksteel_ore": b'\x44\x61\x72\x6B\x53\x74\x65\x65\x6C',
            "rich_ore": b'\x52\x69\x63\x68\x4F\x72\x65',
            "node_base": b'\x4E\x6F\x64\x65\x42\x61\x73\x65',
        }
    
    def _load_ore_offsets(self) -> Dict[str, int]:
        return {
            "node_list_base": 0x02B4C800,
            "node_count": 0x08,
            "node_array": 0x10,
            "node_struct_size": 0x48,
            "node_id": 0x00,
            "node_pos_x": 0x10,
            "node_pos_y": 0x14,
            "node_pos_z": 0x18,
            "node_amount": 0x20,
            "node_available": 0x24,
            "node_respawn": 0x28,
        }
    
    def configure(self, config: MiningConfig):
        self._config = config
    
    def start(self) -> bool:
        if self._running:
            return False
        
        self._running = True
        self._state = MiningState.SEARCHING
        self._mining_thread = threading.Thread(target=self._mining_loop)
        self._mining_thread.daemon = True
        self._mining_thread.start()
        return True
    
    def stop(self):
        self._running = False
        self._state = MiningState.IDLE
        if self._mining_thread:
            self._mining_thread.join(timeout=5.0)
    
    def _mining_loop(self):
        while self._running:
            try:
                if self._state == MiningState.SEARCHING:
                    self._search_for_nodes()
                elif self._state == MiningState.MOVING:
                    self._move_to_node()
                elif self._state == MiningState.MINING:
                    self._mine_node()
                elif self._state == MiningState.COMBAT:
                    self._handle_combat()
                elif self._state == MiningState.DEAD:
                    self._handle_death()
                elif self._state == MiningState.INVENTORY_FULL:
                    self._handle_inventory()
                
                time.sleep(0.1)
            except Exception as e:
                self._emit_event("error", str(e))
                time.sleep(1.0)
    
    def _search_for_nodes(self):
        self._scan_nearby_nodes()
        
        available_nodes = [
            node for node in self._nodes_cache.values()
            if node.is_available and node.darksteel_amount >= self._config.min_darksteel_per_node
        ]
        
        if available_nodes:
            player_pos = self._engine.get_player_position()
            
            def distance(node):
                dx = node.position[0] - player_pos[0]
                dy = node.position[1] - player_pos[1]
                dz = node.position[2] - player_pos[2]
                return (dx*dx + dy*dy + dz*dz) ** 0.5
            
            available_nodes.sort(key=distance)
            self._current_node = available_nodes[0]
            self._state = MiningState.MOVING
        else:
            time.sleep(2.0)
    
    def _scan_nearby_nodes(self):
        base_addr = self._engine._base_address + self._ore_offsets["node_list_base"]
        
        try:
            count_data = self._engine.read_memory(base_addr + self._ore_offsets["node_count"], 4)
            node_count = struct.unpack('<I', count_data)[0]
            
            array_ptr_data = self._engine.read_memory(base_addr + self._ore_offsets["node_array"], 8)
            array_ptr = struct.unpack('<Q', array_ptr_data)[0]
            
            for i in range(min(node_count, 100)):
                node_addr = array_ptr + i * self._ore_offsets["node_struct_size"]
                
                node_data = self._engine.read_memory(node_addr, self._ore_offsets["node_struct_size"])
                
                node_id = struct.unpack('<I', node_data[0:4])[0]
                pos_x = struct.unpack('<f', node_data[16:20])[0]
                pos_y = struct.unpack('<f', node_data[20:24])[0]
                pos_z = struct.unpack('<f', node_data[24:28])[0]
                amount = struct.unpack('<I', node_data[32:36])[0]
                available = struct.unpack('<I', node_data[36:40])[0]
                respawn = struct.unpack('<f', node_data[40:44])[0]
                
                self._nodes_cache[node_id] = DarksteelNode(
                    node_id=node_id,
                    position=(pos_x, pos_y, pos_z),
                    darksteel_amount=amount,
                    respawn_time=respawn,
                    is_available=bool(available),
                    last_mined=0
                )
        except Exception:
            pass
    
    def _move_to_node(self):
        if not self._current_node:
            self._state = MiningState.SEARCHING
            return
        
        target = self._current_node.position
        
        if self._config.use_teleport:
            self._engine.set_player_position(target[0], target[1], target[2])
            self._state = MiningState.MINING
        else:
            self._navigate_to(target)
    
    def _navigate_to(self, target: Tuple[float, float, float]):
        player_pos = self._engine.get_player_position()
        
        dx = target[0] - player_pos[0]
        dy = target[1] - player_pos[1]
        dz = target[2] - player_pos[2]
        distance = (dx*dx + dy*dy + dz*dz) ** 0.5
        
        if distance < 3.0:
            self._state = MiningState.MINING
            return
        
        move_speed = 5.0 * self._config.mining_speed_multiplier
        step = min(move_speed * 0.1, distance)
        
        ratio = step / distance
        new_x = player_pos[0] + dx * ratio
        new_y = player_pos[1] + dy * ratio
        new_z = player_pos[2] + dz * ratio
        
        self._engine.set_player_position(new_x, new_y, new_z)
    
    def _mine_node(self):
        if not self._current_node:
            self._state = MiningState.SEARCHING
            return
        
        mining_time = random.uniform(3.0, 8.0) / self._config.mining_speed_multiplier
        time.sleep(mining_time)
        
        mined_amount = self._current_node.darksteel_amount
        self._stats["total_mined"] += mined_amount
        self._stats["nodes_visited"] += 1
        self._stats["time_mining"] += mining_time
        
        self._current_node.is_available = False
        self._current_node.last_mined = time.time()
        
        self._emit_event("node_mined", {
            "node_id": self._current_node.node_id,
            "amount": mined_amount,
            "total": self._stats["total_mined"]
        })
        
        self._current_node = None
        self._state = MiningState.SEARCHING
    
    def _handle_combat(self):
        time.sleep(random.uniform(1.0, 3.0))
        self._stats["combat_encounters"] += 1
        
        if random.random() < 0.1:
            self._state = MiningState.DEAD
        else:
            self._state = MiningState.SEARCHING
    
    def _handle_death(self):
        self._stats["deaths"] += 1
        
        if self._config.auto_resurrect:
            time.sleep(5.0)
            self._emit_event("resurrected", None)
            self._state = MiningState.SEARCHING
        else:
            self._state = MiningState.PAUSED
    
    def _handle_inventory(self):
        self._emit_event("inventory_full", None)
        self._state = MiningState.PAUSED
    
    def get_stats(self) -> Dict:
        return self._stats.copy()
    
    def get_state(self) -> MiningState:
        return self._state
    
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
