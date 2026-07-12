from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime
from typing import List, Optional

from app.db.session import get_db
from app.models.models import ResourceBookable, ResourceBooking, User
from app.schemas.schemas import ResourceBookableCreate, ResourceBookableResponse, ResourceBookingCreate, ResourceBookingResponse
from app.core.security import get_current_user, RoleChecker
from app.crud.crud import log_activity, create_notification

router = APIRouter()

# ================= BOOKABLE RESOURCES =================
@router.get("/resources", response_model=List[ResourceBookableResponse])
def get_bookable_resources(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ResourceBookable).all()

@router.post("/resources", response_model=ResourceBookableResponse, status_code=status.HTTP_201_CREATED)
def create_bookable_resource(
    res_in: ResourceBookableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    db_res = ResourceBookable(
        name=res_in.name,
        type=res_in.type,
        description=res_in.description,
        status=res_in.status if res_in.status else "Available"
    )
    db.add(db_res)
    db.commit()
    db.refresh(db_res)
    
    log_activity(
        db,
        user_id=current_user.id,
        action=f"Created Bookable Resource: {db_res.name}",
        category="Resource",
        details=f"Type: {db_res.type}"
    )
    return db_res

@router.delete("/resources/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookable_resource(
    res_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"]))
):
    res = db.query(ResourceBookable).filter(ResourceBookable.id == res_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        
    db.delete(res)
    db.commit()
    return None

# ================= BOOKINGS WORKFLOW =================
@router.get("/", response_model=List[ResourceBookingResponse])
def get_bookings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ["Admin", "Asset Manager"]:
        return db.query(ResourceBooking).order_by(ResourceBooking.start_time.desc()).all()
    return db.query(ResourceBooking).filter(
        ResourceBooking.booked_by_id == current_user.id
    ).order_by(ResourceBooking.start_time.desc()).all()

@router.post("/", response_model=ResourceBookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    book_in: ResourceBookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Time validation: start must be before end
    if book_in.start_time >= book_in.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be strictly before end time."
        )
        
    # Verify resource
    res = db.query(ResourceBookable).filter(ResourceBookable.id == book_in.resource_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_444_NOT_FOUND, detail="Resource not found")
        
    if res.status == "Out of Order":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resource is currently out of service.")
        
    # Overlap validation (Business rule: Prevent booking conflicts)
    overlapping = db.query(ResourceBooking).filter(
        ResourceBooking.resource_id == book_in.resource_id,
        ResourceBooking.status.in_(["Approved", "Pending"]),
        and_(
            book_in.start_time < ResourceBooking.end_time,
            book_in.end_time > ResourceBooking.start_time
        )
    ).first()
    
    if overlapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking conflict: This resource is already reserved/pending for the requested time frame."
        )
        
    # Commit booking
    db_booking = ResourceBooking(
        resource_id=book_in.resource_id,
        booked_by_id=current_user.id,
        start_time=book_in.start_time,
        end_time=book_in.end_time,
        purpose=book_in.purpose,
        status="Pending"
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    log_activity(
        db,
        user_id=current_user.id,
        action="Created Resource Booking",
        category="Booking",
        details=f"Resource ID: {book_in.resource_id}, Start: {book_in.start_time}, End: {book_in.end_time}"
    )
    
    # Notify managers of resource
    managers = db.query(User).filter(User.role.in_(["Admin", "Asset Manager"])).all()
    for mgr in managers:
        create_notification(
            db,
            user_id=mgr.id,
            title="Resource Booking Pending Approval",
            message=f"A booking request for '{res.name}' is waiting your approval.",
            notification_type="Approval"
        )
        
    return db_booking

@router.put("/{booking_id}/decision", response_model=ResourceBookingResponse)
def handle_booking_decision(
    booking_id: int,
    approve: bool,  # true = Approved, false = Rejected
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager", "Department Head"]))
):
    booking = db.query(ResourceBooking).filter(ResourceBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking request not found")
        
    if booking.status != "Pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking decision already finalized.")
        
    booking.status = "Approved" if approve else "Rejected"
    booking.approved_by_id = current_user.id
    
    # Log and notify
    log_activity(
        db,
        user_id=current_user.id,
        action=f"{booking.status} Booking ID {booking.id}",
        category="Booking",
        details=f"Approved by user ID: {current_user.id}"
    )
    
    create_notification(
        db,
        user_id=booking.booked_by_id,
        title=f"Booking Request {booking.status}",
        message=f"Your booking for resource ID {booking.resource_id} was {booking.status.lower()}.",
        notification_type="Alert" if not approve else "Info"
    )
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
