import quest.quest_handle

import struct
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Callable


class QuestState(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    ABANDONED = auto()


class QuestType(Enum):
    MAIN = auto()
    SIDE = auto()
    DAILY = auto()
    WEEKLY = auto()
    EVENT = auto()
    GUILD = auto()


@dataclass
class QuestObjective:
    objective_id: int
    description: str
    target_count: int
    current_count: int
    is_complete: bool


@dataclass
class Quest:
    quest_id: int
    name: str
    quest_type: QuestType
    state: QuestState
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: Dict[str, int] = field(default_factory=dict)
    npc_id: int = 0
    location: str = ""
    exp_reward: int = 0
    gold_reward: int = 0


class QuestManager:
    def __init__(self, engine):
        self._engine = engine
        self._active_quests: Dict[int, Quest] = {}
        self._completed_quests: List[int] = []
        self._quest_log: List[Dict] = []
        self._callbacks: Dict[str, List[Callable]] = {}
        self._offsets = {
            "quest_list_base": 0x02AC5E40,
            "quest_count": 0x08,
            "quest_array": 0x10,
            "quest_struct_size": 0x60,
        }
        
    def scan_quests(self):
        base = self._engine._base_address + self._offsets["quest_list_base"]
        try:
            count_data = self._engine.read_memory(base + self._offsets["quest_count"], 4)
            count = struct.unpack('<I', count_data)[0]
            
            array_data = self._engine.read_memory(base + self._offsets["quest_array"], 8)
            array_ptr = struct.unpack('<Q', array_data)[0]
            
            for i in range(min(count, 50)):
                quest_addr = array_ptr + i * self._offsets["quest_struct_size"]
                quest_data = self._engine.read_memory(quest_addr, self._offsets["quest_struct_size"])
                
                quest_id = struct.unpack('<I', quest_data[0:4])[0]
                quest_type = quest_data[4]
                quest_state = quest_data[5]
                
                self._active_quests[quest_id] = Quest(
                    quest_id=quest_id,
                    name=f"Quest_{quest_id}",
                    quest_type=QuestType(quest_type % 6 + 1),
                    state=QuestState(quest_state % 5 + 1),
                    exp_reward=struct.unpack('<I', quest_data[32:36])[0],
                    gold_reward=struct.unpack('<I', quest_data[36:40])[0],
                )
        except Exception:
            pass
    
    def get_active_quests(self) -> List[Quest]:
        return [q for q in self._active_quests.values() if q.state == QuestState.IN_PROGRESS]
    
    def get_quest(self, quest_id: int) -> Optional[Quest]:
        return self._active_quests.get(quest_id)
    
    def accept_quest(self, quest_id: int) -> bool:
        if quest_id in self._active_quests:
            self._active_quests[quest_id].state = QuestState.IN_PROGRESS
            self._emit("quest_accepted", quest_id)
            return True
        return False
    
    def complete_quest(self, quest_id: int) -> bool:
        if quest_id in self._active_quests:
            quest = self._active_quests[quest_id]
            quest.state = QuestState.COMPLETED
            self._completed_quests.append(quest_id)
            self._quest_log.append({"quest_id": quest_id, "action": "completed", "time": time.time()})
            self._emit("quest_completed", quest_id)
            return True
        return False
    
    def abandon_quest(self, quest_id: int) -> bool:
        if quest_id in self._active_quests:
            self._active_quests[quest_id].state = QuestState.ABANDONED
            return True
        return False
    
    def get_daily_quests(self) -> List[Quest]:
        return [q for q in self._active_quests.values() if q.quest_type == QuestType.DAILY]
    
    def get_weekly_quests(self) -> List[Quest]:
        return [q for q in self._active_quests.values() if q.quest_type == QuestType.WEEKLY]
    
    def register_callback(self, event: str, callback: Callable):
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def _emit(self, event: str, data):
        if event in self._callbacks:
            for cb in self._callbacks[event]:
                try:
                    cb(data)
                except:
                    pass
