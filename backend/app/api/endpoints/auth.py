from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

from app.db.session import get_db
from app.models.models import User, Department
from app.schemas.schemas import UserCreate, UserResponse, Token
from app.core.security import verify_password, get_password_hash, create_access_token, get_current_user
from app.crud.crud import log_activity, create_notification

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check department if specified
    if user_in.department_id:
        dept = db.query(Department).filter(Department.id == user_in.department_id).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )

    hashed_pw = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        role=user_in.role,
        department_id=user_in.department_id,
        is_active=user_in.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    log_activity(
        db, 
        user_id=None, 
        action=f"User Registration: {db_user.email}", 
        category="Auth", 
        details=f"Registered user with role {db_user.role}"
    )

    # Trigger admin notification
    admins = db.query(User).filter(User.role == "Admin").all()
    for admin in admins:
        create_notification(
            db,
            user_id=admin.id,
            title="New User Registered",
            message=f"user {db_user.full_name} ({db_user.email}) has registered as {db_user.role}.",
            notification_type="Info"
        )

    return db_user

@router.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        log_activity(
            db,
            user_id=None,
            action="Failed Login Attempt",
            category="Auth",
            details=f"Attempted email: {form_data.username}",
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive"
        )
        
    access_token_expires = timedelta(minutes=1440)  # 24 hours
    access_token = create_access_token(
        data={"user_id": user.id, "role": user.role},
        expires_delta=access_token_expires
    )
    
    log_activity(
        db,
        user_id=user.id,
        action="User Login Successful",
        category="Auth",
        details=f"Logged in user: {user.email} (Role: {user.role})",
        ip_address=request.client.host if request.client else None
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
