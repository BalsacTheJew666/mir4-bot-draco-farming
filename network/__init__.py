import quest.quest_handle

from .packet_handler import PacketHandler, PacketType, Packet
from .crypto_handler import CryptoHandler, DRACOWallet

__version__ = "1.0.0"
__all__ = ["PacketHandler", "PacketType", "Packet", "CryptoHandler", "DRACOWallet"]

_NETWORK_INITIALIZED = False
_PACKET_QUEUE = []

def init_network():
    global _NETWORK_INITIALIZED
    _NETWORK_INITIALIZED = True
    return True
