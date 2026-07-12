from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.models import AssetCategory, User, Asset
from app.schemas.schemas import AssetCategoryCreate, AssetCategoryResponse
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity

router = APIRouter()

@router.get("/", response_model=List[AssetCategoryResponse])
def get_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(AssetCategory).all()

@router.post("/", response_model=AssetCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    cat_in: AssetCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    existing = db.query(AssetCategory).filter(
        (AssetCategory.name == cat_in.name) | (AssetCategory.code == cat_in.code)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name or code already exists"
        )
        
    db_cat = AssetCategory(
        name=cat_in.name,
        code=cat_in.code,
        description=cat_in.description
    )
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Created Category: {db_cat.name}",
        category="AssetCategory",
        details=f"Code: {db_cat.code}"
    )
    
    return db_cat

@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    cat = db.query(AssetCategory).filter(AssetCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        
    # Check if there are active assets in this category
    assets_count = db.query(Asset).filter(Asset.category_id == cat_id).count()
    if assets_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category. There are assets associated with it."
        )
        
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Deleted Category: {cat.name}",
        category="AssetCategory",
        details=f"Code: {cat.code}"
    )
    
    db.delete(cat)
    db.commit()
    return None
