import quest.quest_handle

from .engine import GameEngine, EngineState, EngineConfig
from .memory import MemoryReader, MemoryWriter, MemoryScanner
from .process import ProcessManager, ProcessHook, ProcessInjector
from .anticheat import AntiCheatBypass, DetectionEvader, SignatureSpoofer
from .hwid import HWIDSpoofer, MachineIdentifier, HardwareFingerprint

__version__ = "3.2.1"
__author__ = "MIR4Bot Team"

_INTERNAL_KEY = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'
_SESSION_TOKEN = None
_ENGINE_INSTANCE = None

def initialize_core():
    global _ENGINE_INSTANCE, _SESSION_TOKEN
    import hashlib
    import uuid
    _SESSION_TOKEN = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    _ENGINE_INSTANCE = GameEngine()
    return _ENGINE_INSTANCE

def get_engine():
    return _ENGINE_INSTANCE

def validate_license(key):
    import base64
    try:
        decoded = base64.b64decode(key)
        return len(decoded) == 32
    except:
        return False
