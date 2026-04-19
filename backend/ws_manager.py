import asyncio
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # We need to iterate over a copy of the list to safely remove disconnected websockets
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
                
        for conn in disconnected:
            self.disconnect(conn)

    def sync_broadcast(self, message: dict):
        """Helper to broadcast from synchronous code like the agent."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
        except RuntimeError:
            asyncio.run(self.broadcast(message))

manager = ConnectionManager()
