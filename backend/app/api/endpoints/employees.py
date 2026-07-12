from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.models import User, Department
from app.schemas.schemas import UserResponse, UserUpdate
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
def get_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    role: Optional[str] = None
):
    query = db.query(User)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.full_name.like(search_filter)) | 
            (User.email.like(search_filter))
        )
    
    if department_id:
        query = query.filter(User.department_id == department_id)
        
    if role:
        query = query.filter(User.role == role)
        
    return query.offset(skip).limit(limit).all()

@router.get("/{emp_id}", response_model=UserResponse)
def get_employee_by_id(
    emp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(User).filter(User.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return emp

@router.put("/{emp_id}", response_model=UserResponse)
def update_employee(
    emp_id: int,
    emp_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"]))
):
    emp = db.query(User).filter(User.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        
    if emp_in.email is not None:
        # Check if email is already taken by another user
        chk = db.query(User).filter(User.email == emp_in.email, User.id != emp_id).first()
        if chk:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        emp.email = emp_in.email
        
    if emp_in.full_name is not None:
        emp.full_name = emp_in.full_name
        
    if emp_in.role is not None:
        roles_list = [r.strip() for r in emp_in.role.split(",")]
        for r in roles_list:
            if r not in ["Admin", "Asset Manager", "Department Head", "Employee"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role specified")
        emp.role = emp_in.role
        
    if emp_in.department_id is not None:
        if emp_in.department_id == 0:
            emp.department_id = None
        else:
            dept = db.query(Department).filter(Department.id == emp_in.department_id).first()
            if not dept:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
            emp.department_id = emp_in.department_id
            
    if emp_in.is_active is not None:
        emp.is_active = emp_in.is_active
        
    if emp_in.password is not None:
        from app.core.security import get_password_hash
        emp.hashed_password = get_password_hash(emp_in.password)
        
    db.add(emp)
    db.commit()
    db.refresh(emp)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Updated Employee Profile: {emp.email}",
        category="Employee",
        details=f"Modified roles, status, or details."
    )
    
    return emp

@router.delete("/{emp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    emp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"]))
):
    if emp_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete yourself")
        
    emp = db.query(User).filter(User.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Deleted Employee: {emp.email}",
        category="Employee",
        details=f"Name: {emp.full_name}"
    )
    
    db.delete(emp)
    db.commit()
    return None
