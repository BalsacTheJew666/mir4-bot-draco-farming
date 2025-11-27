import quest.quest_handle

import struct
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple


@dataclass
class NPC:
    npc_id: int
    name: str
    position: Tuple[float, float, float]
    npc_type: str
    has_quest: bool
    dialogue_id: int


@dataclass
class DialogueOption:
    option_id: int
    text: str
    action: str
    next_dialogue: int


class DialogueParser:
    def __init__(self):
        self._dialogue_cache: Dict[int, List[DialogueOption]] = {}
        self._patterns = {
            "accept": ["accept", "yes", "ok", "agree"],
            "decline": ["decline", "no", "refuse"],
            "complete": ["complete", "finish", "done"],
        }
    
    def parse_dialogue(self, dialogue_data: bytes) -> List[DialogueOption]:
        options = []
        offset = 0
        
        while offset < len(dialogue_data) - 8:
            opt_id = struct.unpack('<I', dialogue_data[offset:offset+4])[0]
            if opt_id == 0:
                break
            
            text_len = dialogue_data[offset+4]
            text = dialogue_data[offset+5:offset+5+text_len].decode('utf-8', errors='ignore')
            next_id = struct.unpack('<I', dialogue_data[offset+5+text_len:offset+9+text_len])[0]
            
            action = self._detect_action(text)
            options.append(DialogueOption(opt_id, text, action, next_id))
            offset += 9 + text_len
        
        return options
    
    def _detect_action(self, text: str) -> str:
        text_lower = text.lower()
        for action, keywords in self._patterns.items():
            for kw in keywords:
                if kw in text_lower:
                    return action
        return "unknown"
    
    def find_accept_option(self, options: List[DialogueOption]) -> Optional[DialogueOption]:
        for opt in options:
            if opt.action == "accept":
                return opt
        return options[0] if options else None


class NPCHandler:
    def __init__(self, engine):
        self._engine = engine
        self._npc_cache: Dict[int, NPC] = {}
        self._dialogue_parser = DialogueParser()
        self._interaction_range = 5.0
        self._offsets = {
            "npc_list_base": 0x02AD8C00,
            "npc_count": 0x08,
            "npc_struct_size": 0x50,
        }
    
    def scan_npcs(self):
        base = self._engine._base_address + self._offsets["npc_list_base"]
        try:
            count_data = self._engine.read_memory(base + self._offsets["npc_count"], 4)
            count = struct.unpack('<I', count_data)[0]
            
            for i in range(min(count, 100)):
                npc_addr = base + 0x10 + i * self._offsets["npc_struct_size"]
                npc_data = self._engine.read_memory(npc_addr, self._offsets["npc_struct_size"])
                
                npc_id = struct.unpack('<I', npc_data[0:4])[0]
                if npc_id == 0:
                    continue
                
                pos_x = struct.unpack('<f', npc_data[16:20])[0]
                pos_y = struct.unpack('<f', npc_data[20:24])[0]
                pos_z = struct.unpack('<f', npc_data[24:28])[0]
                has_quest = npc_data[32] != 0
                
                self._npc_cache[npc_id] = NPC(
                    npc_id=npc_id,
                    name=f"NPC_{npc_id}",
                    position=(pos_x, pos_y, pos_z),
                    npc_type="quest" if has_quest else "normal",
                    has_quest=has_quest,
                    dialogue_id=struct.unpack('<I', npc_data[36:40])[0]
                )
        except Exception:
            pass
    
    def get_nearby_npcs(self, radius: float = 50.0) -> List[NPC]:
        player_pos = self._engine.get_player_position()
        nearby = []
        for npc in self._npc_cache.values():
            dx = npc.position[0] - player_pos[0]
            dz = npc.position[2] - player_pos[2]
            if dx*dx + dz*dz <= radius*radius:
                nearby.append(npc)
        return nearby
    
    def get_quest_npcs(self) -> List[NPC]:
        return [npc for npc in self._npc_cache.values() if npc.has_quest]
    
    def interact(self, npc_id: int) -> bool:
        if npc_id not in self._npc_cache:
            return False
        
        npc = self._npc_cache[npc_id]
        player_pos = self._engine.get_player_position()
        
        dx = npc.position[0] - player_pos[0]
        dz = npc.position[2] - player_pos[2]
        dist = (dx*dx + dz*dz) ** 0.5
        
        if dist > self._interaction_range:
            return False
        
        time.sleep(0.5)
        return True
    
    def find_nearest_quest_npc(self) -> Optional[NPC]:
        quest_npcs = self.get_quest_npcs()
        if not quest_npcs:
            return None
        
        player_pos = self._engine.get_player_position()
        def dist(npc):
            dx = npc.position[0] - player_pos[0]
            dz = npc.position[2] - player_pos[2]
            return dx*dx + dz*dz
        
        return min(quest_npcs, key=dist)
