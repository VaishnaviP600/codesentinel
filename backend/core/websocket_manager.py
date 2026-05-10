"""
WebSocket Manager — Broadcasts real-time scan progress
to all connected frontend clients.
"""

import json
from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Map of scan_id -> list of connected websockets
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # All connections (for broadcast)
        self.all_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, scan_id: int = None):
        await websocket.accept()
        self.all_connections.append(websocket)
        if scan_id:
            if scan_id not in self.active_connections:
                self.active_connections[scan_id] = []
            self.active_connections[scan_id].append(websocket)
        logger.info(f"WebSocket connected (scan_id={scan_id}). Total: {len(self.all_connections)}")

    def disconnect(self, websocket: WebSocket, scan_id: int = None):
        if websocket in self.all_connections:
            self.all_connections.remove(websocket)
        if scan_id and scan_id in self.active_connections:
            if websocket in self.active_connections[scan_id]:
                self.active_connections[scan_id].remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.all_connections)}")

    async def send_to_scan(self, scan_id: int, message: dict):
        connections = self.active_connections.get(scan_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, scan_id)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.all_connections:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def broadcast_scan_update(scan_id: int, data: dict):
    await manager.send_to_scan(scan_id, data)
    await manager.broadcast(data)
