import heapq
import math
import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Set

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class Waypoint:
    waypoint_id: int
    position: Tuple[float, float, float]
    connections: List[int] = field(default_factory=list)
    weight: float = 1.0
    is_safe: bool = True
    is_blocked: bool = False


@dataclass
class PathNode:
    position: Tuple[float, float, float]
    g_cost: float = 0.0
    h_cost: float = 0.0
    parent: Optional['PathNode'] = None
    
    @property
    def f_cost(self) -> float:
        return self.g_cost + self.h_cost
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost


class NavigationMesh:
    def __init__(self):
        self._vertices: List[Tuple[float, float, float]] = []
        self._triangles: List[Tuple[int, int, int]] = []
        self._adjacency: Dict[int, List[int]] = {}
        self._bounds = ((0, 0, 0), (10000, 1000, 10000))
        self._cell_size = 10.0
        self._grid: Dict[Tuple[int, int], List[int]] = {}
        
    def build_from_terrain(self, terrain_data: bytes):
        vertex_count = len(terrain_data) // 12
        
        for i in range(vertex_count):
            offset = i * 12
            x = int.from_bytes(terrain_data[offset:offset+4], 'little') / 100.0
            y = int.from_bytes(terrain_data[offset+4:offset+8], 'little') / 100.0
            z = int.from_bytes(terrain_data[offset+8:offset+12], 'little') / 100.0
            self._vertices.append((x, y, z))
        
        self._build_triangles()
        self._build_adjacency()
        self._build_spatial_grid()
    
    def _build_triangles(self):
        if len(self._vertices) < 3:
            return
        
        for i in range(0, len(self._vertices) - 2, 3):
            self._triangles.append((i, i + 1, i + 2))
    
    def _build_adjacency(self):
        for i, tri in enumerate(self._triangles):
            self._adjacency[i] = []
            
            for j, other_tri in enumerate(self._triangles):
                if i == j:
                    continue
                
                shared = len(set(tri) & set(other_tri))
                if shared >= 2:
                    self._adjacency[i].append(j)
    
    def _build_spatial_grid(self):
        for i, vertex in enumerate(self._vertices):
            cell_x = int(vertex[0] / self._cell_size)
            cell_z = int(vertex[2] / self._cell_size)
            cell_key = (cell_x, cell_z)
            
            if cell_key not in self._grid:
                self._grid[cell_key] = []
            self._grid[cell_key].append(i)
    
    def find_nearest_vertex(self, position: Tuple[float, float, float]) -> int:
        cell_x = int(position[0] / self._cell_size)
        cell_z = int(position[2] / self._cell_size)
        
        search_radius = 1
        candidates = []
        
        for dx in range(-search_radius, search_radius + 1):
            for dz in range(-search_radius, search_radius + 1):
                cell_key = (cell_x + dx, cell_z + dz)
                if cell_key in self._grid:
                    candidates.extend(self._grid[cell_key])
        
        if not candidates:
            candidates = list(range(len(self._vertices)))
        
        def distance(idx):
            v = self._vertices[idx]
            dx = v[0] - position[0]
            dy = v[1] - position[1]
            dz = v[2] - position[2]
            return dx*dx + dy*dy + dz*dz
        
        return min(candidates, key=distance)
    
    def get_triangle_center(self, triangle_idx: int) -> Tuple[float, float, float]:
        if triangle_idx >= len(self._triangles):
            return (0, 0, 0)
        
        tri = self._triangles[triangle_idx]
        v0 = self._vertices[tri[0]]
        v1 = self._vertices[tri[1]]
        v2 = self._vertices[tri[2]]
        
        return (
            (v0[0] + v1[0] + v2[0]) / 3,
            (v0[1] + v1[1] + v2[1]) / 3,
            (v0[2] + v1[2] + v2[2]) / 3
        )
    
    def is_walkable(self, position: Tuple[float, float, float]) -> bool:
        cell_x = int(position[0] / self._cell_size)
        cell_z = int(position[2] / self._cell_size)
        cell_key = (cell_x, cell_z)
        
        return cell_key in self._grid and len(self._grid[cell_key]) > 0


