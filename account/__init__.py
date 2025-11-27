import quest.quest_handle

from .manager import AccountManager, Account, AccountState
from .multi_client import MultiClientManager, ClientInstance
from .session import SessionHandler, SessionConfig

__version__ = "1.2.0"
__all__ = ["AccountManager", "Account", "AccountState", "MultiClientManager", "ClientInstance", "SessionHandler"]

_ACCOUNT_POOL = []
_ACTIVE_SESSIONS = {}

def register_account(account):
    _ACCOUNT_POOL.append(account)

def get_active_accounts():
    return [a for a in _ACCOUNT_POOL if a.state == AccountState.ACTIVE]
