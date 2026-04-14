"""Lightweight websocket broadcaster used to push live notifications to clients.

Frontend can connect to ``ws://<host>/ws/notifications`` and display native /
HTML5 notifications when messages arrive.
"""

from __future__ import annotations

from typing import List, Dict, Any
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.debug("WS connected; total=%s", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.debug("WS disconnected; total=%s", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        """Send a JSON message to all connected clients."""
        stale = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning("WS send failed; pruning connection: %s", e)
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)


manager = ConnectionManager()


async def push_notification(payload: Dict[str, Any]):
    """Broadcast a notification payload to all connected clients."""
    await manager.broadcast({"type": "notification", "data": payload})
