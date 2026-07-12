from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.models import Asset, AssetCategory, User
from app.schemas.schemas import AssetCreate, AssetResponse, AssetUpdate
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity

router = APIRouter()

@router.get("/", response_model=List[AssetResponse])
def get_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = "purchase_date",
    sort_order: Optional[str] = "desc"
):
    query = db.query(Asset)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Asset.name.like(search_filter)) | 
            (Asset.asset_tag.like(search_filter)) |
            (Asset.model.like(search_filter)) |
            (Asset.serial_number.like(search_filter))
        )
        
    if category_id:
        query = query.filter(Asset.category_id == category_id)
        
    if status:
        query = query.filter(Asset.status == status)
        
    # Sorting
    if sort_by and hasattr(Asset, sort_by):
        column = getattr(Asset, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
            
    return query.offset(skip).limit(limit).all()

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset_by_id(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset

@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    # Verify category
    category = db.query(AssetCategory).filter(AssetCategory.id == asset_in.category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        
    # Verify asset tag is unique
    existing = db.query(Asset).filter(Asset.asset_tag == asset_in.asset_tag).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset tag '{asset_in.asset_tag}' already exists."
        )
        
    db_asset = Asset(
        name=asset_in.name,
        asset_tag=asset_in.asset_tag,
        category_id=asset_in.category_id,
        model=asset_in.model,
        serial_number=asset_in.serial_number,
        purchase_date=asset_in.purchase_date,
        purchase_cost=asset_in.purchase_cost,
        status=asset_in.status if asset_in.status else "Available",
        current_location=asset_in.current_location
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Registered Asset: {db_asset.name}",
        category="Asset",
        details=f"Tag: {db_asset.asset_tag}, Price: ${db_asset.purchase_cost}"
    )
    
    return db_asset

@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
    if asset_in.category_id is not None:
        category = db.query(AssetCategory).filter(AssetCategory.id == asset_in.category_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        asset.category_id = asset_in.category_id
        
    if asset_in.asset_tag is not None:
        existing = db.query(Asset).filter(Asset.asset_tag == asset_in.asset_tag, Asset.id != asset_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset tag '{asset_in.asset_tag}' already exists."
            )
        asset.asset_tag = asset_in.asset_tag
        
    if asset_in.name is not None:
        asset.name = asset_in.name
    if asset_in.model is not None:
        asset.model = asset_in.model
    if asset_in.serial_number is not None:
        asset.serial_number = asset_in.serial_number
    if asset_in.purchase_date is not None:
        asset.purchase_date = asset_in.purchase_date
    if asset_in.purchase_cost is not None:
        asset.purchase_cost = asset_in.purchase_cost
    if asset_in.status is not None:
        asset.status = asset_in.status
    if asset_in.current_location is not None:
        asset.current_location = asset_in.current_location
        
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Updated Asset: {asset.name}",
        category="Asset",
        details=f"Tag: {asset.asset_tag}, Status set to: {asset.status}"
    )
    
    return asset

@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
    # Prevent deleting dynamic allocations that are active
    if asset.status == "Allocated":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete asset. It is currently allocated to an active employee or department."
        )
        
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Deleted Asset: {asset.name}",
        category="Asset",
        details=f"Tag: {asset.asset_tag}"
    )
    
    db.delete(asset)
    db.commit()
    return None