class WaypointSystem:
    def __init__(self):
        self._waypoints: Dict[int, Waypoint] = {}
        self._next_id = 0
        self._path_cache: Dict[Tuple[int, int], List[int]] = {}
        
    def add_waypoint(self, position: Tuple[float, float, float], is_safe: bool = True) -> int:
        wp_id = self._next_id
        self._next_id += 1
        
        self._waypoints[wp_id] = Waypoint(
            waypoint_id=wp_id,
            position=position,
            is_safe=is_safe
        )
        
        return wp_id
    
    def connect_waypoints(self, wp1_id: int, wp2_id: int, bidirectional: bool = True):
        if wp1_id in self._waypoints and wp2_id in self._waypoints:
            if wp2_id not in self._waypoints[wp1_id].connections:
                self._waypoints[wp1_id].connections.append(wp2_id)
            
            if bidirectional and wp1_id not in self._waypoints[wp2_id].connections:
                self._waypoints[wp2_id].connections.append(wp1_id)
    
    def auto_connect(self, max_distance: float = 50.0):
        wp_list = list(self._waypoints.values())
        
        for i, wp1 in enumerate(wp_list):
            for wp2 in wp_list[i+1:]:
                dx = wp1.position[0] - wp2.position[0]
                dy = wp1.position[1] - wp2.position[1]
                dz = wp1.position[2] - wp2.position[2]
                dist = (dx*dx + dy*dy + dz*dz) ** 0.5
                
                if dist <= max_distance:
                    self.connect_waypoints(wp1.waypoint_id, wp2.waypoint_id)
    
    def find_path(self, start_id: int, end_id: int) -> List[int]:
        cache_key = (start_id, end_id)
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]
        
        if start_id not in self._waypoints or end_id not in self._waypoints:
            return []
        
        open_set = [(0, start_id)]
        came_from: Dict[int, int] = {}
        g_score: Dict[int, float] = {start_id: 0}
        
        end_pos = self._waypoints[end_id].position
        
        while open_set:
            _, current = heapq.heappop(open_set)
            
            if current == end_id:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                self._path_cache[cache_key] = path
                return path
            
            current_wp = self._waypoints[current]
            
            for neighbor_id in current_wp.connections:
                neighbor = self._waypoints[neighbor_id]
                
                if neighbor.is_blocked:
                    continue
                
                dx = current_wp.position[0] - neighbor.position[0]
                dy = current_wp.position[1] - neighbor.position[1]
                dz = current_wp.position[2] - neighbor.position[2]
                dist = (dx*dx + dy*dy + dz*dz) ** 0.5
                
                tentative_g = g_score[current] + dist * neighbor.weight
                
                if neighbor_id not in g_score or tentative_g < g_score[neighbor_id]:
                    came_from[neighbor_id] = current
                    g_score[neighbor_id] = tentative_g
                    
                    dx = neighbor.position[0] - end_pos[0]
                    dy = neighbor.position[1] - end_pos[1]
                    dz = neighbor.position[2] - end_pos[2]
                    h = (dx*dx + dy*dy + dz*dz) ** 0.5
                    
                    f_score = tentative_g + h
                    heapq.heappush(open_set, (f_score, neighbor_id))
        
        return []
    
    def get_waypoint(self, wp_id: int) -> Optional[Waypoint]:
        return self._waypoints.get(wp_id)
    
    def find_nearest_waypoint(self, position: Tuple[float, float, float]) -> Optional[int]:
        if not self._waypoints:
            return None
        
        def distance(wp):
            dx = wp.position[0] - position[0]
            dy = wp.position[1] - position[1]
            dz = wp.position[2] - position[2]
            return dx*dx + dy*dy + dz*dz
        
        nearest = min(self._waypoints.values(), key=distance)
        return nearest.waypoint_id


class PathFinder:
    def __init__(self, nav_mesh: Optional[NavigationMesh] = None, waypoint_system: Optional[WaypointSystem] = None):
        self._nav_mesh = nav_mesh or NavigationMesh()
        self._waypoint_system = waypoint_system or WaypointSystem()
        self._current_path: List[Tuple[float, float, float]] = []
        self._path_index = 0
        
    def find_path(self, start: Tuple[float, float, float], end: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
        start_wp = self._waypoint_system.find_nearest_waypoint(start)
        end_wp = self._waypoint_system.find_nearest_waypoint(end)
        
        if start_wp is None or end_wp is None:
            return self._direct_path(start, end)
        
        wp_path = self._waypoint_system.find_path(start_wp, end_wp)
        
        if not wp_path:
            return self._direct_path(start, end)
        
        path = [start]
        for wp_id in wp_path:
            wp = self._waypoint_system.get_waypoint(wp_id)
            if wp:
                path.append(wp.position)
        path.append(end)
        
        self._current_path = path
        self._path_index = 0
        
        return path
    
    def _direct_path(self, start: Tuple[float, float, float], end: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        distance = (dx*dx + dy*dy + dz*dz) ** 0.5
        
        if distance < 10:
            return [start, end]
        
        num_points = int(distance / 10) + 1
        path = []
        
        for i in range(num_points + 1):
            t = i / num_points
            x = start[0] + dx * t
            y = start[1] + dy * t
            z = start[2] + dz * t
            path.append((x, y, z))
        
        return path
    
    def get_next_point(self) -> Optional[Tuple[float, float, float]]:
        if self._path_index < len(self._current_path):
            point = self._current_path[self._path_index]
            self._path_index += 1
            return point
        return None
    
    def has_path(self) -> bool:
        return self._path_index < len(self._current_path)
    
    def reset_path(self):
        self._current_path = []
        self._path_index = 0
    
    def smooth_path(self, path: List[Tuple[float, float, float]], iterations: int = 3) -> List[Tuple[float, float, float]]:
        if len(path) < 3:
            return path
        
        smoothed = list(path)
        
        for _ in range(iterations):
            new_path = [smoothed[0]]
            
            for i in range(1, len(smoothed) - 1):
                prev = smoothed[i - 1]
                curr = smoothed[i]
                next_ = smoothed[i + 1]
                
                x = (prev[0] + curr[0] * 2 + next_[0]) / 4
                y = (prev[1] + curr[1] * 2 + next_[1]) / 4
                z = (prev[2] + curr[2] * 2 + next_[2]) / 4
                
                new_path.append((x, y, z))
            
            new_path.append(smoothed[-1])
            smoothed = new_path
        
        return smoothed
