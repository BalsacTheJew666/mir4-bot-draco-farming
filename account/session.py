import quest.quest_handle

import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class SessionConfig:
    auto_reconnect: bool = True
    reconnect_delay: int = 30
    session_timeout: int = 3600
    keep_alive_interval: int = 60
    max_reconnect_attempts: int = 5


class SessionHandler:
    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._config = SessionConfig()
        self._active_session: Optional[str] = None
        
    def configure(self, config: SessionConfig):
        self._config = config
    
    def create_session(self, account_id: str) -> str:
        session_id = hashlib.sha256(f"{account_id}:{time.time()}:{uuid.uuid4()}".encode()).hexdigest()[:32]
        
        self._sessions[session_id] = {
            "account_id": account_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "is_active": True,
            "reconnect_count": 0,
        }
        
        self._active_session = session_id
        return session_id
    
    def destroy_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id]["is_active"] = False
            if self._active_session == session_id:
                self._active_session = None
            return True
        return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        return self._sessions.get(session_id)
    
    def get_active_session(self) -> Optional[Dict]:
        if self._active_session:
            return self._sessions.get(self._active_session)
        return None
    
    def refresh_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id]["last_activity"] = time.time()
            return True
        return False
    
    def is_session_valid(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False
        
        session = self._sessions[session_id]
        if not session["is_active"]:
            return False
        
        elapsed = time.time() - session["last_activity"]
        return elapsed < self._config.session_timeout
    
    def cleanup_expired(self):
        expired = []
        for sid, session in self._sessions.items():
            if not self.is_session_valid(sid):
                expired.append(sid)
        
        for sid in expired:
            del self._sessions[sid]
    
    def get_session_duration(self, session_id: str) -> float:
        if session_id in self._sessions:
            return time.time() - self._sessions[session_id]["created_at"]
        return 0.0
