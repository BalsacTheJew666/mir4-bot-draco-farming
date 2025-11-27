import quest.quest_handle

import json
import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Tuple

try:
    import numpy as np
except ImportError:
    np = None


class ZoneType(Enum):
    SAFE = auto()
    PVP = auto()
    DUNGEON = auto()
    BOSS = auto()
    MINING = auto()
    QUEST = auto()


@dataclass
class MiningLocation:
    location_id: str
    name: str
    zone_type: ZoneType
    coordinates: Tuple[float, float, float]
    floor_level: int
    darksteel_density: float
    danger_level: int
    recommended_power: int
    spawn_points: List[Tuple[float, float, float]] = field(default_factory=list)
    ore_positions: List[Tuple[float, float, float]] = field(default_factory=list)
    safe_spots: List[Tuple[float, float, float]] = field(default_factory=list)
    npc_positions: List[Tuple[float, float, float]] = field(default_factory=list)


class LocationManager:
    def __init__(self):
        self._locations: Dict[str, MiningLocation] = {}
        self._current_location: Optional[MiningLocation] = None
        self._location_history: List[str] = []
        self._cache_file = "locations_cache.json"
        self._load_default_locations()
        
    def _load_default_locations(self):
        default_locations = [
            MiningLocation(
                location_id="bicheon_f1",
                name="Bicheon Valley F1",
                zone_type=ZoneType.MINING,
                coordinates=(1250.5, 100.0, 3420.8),
                floor_level=1,
                darksteel_density=0.6,
                danger_level=1,
                recommended_power=10000,
                spawn_points=[
                    (1200.0, 100.0, 3400.0),
                    (1300.0, 100.0, 3450.0),
                ],
                ore_positions=[
                    (1220.0, 100.0, 3410.0),
                    (1280.0, 100.0, 3430.0),
                    (1260.0, 100.0, 3480.0),
                ]
            ),
            MiningLocation(
                location_id="bicheon_f2",
                name="Bicheon Valley F2",
                zone_type=ZoneType.MINING,
                coordinates=(1450.2, 80.0, 3620.5),
                floor_level=2,
                darksteel_density=0.75,
                danger_level=2,
                recommended_power=25000,
                spawn_points=[
                    (1400.0, 80.0, 3600.0),
                    (1500.0, 80.0, 3650.0),
                ],
                ore_positions=[
                    (1420.0, 80.0, 3610.0),
                    (1480.0, 80.0, 3640.0),
                ]
            ),
            MiningLocation(
                location_id="bicheon_f3",
                name="Bicheon Valley F3",
                zone_type=ZoneType.MINING,
                coordinates=(1650.8, 60.0, 3820.3),
                floor_level=3,
                darksteel_density=0.9,
                danger_level=3,
                recommended_power=50000,
                spawn_points=[
                    (1600.0, 60.0, 3800.0),
                ],
                ore_positions=[
                    (1620.0, 60.0, 3810.0),
                    (1680.0, 60.0, 3850.0),
                    (1700.0, 60.0, 3880.0),
                ]
            ),
            MiningLocation(
                location_id="snake_pit_f1",
                name="Snake Pit F1",
                zone_type=ZoneType.MINING,
                coordinates=(2100.0, 120.0, 4500.0),
                floor_level=1,
                darksteel_density=0.7,
                danger_level=2,
                recommended_power=30000,
                spawn_points=[
                    (2050.0, 120.0, 4480.0),
                ],
                ore_positions=[
                    (2080.0, 120.0, 4510.0),
                    (2120.0, 120.0, 4530.0),
                ]
            ),
            MiningLocation(
                location_id="snake_pit_f2",
                name="Snake Pit F2",
                zone_type=ZoneType.MINING,
                coordinates=(2300.0, 100.0, 4700.0),
                floor_level=2,
                darksteel_density=0.85,
                danger_level=3,
                recommended_power=60000,
                spawn_points=[
                    (2250.0, 100.0, 4680.0),
                ],
                ore_positions=[
                    (2280.0, 100.0, 4710.0),
                    (2320.0, 100.0, 4740.0),
                    (2350.0, 100.0, 4760.0),
                ]
            ),
            MiningLocation(
                location_id="snake_pit_f3",
                name="Snake Pit F3",
                zone_type=ZoneType.MINING,
                coordinates=(2500.0, 80.0, 4900.0),
                floor_level=3,
                darksteel_density=1.0,
                danger_level=4,
                recommended_power=100000,
                spawn_points=[
                    (2450.0, 80.0, 4880.0),
                ],
                ore_positions=[
                    (2480.0, 80.0, 4910.0),
                    (2520.0, 80.0, 4940.0),
                ]
            ),
            MiningLocation(
                location_id="secret_peak",
                name="Secret Peak",
                zone_type=ZoneType.MINING,
                coordinates=(3000.0, 200.0, 5500.0),
                floor_level=1,
                darksteel_density=1.2,
                danger_level=5,
                recommended_power=150000,
                spawn_points=[
                    (2950.0, 200.0, 5480.0),
                ],
                ore_positions=[
                    (2980.0, 200.0, 5510.0),
                    (3020.0, 200.0, 5540.0),
                    (3050.0, 200.0, 5560.0),
                    (3080.0, 200.0, 5580.0),
                ]
            ),
        ]
        
        for loc in default_locations:
            self._locations[loc.location_id] = loc
    
    def get_location(self, location_id: str) -> Optional[MiningLocation]:
        return self._locations.get(location_id)
    
    def get_all_locations(self) -> List[MiningLocation]:
        return list(self._locations.values())
    
    def get_locations_by_zone(self, zone_type: ZoneType) -> List[MiningLocation]:
        return [loc for loc in self._locations.values() if loc.zone_type == zone_type]
    
    def get_locations_by_floor(self, floor: int) -> List[MiningLocation]:
        return [loc for loc in self._locations.values() if loc.floor_level == floor]
    
    def get_best_mining_location(self, player_power: int) -> Optional[MiningLocation]:
        suitable = [
            loc for loc in self._locations.values()
            if loc.zone_type == ZoneType.MINING and loc.recommended_power <= player_power
        ]
        
        if not suitable:
            return None
        
        return max(suitable, key=lambda x: x.darksteel_density)
    
    def set_current_location(self, location_id: str):
        if location_id in self._locations:
            self._current_location = self._locations[location_id]
            self._location_history.append(location_id)
    
    def get_current_location(self) -> Optional[MiningLocation]:
        return self._current_location
    
    def calculate_distance(self, loc1: MiningLocation, loc2: MiningLocation) -> float:
        dx = loc1.coordinates[0] - loc2.coordinates[0]
        dy = loc1.coordinates[1] - loc2.coordinates[1]
        dz = loc1.coordinates[2] - loc2.coordinates[2]
        return (dx*dx + dy*dy + dz*dz) ** 0.5
    
    def find_nearest_location(self, position: Tuple[float, float, float], zone_type: Optional[ZoneType] = None) -> Optional[MiningLocation]:
        locations = self._locations.values()
        
        if zone_type:
            locations = [loc for loc in locations if loc.zone_type == zone_type]
        
        if not locations:
            return None
        
        def distance(loc):
            dx = loc.coordinates[0] - position[0]
            dy = loc.coordinates[1] - position[1]
            dz = loc.coordinates[2] - position[2]
            return (dx*dx + dy*dy + dz*dz) ** 0.5
        
        return min(locations, key=distance)
    
    def add_custom_location(self, location: MiningLocation):
        self._locations[location.location_id] = location
    
    def remove_location(self, location_id: str):
        if location_id in self._locations:
            del self._locations[location_id]
    
    def save_to_file(self, file_path: str):
        data = {}
        for loc_id, loc in self._locations.items():
            data[loc_id] = {
                "name": loc.name,
                "zone_type": loc.zone_type.name,
                "coordinates": loc.coordinates,
                "floor_level": loc.floor_level,
                "darksteel_density": loc.darksteel_density,
                "danger_level": loc.danger_level,
                "recommended_power": loc.recommended_power,
                "spawn_points": loc.spawn_points,
                "ore_positions": loc.ore_positions,
            }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, file_path: str):
        if not os.path.exists(file_path):
            return
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        for loc_id, loc_data in data.items():
            location = MiningLocation(
                location_id=loc_id,
                name=loc_data["name"],
                zone_type=ZoneType[loc_data["zone_type"]],
                coordinates=tuple(loc_data["coordinates"]),
                floor_level=loc_data["floor_level"],
                darksteel_density=loc_data["darksteel_density"],
                danger_level=loc_data["danger_level"],
                recommended_power=loc_data["recommended_power"],
                spawn_points=[tuple(p) for p in loc_data.get("spawn_points", [])],
                ore_positions=[tuple(p) for p in loc_data.get("ore_positions", [])],
            )
            self._locations[loc_id] = location
