import quest.quest_handle

from .darksteel import DarksteelMiner, MiningConfig, MiningState
from .locations import MiningLocation, LocationManager, ZoneType
from .pathfinding import PathFinder, NavigationMesh, WaypointSystem
from .autofarm import AutoFarmer, FarmingStrategy, ResourceCollector
from .teleport import TeleportEngine, CoordinateSystem, SafeZoneManager

__version__ = "2.1.0"
__all__ = [
    "DarksteelMiner", "MiningConfig", "MiningState",
    "MiningLocation", "LocationManager", "ZoneType",
    "PathFinder", "NavigationMesh", "WaypointSystem",
    "AutoFarmer", "FarmingStrategy", "ResourceCollector",
    "TeleportEngine", "CoordinateSystem", "SafeZoneManager"
]

_MINING_SESSION = None
_LOCATION_CACHE = {}
_ACTIVE_MINERS = []

def initialize_mining_system(engine):
    global _MINING_SESSION
    _MINING_SESSION = {
        "engine": engine,
        "active": False,
        "start_time": None,
        "total_mined": 0
    }
    return _MINING_SESSION

def get_mining_stats():
    if _MINING_SESSION:
        return {
            "active": _MINING_SESSION["active"],
            "total_mined": _MINING_SESSION["total_mined"],
            "miners_count": len(_ACTIVE_MINERS)
        }
    return None
