from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# ================= AUTHENTICATION =================
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None

# ================= USER / EMPLOYEE =================
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str  # Admin, Asset Manager, Department Head, Employee
    department_id: Optional[int] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ================= DEPARTMENT =================
class DepartmentBase(BaseModel):
    name: str
    code: str
    manager_id: Optional[int] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    manager_id: Optional[int] = None

class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime
    manager: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# ================= ASSET CATEGORY =================
class AssetCategoryBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class AssetCategoryCreate(AssetCategoryBase):
    pass

class AssetCategoryResponse(AssetCategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ================= ASSET =================
class AssetBase(BaseModel):
    name: str
    asset_tag: str
    category_id: int
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: datetime
    purchase_cost: float
    status: Optional[str] = "Available"  # Available, Allocated, Under Maintenance, Disposed
    current_location: Optional[str] = None

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_tag: Optional[str] = None
    category_id: Optional[int] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_cost: Optional[float] = None
    status: Optional[str] = None
    current_location: Optional[str] = None

class AssetResponse(AssetBase):
    id: int
    created_at: datetime
    category: AssetCategoryResponse

    class Config:
        from_attributes = True

# ================= ASSET ALLOCATION =================
class AssetAllocationBase(BaseModel):
    asset_id: int
    allocated_to_id: Optional[int] = None
    allocated_dept_id: Optional[int] = None
    return_due_date: Optional[datetime] = None

class AssetAllocationCreate(AssetAllocationBase):
    pass

class AssetAllocationResponse(BaseModel):
    id: int
    asset_id: int
    allocated_to_id: Optional[int] = None
    allocated_dept_id: Optional[int] = None
    allocated_by_id: int
    allocation_date: datetime
    return_due_date: Optional[datetime] = None
    return_date: Optional[datetime] = None
    status: str
    created_at: datetime
    asset: AssetResponse
    allocated_to: Optional[UserResponse] = None
    allocated_dept: Optional[DepartmentResponse] = None

    class Config:
        from_attributes = True

# ================= TRANSFER REQUEST =================
class TransferRequestBase(BaseModel):
    asset_id: int
    target_dept_id: int
    reason: str

class TransferRequestCreate(TransferRequestBase):
    pass

class TransferRequestUpdate(BaseModel):
    status: str  # Approved, Rejected
    comments: Optional[str] = None

class TransferRequestResponse(BaseModel):
    id: int
    asset_id: int
    requested_by_id: int
    source_dept_id: Optional[int] = None
    target_dept_id: int
    reason: str
    status: str
    approved_by_id: Optional[int] = None
    comments: Optional[str] = None
    created_at: datetime
    asset: AssetResponse
    requested_by: UserResponse
    source_dept: Optional[DepartmentResponse] = None
    target_dept: DepartmentResponse
    approved_by: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# ================= RESOURCE BOOKABLE =================
class ResourceBookableBase(BaseModel):
    name: str
    type: str  # Conference Room, Projector, Vehicle, Lab Equipment
    description: Optional[str] = None
    status: Optional[str] = "Available"

class ResourceBookableCreate(ResourceBookableBase):
    pass

class ResourceBookableResponse(ResourceBookableBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ================= RESOURCE BOOKING =================
class ResourceBookingBase(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime
    purpose: str

class ResourceBookingCreate(ResourceBookingBase):
    pass

class ResourceBookingResponse(BaseModel):
    id: int
    resource_id: int
    booked_by_id: int
    start_time: datetime
    end_time: datetime
    purpose: str
    status: str
    approved_by_id: Optional[int] = None
    created_at: datetime
    resource: ResourceBookableResponse
    booked_by: UserResponse
    approved_by: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# ================= MAINTENANCE RECORD =================
class MaintenanceRecordBase(BaseModel):
    asset_id: int
    maintenance_type: str  # Preventive, Corrective, Upgrade
    description: str
    scheduled_date: datetime

class MaintenanceRecordCreate(MaintenanceRecordBase):
    pass

class MaintenanceRecordComplete(BaseModel):
    completion_date: datetime
    cost: float
    notes: Optional[str] = None
    status: Optional[str] = "Completed"  # Completed or Cancelled

class MaintenanceRecordResponse(BaseModel):
    id: int
    asset_id: int
    reported_by_id: int
    maintenance_type: str
    description: str
    scheduled_date: datetime
    completion_date: Optional[datetime] = None
    cost: float
    status: str
    notes: Optional[str] = None
    created_at: datetime
    asset: AssetResponse
    reported_by: UserResponse

    class Config:
        from_attributes = True

# ================= AUDIT RECORD =================
class AuditRecordBase(BaseModel):
    asset_id: int
    condition: str  # Excellent, Good, Fair, Poor
    status: str  # Verified, Missing, Misplaced
    notes: Optional[str] = None

class AuditRecordCreate(AuditRecordBase):
    pass

class AuditRecordResponse(AuditRecordBase):
    id: int
    auditor_id: int
    audit_date: datetime
    auditor: UserResponse
    asset: AssetResponse

    class Config:
        from_attributes = True

# ================= NOTIFICATION =================
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    type: str
    created_at: datetime

    class Config:
        from_attributes = True

# ================= ACTIVITY LOG =================
class ActivityLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    category: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    browser: Optional[str] = None
    affected_module: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# ================= DASHBOARD METRICS =================
class KPIItem(BaseModel):
    title: str
    value: str
    change: str
    icon: str
    color: str

class DashboardStats(BaseModel):
    kpis: List[KPIItem]
    recent_activities: List[ActivityLogResponse]
    maintenance_pending: List[MaintenanceRecordResponse]
    bookings_pending: List[ResourceBookingResponse]

# ================= SYSTEM SETTINGS & LOOKUP OPTIONS =================
class SystemSettingBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SystemSettingResponse(SystemSettingBase):
    created_at: datetime
    class Config:
        from_attributes = True

class LookupOptionCreate(BaseModel):
    category: str
    name: str
    value: Optional[str] = None
    is_active: Optional[bool] = True

class LookupOptionResponse(BaseModel):
    id: int
    category: str
    name: str
    value: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
