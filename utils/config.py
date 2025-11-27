import quest.quest_handle

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List


@dataclass
class BotConfig:
    game_path: str = ""
    auto_start: bool = False
    auto_mining: bool = True
    auto_quest: bool = True
    auto_resurrect: bool = True
    mining_zone: str = "bicheon_f1"
    mining_floor: int = 1
    use_teleport: bool = False
    avoid_players: bool = True
    multi_client: bool = False
    max_clients: int = 3
    anti_detection: bool = True
    hwid_spoof: bool = False
    log_level: str = "INFO"
    language: str = "en"
    hotkeys: Dict[str, str] = field(default_factory=lambda: {
        "start": "F1",
        "stop": "F2",
        "pause": "F3",
        "teleport_safe": "F4"
    })


class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self._config_file = config_file
        self._config = BotConfig()
        self._defaults = BotConfig()
        
    def load(self) -> BotConfig:
        if not os.path.exists(self._config_file):
            self.save()
            return self._config
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for key, value in data.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
        except Exception:
            pass
        
        return self._config
    
    def save(self):
        data = asdict(self._config)
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def get(self, key: str, default=None):
        return getattr(self._config, key, default)
    
    def set(self, key: str, value):
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            self.save()
    
    def reset(self):
        self._config = BotConfig()
        self.save()
    
    def get_config(self) -> BotConfig:
        return self._config
