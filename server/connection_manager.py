from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Class defining socket events"""
    def __init__(self):
        """init method, keeping track of connections"""
        self.active_connections = []
    
    async def connect(self, websocket: WebSocket):
        """connect event"""
        await websocket.accept()
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Direct Message - handle closed sockets gracefully"""
        try:
            # Check if WebSocket is in active connections before attempting to send
            if websocket not in self.active_connections:
                logger.debug("Attempted to send message to WebSocket not in active connections")
                
                return
            await websocket.send_text(message)
        except RuntimeError as e:
            # Raised when a close message has already been sent
            logger.debug("WebSocket send failed (runtime): %s", e)
            try:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
            except ValueError:
                pass
        except WebSocketDisconnect:
            # WebSocket was disconnected during send
            logger.debug("WebSocket disconnected during send operation")
            try:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
            except ValueError:
                pass
        except Exception as e:
            # Catch-all to avoid crashing the caller loop
            logger.exception("Unexpected error sending websocket message: %s", e)
            try:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
            except ValueError:
                pass
    
    def disconnect(self, websocket: WebSocket):
        """disconnect event"""
        try:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected and removed from active connections")
        except ValueError:
            # socket already removed; ignore
            logger.info(f"WebSocket already removed from active connections")
            pass