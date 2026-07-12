from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.db.session import get_db
from app.models.models import Asset, MaintenanceRecord, User
from app.schemas.schemas import MaintenanceRecordCreate, MaintenanceRecordResponse, MaintenanceRecordComplete
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity, create_notification

router = APIRouter()

@router.get("/", response_model=List[MaintenanceRecordResponse])
def get_maintenances(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Admins/Managers see all records
    if current_user.role in ["Admin", "Asset Manager"]:
        return db.query(MaintenanceRecord).order_by(MaintenanceRecord.scheduled_date.desc()).all()
    # Employees only see records they reported
    return db.query(MaintenanceRecord).filter(
        MaintenanceRecord.reported_by_id == current_user.id
    ).order_by(MaintenanceRecord.scheduled_date.desc()).all()

@router.post("/", response_model=MaintenanceRecordResponse, status_code=status.HTTP_201_CREATED)
def schedule_maintenance(
    m_in: MaintenanceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify asset
    asset = db.query(Asset).filter(Asset.id == m_in.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
    db_rec = MaintenanceRecord(
        asset_id=m_in.asset_id,
        reported_by_id=current_user.id,
        maintenance_type=m_in.maintenance_type,
        description=m_in.description,
        scheduled_date=m_in.scheduled_date,
        status="Scheduled"
    )
    
    # Update asset status
    asset.status = "Under Maintenance"
    db.add(asset)
    db.add(db_rec)
    db.commit()
    db.refresh(db_rec)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Scheduled Maintenance ID {db_rec.id}",
        category="Maintenance",
        details=f"Asset ID: {m_in.asset_id}, Type: {m_in.maintenance_type}"
    )
    
    # Notify Admin/Asset Manager
    managers = db.query(User).filter(User.role.in_(["Admin", "Asset Manager"])).all()
    for mgr in managers:
        create_notification(
            db,
            user_id=mgr.id,
            title="Asset Maintenance Scheduled",
            message=f"Maintenance scheduled for asset '{asset.name}' due to: {m_in.description}",
            notification_type="Info"
        )
        
    return db_rec

@router.put("/{record_id}/start", response_model=MaintenanceRecordResponse)
def start_maintenance(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    rec = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
    
    if rec.status != "Scheduled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maintenance can only start from Scheduled status.")
        
    rec.status = "In Progress"
    db.add(rec)
    db.commit()
    db.refresh(rec)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Started Maintenance ID {rec.id}",
        category="Maintenance"
    )
    return rec

@router.put("/{record_id}/complete", response_model=MaintenanceRecordResponse)
def complete_maintenance(
    record_id: int,
    m_comp: MaintenanceRecordComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    rec = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
        
    if rec.status not in ["Scheduled", "In Progress"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maintenance already completed or cancelled.")
        
    rec.completion_date = m_comp.completion_date
    rec.cost = m_comp.cost
    rec.notes = m_comp.notes
    rec.status = m_comp.status if m_comp.status else "Completed"
    
    # Restore asset status to Available if completed, or check context.
    # What if it should stay Allocated? Typically it resets to Available,
    # and the staff can allocate it again, or we check previous allocation.
    # Let's default to setting asset back to Available.
    asset = db.query(Asset).filter(Asset.id == rec.asset_id).first()
    if asset:
        asset.status = "Available"
        db.add(asset)
        
    db.add(rec)
    db.commit()
    db.refresh(rec)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Completed Maintenance ID {rec.id}",
        category="Maintenance",
        details=f"Asset ID: {rec.asset_id}, Final Cost: ${m_comp.cost}. Status set to: {rec.status}"
    )
    
    # Notify reporter
    create_notification(
        db,
        user_id=rec.reported_by_id,
        title="Asset Maintenance Finished",
        message=f"The maintenance for your reported issue on asset '{asset.name if asset else 'Resource'}' is marked: {rec.status}.",
        notification_type="Info"
    )
    
    return rec
