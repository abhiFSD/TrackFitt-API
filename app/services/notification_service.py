from sqlalchemy.orm import Session
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.models.models import Notification as DBNotification, NotificationType, User
from app.schemas.schemas import NotificationCreate

class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        notification_type: NotificationType,
        user_id: int,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> DBNotification:
        """
        Create a notification for a user
        """
        data_json = json.dumps(data) if data else None
        
        # Use UTC datetime to ensure consistency across timezones
        notification = DBNotification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data_json,
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        return notification
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False
    ) -> List[DBNotification]:
        """
        Get notifications for a specific user
        """
        query = db.query(DBNotification).filter(DBNotification.user_id == user_id)
        
        if unread_only:
            query = query.filter(DBNotification.is_read == False)
            
        return query.order_by(DBNotification.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def mark_notification_as_read(db: Session, notification_id: int, user_id: int) -> Optional[DBNotification]:
        """
        Mark a notification as read
        """
        notification = db.query(DBNotification).filter(
            DBNotification.id == notification_id,
            DBNotification.user_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            db.commit()
            db.refresh(notification)
            
        return notification
    
    @staticmethod
    def mark_all_notifications_as_read(db: Session, user_id: int) -> int:
        """
        Mark all notifications for a user as read
        Returns the number of notifications updated
        """
        result = db.query(DBNotification).filter(
            DBNotification.user_id == user_id,
            DBNotification.is_read == False
        ).update({"is_read": True})
        
        db.commit()
        return result
    
    @staticmethod
    def get_unread_count(db: Session, user_id: int) -> int:
        """
        Get the count of unread notifications for a user
        """
        return db.query(DBNotification).filter(
            DBNotification.user_id == user_id,
            DBNotification.is_read == False
        ).count()
    
    @staticmethod
    def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
        """
        Delete a notification
        """
        notification = db.query(DBNotification).filter(
            DBNotification.id == notification_id,
            DBNotification.user_id == user_id
        ).first()
        
        if notification:
            db.delete(notification)
            db.commit()
            return True
        
        return False 