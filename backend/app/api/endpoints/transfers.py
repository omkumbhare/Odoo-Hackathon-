from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.db.session import get_db
from app.models.models import Asset, TransferRequest, Department, User, AssetAllocation
from app.schemas.schemas import TransferRequestCreate, TransferRequestResponse, TransferRequestUpdate
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity, create_notification

router = APIRouter()

@router.get("/", response_model=List[TransferRequestResponse])
def get_transfers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Admins/Asset Managers can see all
    if current_user.role in ["Admin", "Asset Manager"]:
        return db.query(TransferRequest).all()
    # Department Heads can see transfers related to their department (source or target)
    elif current_user.role == "Department Head":
        dept = db.query(Department).filter(Department.manager_id == current_user.id).first()
        if dept:
            return db.query(TransferRequest).filter(
                (TransferRequest.source_dept_id == dept.id) | 
                (TransferRequest.target_dept_id == dept.id)
            ).all()
    # Employees can only see their own requests
    return db.query(TransferRequest).filter(TransferRequest.requested_by_id == current_user.id).all()

@router.post("/", response_model=TransferRequestResponse, status_code=status.HTTP_201_CREATED)
def request_transfer(
    req_in: TransferRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify asset
    asset = db.query(Asset).filter(Asset.id == req_in.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
    # Verify target department
    target_dept = db.query(Department).filter(Department.id == req_in.target_dept_id).first()
    if not target_dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target department not found")
        
    # Source department is determined by the asset's active allocation or the requesting user's department
    source_dept_id = None
    active_alloc = db.query(AssetAllocation).filter(
        AssetAllocation.asset_id == asset.id, 
        AssetAllocation.status == "Active"
    ).first()
    
    if active_alloc:
        if active_alloc.allocated_dept_id:
            source_dept_id = active_alloc.allocated_dept_id
        elif active_alloc.allocated_to:
            source_dept_id = active_alloc.allocated_to.department_id
            
    if not source_dept_id:
        source_dept_id = current_user.department_id

    # Create request
    db_req = TransferRequest(
        asset_id=req_in.asset_id,
        requested_by_id=current_user.id,
        source_dept_id=source_dept_id,
        target_dept_id=req_in.target_dept_id,
        reason=req_in.reason,
        status="Pending"
    )
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Requested Asset Transfer: ID {asset.name}",
        category="Transfer",
        details=f"From Dept ID: {source_dept_id} to Dept ID: {req_in.target_dept_id}"
    )

    # Notify managers of departments
    if target_dept.manager_id:
        create_notification(
            db,
            user_id=target_dept.manager_id,
            title="Asset Transfer Pending Approval",
            message=f"A transfer request for asset '{asset.name}' is waiting your approval.",
            notification_type="Approval"
        )
        
    return db_req

@router.put("/{transfer_id}", response_model=TransferRequestResponse)
def handle_transfer_decision(
    transfer_id: int,
    decision: TransferRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(TransferRequest).filter(TransferRequest.id == transfer_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer request not found")
        
    if req.status != "Pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request has already been processed.")
        
    # Check permissions: Admin or Target Dept Head can approve/reject
    is_admin = current_user.role in ["Admin", "Asset Manager"]
    is_target_dept_head = False
    if current_user.role == "Department Head":
        dept = db.query(Department).filter(Department.id == req.target_dept_id).first()
        if dept and dept.manager_id == current_user.id:
            is_target_dept_head = True
            
    if not (is_admin or is_target_dept_head):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to approve/reject this transfer request."
        )

    # Process decision
    req.status = decision.status
    req.approved_by_id = current_user.id
    req.comments = decision.comments
    
    if decision.status == "Approved":
        asset = db.query(Asset).filter(Asset.id == req.asset_id).first()
        if asset:
            # Terminate active allocation first
            active_allocs = db.query(AssetAllocation).filter(
                AssetAllocation.asset_id == asset.id,
                AssetAllocation.status == "Active"
            ).all()
            for alloc in active_allocs:
                alloc.status = "Returned"
                alloc.return_date = datetime.utcnow()
                db.add(alloc)
            
            # Start a new department allocation
            new_alloc = AssetAllocation(
                asset_id=asset.id,
                allocated_dept_id=req.target_dept_id,
                allocated_by_id=current_user.id,
                allocation_date=datetime.utcnow(),
                status="Active"
            )
            db.add(new_alloc)
            
            # Update asset location and state
            asset.status = "Allocated"
            dept = db.query(Department).filter(Department.id == req.target_dept_id).first()
            if dept:
                asset.current_location = f"{dept.name} Division"
            db.add(asset)
            
        log_activity(
            db,
            user_id=current_user.id,
            action=f"Approved Transfer ID {req.id}",
            category="Transfer",
            details=f"Asset ID {req.asset_id} moved to Department ID {req.target_dept_id}."
        )
        
        create_notification(
            db,
            user_id=req.requested_by_id,
            title="Transfer Request Approved",
            message=f"Your transfer request for asset ID {req.asset_id} has been approved.",
            notification_type="Info"
        )
    else:
        log_activity(
            db,
            user_id=current_user.id,
            action=f"Rejected Transfer ID {req.id}",
            category="Transfer",
            details=f"Reason: {decision.comments}"
        )
        create_notification(
            db,
            user_id=req.requested_by_id,
            title="Transfer Request Rejected",
            message=f"Your transfer request for asset ID {req.asset_id} has been rejected. Reason: {decision.comments}",
            notification_type="Alert"
        )
        
    db.add(req)
    db.commit()
    db.refresh(req)
    return req
