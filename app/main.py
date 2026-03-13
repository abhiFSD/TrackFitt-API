from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from jose import jwt
from typing import Optional

from app.api import router
from app.models.models import Base, UserRole
from app.db.database import engine, get_db
from app.services.websocket_service import connection_manager
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the database tables
def create_tables():
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Workout Tracker API",
    description="API for tracking workouts and exercises",
    version="0.1.0"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://trackfitt.onrender.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Authorization"],
)

# Include API router
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Workout Tracker API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# WebSocket for real-time notifications
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=1008, reason="Authorization token missing")
        return
    
    try:
        from app.api.auth import SECRET_KEY, ALGORITHM
        
        # Decode the token to get user info
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if username is None:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Get user from database
        from app.models.models import User
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return
            
        # Check if user is active
        if not user.is_active:
            await websocket.close(code=1008, reason="User is inactive")
            return
        
        # Connect to WebSocket
        is_admin = user.role == UserRole.ADMIN
        await connection_manager.connect(websocket, user.id, is_admin=is_admin)
        
        try:
            # Keep connection alive and handle messages
            while True:
                # Wait for messages (can be used for client interactions)
                data = await websocket.receive_text()
                
                # Handle received data (for future implementation)
                # For now, just echo back to confirm receipt
                await websocket.send_json({
                    "type": "message_received", 
                    "message": f"Received: {data}"
                })
                
        except WebSocketDisconnect:
            # Clean up connection if WebSocket disconnects
            connection_manager.disconnect(user.id, is_admin=is_admin)
        
    except jwt.PyJWTError:
        await websocket.close(code=1008, reason="Invalid token")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close(code=1011, reason="Server error")

# Create tables at startup
@app.on_event("startup")
def startup_event():
    # Wait for database to be ready
    time.sleep(5)
    # Create tables
    create_tables() 