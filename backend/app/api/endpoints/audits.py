from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.db.session import get_db
from app.models.models import AuditRecord, Asset, User
from app.schemas.schemas import AuditRecordCreate, AuditRecordResponse
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity, create_notification

router = APIRouter()

@router.get("/", response_model=List[AuditRecordResponse])
def get_audits(
    db: Session = Depends(get_db), 
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    return db.query(AuditRecord).order_by(AuditRecord.audit_date.desc()).all()

@router.post("/", response_model=AuditRecordResponse, status_code=status.HTTP_201_CREATED)
def record_audit(
    audit_in: AuditRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    # Verify asset
    asset = db.query(Asset).filter(Asset.id == audit_in.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
    db_audit = AuditRecord(
        asset_id=audit_in.asset_id,
        auditor_id=current_user.id,
        condition=audit_in.condition,
        status=audit_in.status,
        notes=audit_in.notes
    )
    
    # If the asset status is reported as "Missing", we automatically update the asset's database status to "Disposed" or maintain status representation
    if audit_in.status == "Missing":
        asset.status = "Disposed"
        db.add(asset)
        
    db.add(db_audit)
    db.commit()
    db.refresh(db_audit)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Audited Asset ID {asset.id} ({asset.name})",
        category="Audit",
        details=f"Condition: {audit_in.condition}, Verification status: {audit_in.status}. Notes: {audit_in.notes}"
    )
    
    # Trigger notifications if missing or poor condition
    if audit_in.status == "Missing" or audit_in.condition == "Poor":
        admins = db.query(User).filter(User.role == "Admin").all()
        for admin in admins:
            create_notification(
                db,
                user_id=admin.id,
                title="Critical Asset Audit Notification",
                message=f"Asset '{asset.name}' has been audited in status '{audit_in.status}' with condition '{audit_in.condition}'.",
                notification_type="Alert"
            )
            
    return db_audit
