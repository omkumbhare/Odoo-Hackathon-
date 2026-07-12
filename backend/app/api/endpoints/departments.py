from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.models import Department, User
from app.schemas.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity, create_notification

router = APIRouter()

@router.get("/", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"]))
):
    # Check if department code or name already exists
    existing = db.query(Department).filter(
        (Department.name == dept_in.name) | (Department.code == dept_in.code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department with this name or code already exists"
        )
    
    # Check manager if specified
    if dept_in.manager_id:
        manager = db.query(User).filter(User.id == dept_in.manager_id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager user not found"
            )

    db_dept = Department(
        name=dept_in.name,
        code=dept_in.code,
        manager_id=dept_in.manager_id
    )
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Created Department: {db_dept.name}",
        category="Department",
        details=f"Code: {db_dept.code}, Manager ID: {db_dept.manager_id}"
    )
    
    # Notify manager if assigned
    if db_dept.manager_id:
        create_notification(
            db,
            user_id=db_dept.manager_id,
            title="Assigned as Department Head",
            message=f"You have been assigned as head of department: {db_dept.name}.",
            notification_type="Info"
        )

    return db_dept

@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: int,
    dept_in: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"]))
):
    db_dept = db.query(Department).filter(Department.id == dept_id).first()
    if not db_dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    if dept_in.name is not None:
        db_dept.name = dept_in.name
    if dept_in.code is not None:
        db_dept.code = dept_in.code
    
    if dept_in.manager_id is not None:
        if dept_in.manager_id == 0:
            db_dept.manager_id = None
        else:
            manager = db.query(User).filter(User.id == dept_in.manager_id).first()
            if not manager:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager user not found")
            # Update role of manager to Department Head if not already Admin/Asset Manager
            if manager.role not in ["Admin", "Asset Manager", "Department Head"]:
                manager.role = "Department Head"
                db.add(manager)
            db_dept.manager_id = dept_in.manager_id
            
            create_notification(
                db,
                user_id=dept_in.manager_id,
                title="Assigned as Department Head",
                message=f"You have been assigned head of department: {db_dept.name}.",
                notification_type="Info"
            )

    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)

    log_activity(
        db,
        user_id=current_user.id,
        action=f"Updated Department: {db_dept.name}",
        category="Department",
        details=f"Updated code/manager configurations."
    )
    
    return db_dept

@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"]))
):
    db_dept = db.query(Department).filter(Department.id == dept_id).first()
    if not db_dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    # Check if there are employees assigned to this department
    users_count = db.query(User).filter(User.department_id == dept_id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete department. There are active employees assigned to it."
        )

    log_activity(
        db,
        user_id=current_user.id,
        action=f"Deleted Department: {db_dept.name}",
        category="Department",
        details=f"Code: {db_dept.code}"
    )

    db.delete(db_dept)
    db.commit()
    return None
