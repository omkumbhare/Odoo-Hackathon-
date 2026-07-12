import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.db.session import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=False, unique=True)
    manager_id = Column(Integer, ForeignKey("users.id", name="fk_department_manager", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    manager = relationship("User", foreign_keys=[manager_id], post_update=True)
    employees = relationship("User", foreign_keys="[User.department_id]", back_populates="department")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # Admin, Asset Manager, Department Head, Employee
    department_id = Column(Integer, ForeignKey("departments.id", name="fk_user_department", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    department = relationship("Department", foreign_keys=[department_id], back_populates="employees")
    allocations = relationship("AssetAllocation", foreign_keys="[AssetAllocation.allocated_to_id]", back_populates="allocated_to")
    bookings = relationship("ResourceBooking", foreign_keys="[ResourceBooking.booked_by_id]", back_populates="booked_by")

class AssetCategory(Base):
    __tablename__ = "asset_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    assets = relationship("Asset", back_populates="category")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    asset_tag = Column(String, unique=True, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("asset_categories.id", ondelete="RESTRICT"), nullable=False)
    model = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    purchase_date = Column(DateTime, nullable=False)
    purchase_cost = Column(Float, nullable=False)
    status = Column(String, default="Available")  # Available, Allocated, Under Maintenance, Disposed
    current_location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    category = relationship("AssetCategory", back_populates="assets")
    allocations = relationship("AssetAllocation", back_populates="asset")
    maintenances = relationship("MaintenanceRecord", back_populates="asset")
    audits = relationship("AuditRecord", back_populates="asset")

class AssetAllocation(Base):
    __tablename__ = "asset_allocations"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    allocated_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Can be to specific user
    allocated_dept_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)  # Or to a department
    allocated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    allocation_date = Column(DateTime, default=datetime.datetime.utcnow)
    return_due_date = Column(DateTime, nullable=True)
    return_date = Column(DateTime, nullable=True)
    status = Column(String, default="Active")  # Active, Returned
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    asset = relationship("Asset", back_populates="allocations")
    allocated_to = relationship("User", foreign_keys=[allocated_to_id], back_populates="allocations")
    allocated_dept = relationship("Department")

class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    requested_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_dept_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    target_dept_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="Pending")  # Pending, Approved, Rejected
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comments = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    asset = relationship("Asset")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    source_dept = relationship("Department", foreign_keys=[source_dept_id])
    target_dept = relationship("Department", foreign_keys=[target_dept_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

class ResourceBookable(Base):
    __tablename__ = "resource_bookables"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Conference Room, Projector, Vehicle, Lab Equipment
    description = Column(String, nullable=True)
    status = Column(String, default="Available")  # Available, Active Bookings, Out of Order
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bookings = relationship("ResourceBooking", back_populates="resource")

class ResourceBooking(Base):
    __tablename__ = "resource_bookings"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resource_bookables.id", ondelete="CASCADE"), nullable=False)
    booked_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    purpose = Column(String, nullable=False)
    status = Column(String, default="Pending")  # Pending, Approved, Rejected, Cancelled
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    resource = relationship("ResourceBookable", back_populates="bookings")
    booked_by = relationship("User", foreign_keys=[booked_by_id], back_populates="bookings")
    approved_by = relationship("User", foreign_keys=[approved_by_id])

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    maintenance_type = Column(String, nullable=False)  # Preventive, Corrective, Upgrade
    description = Column(String, nullable=False)
    scheduled_date = Column(DateTime, nullable=False)
    completion_date = Column(DateTime, nullable=True)
    cost = Column(Float, default=0.0)
    status = Column(String, default="Scheduled")  # Scheduled, In Progress, Completed, Cancelled
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    asset = relationship("Asset", back_populates="maintenances")
    reported_by = relationship("User")

class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    auditor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    audit_date = Column(DateTime, default=datetime.datetime.utcnow)
    condition = Column(String, nullable=False)  # Excellent, Good, Fair, Poor
    status = Column(String, default="Verified")  # Verified, Missing, Misplaced
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    asset = relationship("Asset", back_populates="audits")
    auditor = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    type = Column(String, default="Information")  # Info, Alert, Approval
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Nullable for anonymous/failed logins
    action = Column(String, nullable=False)  # e.g., "Create Asset", "Approve Booking"
    category = Column(String, nullable=False)  # e.g., "Asset", "Booking", "Auth"
    details = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    affected_module = Column(String, nullable=True)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LookupOption(Base):
    __tablename__ = "lookup_options"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True, nullable=False)  # e.g., Vendor, Location, AssetType, Status, Condition, TimeSlot, NotificationTemplate
    name = Column(String, nullable=False)
    value = Column(String, nullable=True)  # custom JSON configurations or target code values
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
