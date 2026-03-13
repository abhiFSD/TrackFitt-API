from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Any, Optional
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        # Dictionary to store active connections: {user_id: WebSocket}
        self.active_connections: Dict[int, WebSocket] = {}
        # Dictionary to store admin connections separately
        self.admin_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket, user_id: int, is_admin: bool = False):
        """
        Connect a user's WebSocket and store the connection
        """
        await websocket.accept()
        
        # Store regular user connection
        self.active_connections[user_id] = websocket
        
        # If admin, also store in admin connections
        if is_admin:
            self.admin_connections.append(websocket)
            
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to notification service",
            "timestamp": datetime.now().isoformat()
        })
    
    def disconnect(self, user_id: int, is_admin: bool = False):
        """
        Disconnect a user and remove their connection
        """
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            del self.active_connections[user_id]
            
            # Also remove from admin connections if applicable
            if is_admin and websocket in self.admin_connections:
                self.admin_connections.remove(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected clients
        """
        # Create a list of disconnected users to clean up
        disconnected_users = []
        
        # Send to all active connections
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            is_admin = self.active_connections[user_id] in self.admin_connections
            self.disconnect(user_id, is_admin)
    
    async def broadcast_to_admins(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected admin clients
        """
        # Create a list of disconnected admins to clean up
        disconnected_admins = []
        
        # Send to all admin connections
        for websocket in self.admin_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected_admins.append(websocket)
        
        # Clean up disconnected admins
        for websocket in disconnected_admins:
            self.admin_connections.remove(websocket)
            # Also remove from active connections
            disconnected_user_ids = []
            for user_id, ws in self.active_connections.items():
                if ws == websocket:
                    disconnected_user_ids.append(user_id)
            
            for user_id in disconnected_user_ids:
                del self.active_connections[user_id]
    
    async def send_personal_notification(self, user_id: int, message: Dict[str, Any]):
        """
        Send a notification to a specific user
        """
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                return True
            except Exception:
                # Remove the connection if it's broken
                is_admin = self.active_connections[user_id] in self.admin_connections
                self.disconnect(user_id, is_admin)
                return False
        return False
    
    async def send_to_multiple_users(self, user_ids: List[int], message: Dict[str, Any]):
        """
        Send a notification to multiple specific users
        """
        for user_id in user_ids:
            await self.send_personal_notification(user_id, message)

# Create a global connection manager
connection_manager = ConnectionManager() 