import quest.quest_handle

import struct
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List, Dict, Callable


class PacketType(Enum):
    LOGIN = 0x01
    LOGOUT = 0x02
    MOVE = 0x10
    ATTACK = 0x11
    SKILL = 0x12
    CHAT = 0x20
    TRADE = 0x30
    MINING = 0x40
    QUEST = 0x50
    INVENTORY = 0x60
    SMELT = 0x70


@dataclass
class Packet:
    packet_id: int
    packet_type: PacketType
    data: bytes
    timestamp: float
    is_encrypted: bool = True


class PacketHandler:
    def __init__(self, engine):
        self._engine = engine
        self._send_queue: List[Packet] = []
        self._recv_queue: List[Packet] = []
        self._handlers: Dict[PacketType, List[Callable]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._packet_counter = 0
        self._offsets = {
            "send_func": 0x1A5F40,
            "recv_func": 0x1A6280,
            "packet_buffer": 0x02AE7B20,
        }
        
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._packet_loop)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def _packet_loop(self):
        while self._running:
            self._process_send_queue()
            self._process_recv_queue()
            time.sleep(0.01)
    
    def _process_send_queue(self):
        while self._send_queue:
            packet = self._send_queue.pop(0)
            self._send_packet(packet)
    
    def _process_recv_queue(self):
        pass
    
    def _send_packet(self, packet: Packet):
        header = struct.pack('<HHI', packet.packet_id, packet.packet_type.value, len(packet.data))
        full_packet = header + packet.data
        
        buffer_addr = self._engine._base_address + self._offsets["packet_buffer"]
        self._engine.write_memory(buffer_addr, full_packet)
    
    def send(self, packet_type: PacketType, data: bytes) -> int:
        self._packet_counter += 1
        packet = Packet(
            packet_id=self._packet_counter,
            packet_type=packet_type,
            data=data,
            timestamp=time.time()
        )
        self._send_queue.append(packet)
        return packet.packet_id
    
    def register_handler(self, packet_type: PacketType, handler: Callable):
        if packet_type not in self._handlers:
            self._handlers[packet_type] = []
        self._handlers[packet_type].append(handler)
    
    def send_move(self, x: float, y: float, z: float) -> int:
        data = struct.pack('<fff', x, y, z)
        return self.send(PacketType.MOVE, data)
    
    def send_mining_start(self, node_id: int) -> int:
        data = struct.pack('<I', node_id)
        return self.send(PacketType.MINING, data)
    
    def send_smelt_request(self, darksteel_amount: int) -> int:
        data = struct.pack('<I', darksteel_amount)
        return self.send(PacketType.SMELT, data)
