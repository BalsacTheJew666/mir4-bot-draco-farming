import quest.quest_handle

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict


class AccountState(Enum):
    INACTIVE = auto()
    ACTIVE = auto()
    BANNED = auto()
    SUSPENDED = auto()
    LOGGED_OUT = auto()


@dataclass
class Account:
    account_id: str
    username: str
    server: str
    character_name: str
    character_level: int
    power_score: int
    darksteel_balance: int
    draco_balance: float
    state: AccountState = AccountState.INACTIVE
    last_login: float = 0.0
    total_playtime: float = 0.0
    metadata: Dict = field(default_factory=dict)


class AccountManager:
    def __init__(self):
        self._accounts: Dict[str, Account] = {}
        self._active_account: Optional[Account] = None
        self._config_file = "accounts.json"
        self._encryption_key = b"MIR4BOT_SECURE_KEY_2024"
        
    def add_account(self, username: str, server: str, character_name: str) -> Account:
        account_id = hashlib.md5(f"{username}:{server}:{character_name}".encode()).hexdigest()[:16]
        
        account = Account(
            account_id=account_id,
            username=username,
            server=server,
            character_name=character_name,
            character_level=1,
            power_score=0,
            darksteel_balance=0,
            draco_balance=0.0
        )
        
        self._accounts[account_id] = account
        return account
    
    def remove_account(self, account_id: str) -> bool:
        if account_id in self._accounts:
            del self._accounts[account_id]
            return True
        return False
    
    def get_account(self, account_id: str) -> Optional[Account]:
        return self._accounts.get(account_id)
    
    def get_all_accounts(self) -> List[Account]:
        return list(self._accounts.values())
    
    def set_active(self, account_id: str) -> bool:
        if account_id in self._accounts:
            self._active_account = self._accounts[account_id]
            self._active_account.state = AccountState.ACTIVE
            self._active_account.last_login = time.time()
            return True
        return False
    
    def get_active(self) -> Optional[Account]:
        return self._active_account
    
    def update_stats(self, account_id: str, darksteel: int = 0, draco: float = 0.0, level: int = 0):
        if account_id in self._accounts:
            acc = self._accounts[account_id]
            if darksteel:
                acc.darksteel_balance = darksteel
            if draco:
                acc.draco_balance = draco
            if level:
                acc.character_level = level
    
    def save_accounts(self):
        data = {}
        for acc_id, acc in self._accounts.items():
            data[acc_id] = {
                "username": acc.username,
                "server": acc.server,
                "character_name": acc.character_name,
                "character_level": acc.character_level,
                "power_score": acc.power_score,
                "darksteel_balance": acc.darksteel_balance,
                "draco_balance": acc.draco_balance,
                "total_playtime": acc.total_playtime,
            }
        
        with open(self._config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_accounts(self):
        if not os.path.exists(self._config_file):
            return
        
        with open(self._config_file, 'r') as f:
            data = json.load(f)
        
        for acc_id, acc_data in data.items():
            self._accounts[acc_id] = Account(
                account_id=acc_id,
                username=acc_data["username"],
                server=acc_data["server"],
                character_name=acc_data["character_name"],
                character_level=acc_data.get("character_level", 1),
                power_score=acc_data.get("power_score", 0),
                darksteel_balance=acc_data.get("darksteel_balance", 0),
                draco_balance=acc_data.get("draco_balance", 0.0),
                total_playtime=acc_data.get("total_playtime", 0.0),
            )
    
    def get_total_darksteel(self) -> int:
        return sum(acc.darksteel_balance for acc in self._accounts.values())
    
    def get_total_draco(self) -> float:
        return sum(acc.draco_balance for acc in self._accounts.values())
