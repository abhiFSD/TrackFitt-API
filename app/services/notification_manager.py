from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
import asyncio

from app.models.models import NotificationType, User, UserRole
from app.services.notification_service import NotificationService
from app.services.websocket_service import connection_manager

class NotificationManager:
    @staticmethod
    async def create_and_send_notification(
        db: Session,
        notification_type: NotificationType,
        user_id: int,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Create a notification in the database and send it in real-time if the user is connected
        """
        # Create notification in the database
        notification = NotificationService.create_notification(
            db=db,
            notification_type=notification_type,
            user_id=user_id,
            title=title,
            message=message,
            data=data
        )
        
        # Prepare notification for WebSocket
        notification_data = {
            "type": "notification",
            "notification_id": notification.id,
            "notification_type": notification.type.value,
            "title": notification.title,
            "message": notification.message,
            "data": json.loads(notification.data) if notification.data else None,
            "timestamp": notification.created_at.isoformat()
        }
        
        # Send real-time notification
        await connection_manager.send_personal_notification(user_id, notification_data)
        
        return notification
    
    @staticmethod
    async def notify_admins(
        db: Session,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        save_to_db: bool = True
    ):
        """
        Notify all admin users
        """
        # Get all admin users
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
        
        for admin in admin_users:
            if save_to_db:
                # Save notification to database
                await NotificationManager.create_and_send_notification(
                    db=db,
                    notification_type=NotificationType.ADMIN_NOTIFICATION,
                    user_id=admin.id,
                    title=title,
                    message=message,
                    data=data
                )
            else:
                # Just send real-time notification without saving
                notification_data = {
                    "type": "notification",
                    "notification_type": "admin_notification",
                    "title": title,
                    "message": message,
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await connection_manager.send_personal_notification(admin.id, notification_data)
    
    @staticmethod
    async def broadcast_system_notification(
        db: Session,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        save_to_db: bool = True
    ):
        """
        Broadcast a system notification to all connected users
        """
        users = []
        
        if save_to_db:
            # Get all active users
            users = db.query(User).filter(User.is_active == True).all()
            
            # Create notifications for each user
            for user in users:
                NotificationService.create_notification(
                    db=db,
                    notification_type=NotificationType.SYSTEM_NOTIFICATION,
                    user_id=user.id,
                    title=title,
                    message=message,
                    data=data
                )
        
        # Broadcast to all connected users
        notification_data = {
            "type": "notification",
            "notification_type": "system_notification",
            "title": title,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await connection_manager.broadcast(notification_data)
    
    # Specialized notification methods for different events
    
    @staticmethod
    async def notify_token_request(db: Session, request_id: int, user_id: int, amount: int, reason: str):
        """
        Notify admins when a token request is created
        """
        await NotificationManager.notify_admins(
            db=db,
            title="New Token Request",
            message=f"User ID {user_id} has requested {amount} tokens",
            data={
                "request_id": request_id,
                "user_id": user_id,
                "amount": amount,
                "reason": reason
            }
        )
    
    @staticmethod
    async def notify_token_request_status(
        db: Session, 
        request_id: int, 
        user_id: int, 
        approved: bool, 
        admin_id: int,
        amount: int
    ):
        """
        Notify a user when their token request status is updated
        """
        status = "approved" if approved else "rejected"
        notification_type = NotificationType.TOKEN_APPROVED if approved else NotificationType.TOKEN_REJECTED
        
        await NotificationManager.create_and_send_notification(
            db=db,
            notification_type=notification_type,
            user_id=user_id,
            title=f"Token Request {status.capitalize()}",
            message=f"Your request for {amount} tokens has been {status}",
            data={
                "request_id": request_id,
                "status": status,
                "admin_id": admin_id,
                "amount": amount
            }
        )
    
    @staticmethod
    async def notify_workout_completed(db: Session, user_id: int, workout_history_id: int, title: str, tokens_earned: int = 0):
        """
        Notify a user when they complete a workout
        """
        message = f"You completed the workout: {title}"
        if tokens_earned > 0:
            message += f" and earned {tokens_earned} tokens!"
        
        await NotificationManager.create_and_send_notification(
            db=db,
            notification_type=NotificationType.WORKOUT_COMPLETED,
            user_id=user_id,
            title="Workout Completed",
            message=message,
            data={
                "workout_history_id": workout_history_id,
                "tokens_earned": tokens_earned
            }
        ) 