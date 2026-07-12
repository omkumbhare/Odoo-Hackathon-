from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.models import Notification, ActivityLog, User, SystemSetting, LookupOption
from app.schemas.schemas import NotificationResponse, ActivityLogResponse, SystemSettingResponse, LookupOptionResponse, LookupOptionCreate, SystemSettingBase
from app.core.security import get_current_user, RoleChecker

router = APIRouter()

# ================= NOTIFICATIONS =================
@router.get("/notifications", response_model=List[NotificationResponse])
def get_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()

@router.put("/notifications/{notif_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
    notif.is_read = True
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

# ================= ACTIVITY LOGS =================
@router.get("/logs", response_model=List[ActivityLogResponse])
def get_activity_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"])),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    return db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit).all()

# ================= SYSTEM CONFIG SETTINGS =================
@router.get("/settings", response_model=List[SystemSettingResponse])
def get_system_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(SystemSetting).all()

@router.post("/settings", response_model=SystemSettingResponse)
def save_system_setting(
    setting_in: SystemSettingBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"]))
):
    db_setting = db.query(SystemSetting).filter(SystemSetting.key == setting_in.key).first()
    if db_setting:
        db_setting.value = setting_in.value
        if setting_in.description is not None:
            db_setting.description = setting_in.description
    else:
        db_setting = SystemSetting(
            key=setting_in.key,
            value=setting_in.value,
            description=setting_in.description
        )
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting

# ================= DYNAMIC LOOKUP OPTIONS =================
@router.get("/lookup-options", response_model=List[LookupOptionResponse])
def get_lookup_options(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LookupOption)
    if category:
        query = query.filter(LookupOption.category == category)
    return query.all()

@router.post("/lookup-options", response_model=LookupOptionResponse, status_code=status.HTTP_201_CREATED)
def create_lookup_option(
    opt_in: LookupOptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    db_opt = LookupOption(
        category=opt_in.category,
        name=opt_in.name,
        value=opt_in.value,
        is_active=opt_in.is_active if opt_in.is_active is not None else True
    )
    db.add(db_opt)
    db.commit()
    db.refresh(db_opt)
    return db_opt

@router.put("/lookup-options/{opt_id}", response_model=LookupOptionResponse)
def update_lookup_option(
    opt_id: int,
    opt_in: LookupOptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    db_opt = db.query(LookupOption).filter(LookupOption.id == opt_id).first()
    if not db_opt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lookup Option not found")
    
    db_opt.category = opt_in.category
    db_opt.name = opt_in.name
    if opt_in.value is not None:
        db_opt.value = opt_in.value
    if opt_in.is_active is not None:
        db_opt.is_active = opt_in.is_active
        
    db.add(db_opt)
    db.commit()
    db.refresh(db_opt)
    return db_opt

@router.delete("/lookup-options/{opt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lookup_option(
    opt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"]))
):
    db_opt = db.query(LookupOption).filter(LookupOption.id == opt_id).first()
    if not db_opt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lookup Option not found")
    db.delete(db_opt)
    db.commit()
    return None
