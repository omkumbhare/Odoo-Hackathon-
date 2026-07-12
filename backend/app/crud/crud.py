from sqlalchemy.orm import Session
from typing import Optional
from app.models.models import ActivityLog, Notification

def log_activity(
    db: Session,
    user_id: Optional[int],
    action: str,
    category: str,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    browser: Optional[str] = None,
    affected_module: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None
) -> ActivityLog:
    db_log = ActivityLog(
        user_id=user_id,
        action=action,
        category=category,
        details=details,
        ip_address=ip_address,
        browser=browser,
        affected_module=affected_module,
        old_value=old_value,
        new_value=new_value
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "Information"
) -> Notification:
    db_notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type
    )
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    return db_notif
