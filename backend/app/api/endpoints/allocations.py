from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.db.session import get_db
from app.models.models import Asset, AssetAllocation, User, Department
from app.schemas.schemas import AssetAllocationCreate, AssetAllocationResponse
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity, create_notification

router = APIRouter()

@router.get("/", response_model=List[AssetAllocationResponse])
def get_allocations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = None
):
    query = db.query(AssetAllocation)
    if status:
        query = query.filter(AssetAllocation.status == status)
    
    # If not Admin or Asset Manager, only view their own allocations
    if current_user.role not in ["Admin", "Asset Manager"]:
        query = query.filter(AssetAllocation.allocated_to_id == current_user.id)
        
    return query.order_by(AssetAllocation.allocation_date.desc()).all()

@router.post("/", response_model=AssetAllocationResponse, status_code=status.HTTP_201_CREATED)
def allocate_asset(
    alloc_in: AssetAllocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == alloc_in.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
    # Check if asset is available (Business rule: Prevent duplicate allocations)
    if asset.status != "Available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset is not available for allocation. Current status: {asset.status}."
        )
        
    # Ensure checking either user or department holds the destination
    if not alloc_in.allocated_to_id and not alloc_in.allocated_dept_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Allocation must target either a user or a department."
        )
        
    if alloc_in.allocated_to_id:
        user = db.query(User).filter(User.id == alloc_in.allocated_to_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")
            
    if alloc_in.allocated_dept_id:
        dept = db.query(Department).filter(Department.id == alloc_in.allocated_dept_id).first()
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target department not found")
            
    # Perform allocation
    db_alloc = AssetAllocation(
        asset_id=alloc_in.asset_id,
        allocated_to_id=alloc_in.allocated_to_id,
        allocated_dept_id=alloc_in.allocated_dept_id,
        allocated_by_id=current_user.id,
        return_due_date=alloc_in.return_due_date,
        status="Active"
    )
    
    # Update asset status
    asset.status = "Allocated"
    db.add(asset)
    db.add(db_alloc)
    db.commit()
    db.refresh(db_alloc)
    
    # Log and notifications
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Allocated Asset ID {asset.id} ({asset.name})",
        category="Allocation",
        details=f"Allocated to User: {alloc_in.allocated_to_id}, Dept: {alloc_in.allocated_dept_id}."
    )
    
    if alloc_in.allocated_to_id:
        create_notification(
            db,
            user_id=alloc_in.allocated_to_id,
            title="New Asset Allocated",
            message=f"You have been allocated the asset: {asset.name} ({asset.asset_tag}).",
            notification_type="Info"
        )
        
    return db_alloc

@router.post("/{alloc_id}/return", response_model=AssetAllocationResponse)
def return_asset(
    alloc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    db_alloc = db.query(AssetAllocation).filter(AssetAllocation.id == alloc_id).first()
    if not db_alloc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation record not found")
        
    if db_alloc.status == "Returned":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset already returned.")
        
    # Update allocation
    db_alloc.return_date = datetime.utcnow()
    db_alloc.status = "Returned"
    
    # Update asset status
    asset = db.query(Asset).filter(Asset.id == db_alloc.asset_id).first()
    if asset:
        asset.status = "Available"
        db.add(asset)
        
    db.add(db_alloc)
    db.commit()
    db.refresh(db_alloc)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Returned Asset ID {db_alloc.asset_id}",
        category="Allocation",
        details=f"Allocation ID: {db_alloc.id} marked as Returned."
    )
    
    if db_alloc.allocated_to_id:
        create_notification(
            db,
            user_id=db_alloc.allocated_to_id,
            title="Asset Returned",
            message=f"Asset {asset.name if asset else 'Resource'} has been successfully checked in list.",
            notification_type="Info"
        )
        
    return db_alloc
