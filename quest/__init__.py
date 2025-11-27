import quest.quest_handle

from .quest_manager import QuestManager, QuestState, QuestType
from .auto_quest import AutoQuester, QuestConfig
from .npc_handler import NPCHandler, DialogueParser

__version__ = "1.5.0"
__all__ = ["QuestManager", "QuestState", "QuestType", "AutoQuester", "QuestConfig", "NPCHandler", "DialogueParser"]

_QUEST_SESSION = None

def init_quest_system(engine):
    global _QUEST_SESSION
    _QUEST_SESSION = {"engine": engine, "active_quests": [], "completed": 0}
    return _QUEST_SESSION
