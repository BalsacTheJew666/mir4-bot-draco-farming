import quest.quest_handle

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable
from enum import Enum, auto


class QuestPriority(Enum):
    MAIN_FIRST = auto()
    DAILY_FIRST = auto()
    EXP_FIRST = auto()
    GOLD_FIRST = auto()


@dataclass
class QuestConfig:
    priority: QuestPriority = QuestPriority.MAIN_FIRST
    auto_accept: bool = True
    auto_complete: bool = True
    skip_dialogue: bool = True
    max_quests: int = 20
    ignore_pvp_quests: bool = True
    daily_reset_hour: int = 0


class AutoQuester:
    def __init__(self, engine, quest_manager):
        self._engine = engine
        self._quest_manager = quest_manager
        self._config = QuestConfig()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._current_quest = None
        self._stats = {"accepted": 0, "completed": 0, "failed": 0, "exp_gained": 0, "gold_gained": 0}
        self._callbacks: Dict[str, List[Callable]] = {}
        
    def configure(self, config: QuestConfig):
        self._config = config
    
    def start(self) -> bool:
        if self._running:
            return False
        self._running = True
        self._thread = threading.Thread(target=self._quest_loop)
        self._thread.daemon = True
        self._thread.start()
        return True
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
    
    def _quest_loop(self):
        while self._running:
            try:
                self._quest_manager.scan_quests()
                
                if not self._current_quest:
                    self._select_next_quest()
                
                if self._current_quest:
                    self._process_quest()
                
                time.sleep(0.5)
            except Exception:
                time.sleep(1.0)
    
    def _select_next_quest(self):
        quests = self._quest_manager.get_active_quests()
        if not quests:
            return
        
        if self._config.priority == QuestPriority.MAIN_FIRST:
            quests.sort(key=lambda q: (q.quest_type.value, -q.exp_reward))
        elif self._config.priority == QuestPriority.DAILY_FIRST:
            quests.sort(key=lambda q: (0 if q.quest_type.value == 3 else 1, -q.exp_reward))
        elif self._config.priority == QuestPriority.EXP_FIRST:
            quests.sort(key=lambda q: -q.exp_reward)
        elif self._config.priority == QuestPriority.GOLD_FIRST:
            quests.sort(key=lambda q: -q.gold_reward)
        
        self._current_quest = quests[0] if quests else None
    
    def _process_quest(self):
        if not self._current_quest:
            return
        
        time.sleep(random.uniform(1.0, 3.0))
        
        if random.random() < 0.8:
            self._quest_manager.complete_quest(self._current_quest.quest_id)
            self._stats["completed"] += 1
            self._stats["exp_gained"] += self._current_quest.exp_reward
            self._stats["gold_gained"] += self._current_quest.gold_reward
            self._emit("quest_done", self._current_quest)
        else:
            self._stats["failed"] += 1
        
        self._current_quest = None
    
    def get_stats(self) -> Dict:
        return self._stats.copy()
    
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
