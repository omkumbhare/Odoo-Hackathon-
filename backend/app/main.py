import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.models.models import Base, User, Department, AssetCategory, ResourceBookable, SystemSetting, LookupOption
from app.core.security import get_password_hash
from app.api.endpoints import auth, departments, employees, categories, assets, allocations, transfers, bookings, maintenance, audits, dashboard, reports, logs_notifs

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    
    # Speed data seeding for local testing and first deployment
    db = SessionLocal()
    try:
        # Check if system administrator is already registered
        admin_exists = db.query(User).filter(User.email == "admin@assetflow.com").first()
        if not admin_exists:
            # Create default departments
            it_dept = Department(name="Information Technology", code="IT")
            hr_dept = Department(name="Human Resources", code="HR")
            ops_dept = Department(name="Operations", code="OPS")
            db.add_all([it_dept, hr_dept, ops_dept])
            db.commit()
            db.refresh(it_dept)
            db.refresh(hr_dept)
            db.refresh(ops_dept)
            
            # Create core role hierarchy accounts
            admin_user = User(
                email="admin@assetflow.com",
                hashed_password=get_password_hash("admin123"),
                full_name="System Administrator",
                role="Admin",
                department_id=it_dept.id,
                is_active=True
            )
            mgr_user = User(
                email="manager@assetflow.com",
                hashed_password=get_password_hash("manager123"),
                full_name="Asset Manager",
                role="Asset Manager",
                department_id=it_dept.id,
                is_active=True
            )
            head_user = User(
                email="head@assetflow.com",
                hashed_password=get_password_hash("head123"),
                full_name="Department Head", 
                role="Department Head", 
                department_id=ops_dept.id,
                is_active=True
            )
            emp_user = User(
                email="employee@assetflow.com",
                hashed_password=get_password_hash("employee123"),
                full_name="John Doe", 
                role="Employee", 
                department_id=ops_dept.id,
                is_active=True
            )
            db.add_all([admin_user, mgr_user, head_user, emp_user])
            db.commit()
            
            # Assign department managers
            it_dept.manager_id = admin_user.id
            hr_dept.manager_id = mgr_user.id
            ops_dept.manager_id = head_user.id
            db.add_all([it_dept, hr_dept, ops_dept])
            db.commit()
            
            # Seed Asset Categories
            cats = [
                AssetCategory(name="Laptops & Computers", code="COMP", description="Workstations, developer rigs, and server racks"),
                AssetCategory(name="Office Desk Furniture", code="FURN", description="Adjustable desks, chairs, cabinet drawers"),
                AssetCategory(name="Infrastructure Equipment", code="NET", description="Routers, server switches, optical transceivers"),
                AssetCategory(name="Company Vehicles", code="VEH", description="Car pools, delivery trucks, field machinery")
            ]
            db.add_all(cats)
            
            # Seed Bookable Resources
            res = [
                ResourceBookable(name="Conference Room A (Ground Floor)", type="Conference Room", description="Conference table, smart TV, projector, 12 seats capacity"),
                ResourceBookable(name="Corporate Sedan (Model S)", type="Vehicle", description="Business travel dispatch passenger car"),
                ResourceBookable(name="Portable 4K VC Projector", type="Equipment", description="Portable high brightness conference presentation projector")
            ]
            db.add_all(res)
            
            # Seed dynamic SystemSettings
            settings_list = [
                SystemSetting(key="company_name", value="AssetFlow ERP Corp", description="Corporate entity title"),
                SystemSetting(key="company_logo", value="/img/logo.png", description="Link directory endpoint to company logo"),
                SystemSetting(key="address", value="100 Tech Drive, Suite 500, New York, NY", description="Office standard location"),
                SystemSetting(key="timezone", value="America/New_York", description="Standard local timezone setting"),
                SystemSetting(key="currency", value="USD ($)", description="Standard monetary formatting key"),
                SystemSetting(key="language", value="English", description="System language option"),
                SystemSetting(key="session_timeout_minutes", value="60", description="Admin session duration limits"),
                SystemSetting(key="password_min_length", value="8", description="Constraint threshold for authentication security")
            ]
            db.add_all(settings_list)
            
            # Seed dynamic LookupOptions for Location/Office grids
            lookups_list = [
                LookupOption(category="Location", name="New York Headquarters"),
                LookupOption(category="Location", name="San Francisco Lab Branch"),
                LookupOption(category="Building", name="East Wing Corporate Plaza"),
                LookupOption(category="Building", name="West Wing Tech Suite"),
                LookupOption(category="Floor", name="1st Floor Executive"),
                LookupOption(category="Floor", name="2nd Floor Labs"),
                LookupOption(category="Room", name="Gold Room 102"),
                LookupOption(category="Room", name="Boardroom Suite 504"),
                LookupOption(category="Vendor", name="Dell Technologies Enterprise"),
                LookupOption(category="Vendor", name="Steelcase Office Furnishings"),
                LookupOption(category="Manufacturer", name="Cisco Systems Inc"),
                LookupOption(category="Manufacturer", name="Tesla Motors Fleet"),
                LookupOption(category="Condition", name="Excellent"),
                LookupOption(category="Condition", name="Good"),
                LookupOption(category="Condition", name="Fair"),
                LookupOption(category="Condition", name="Poor"),
                LookupOption(category="Status", name="Available"),
                LookupOption(category="Status", name="Allocated"),
                LookupOption(category="Status", name="Under Maintenance"),
                LookupOption(category="Status", name="Disposed"),
                LookupOption(category="TimeSlot", name="09:00 AM - 11:00 AM"),
                LookupOption(category="TimeSlot", name="11:00 AM - 01:00 PM"),
                LookupOption(category="TimeSlot", name="02:00 PM - 04:00 PM"),
                LookupOption(category="TimeSlot", name="04:00 PM - 06:00 PM"),
                LookupOption(category="TransferReason", name="Departmental Relocation"),
                LookupOption(category="TransferReason", name="Hardware Upgrade Replacement"),
                LookupOption(category="TransferReason", name="Remote Workforce Transfer")
            ]
            db.add_all(lookups_list)
            db.commit()
            print("Successfully initialized and seeded enterprise database with dynamic Lookups & Settings.")
    except Exception as e:
        print(f"Err during table configuration or seeding: {e}")
    finally:
        db.close()
    
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware Configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach API endpoints router to global pipeline
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(departments.router, prefix=f"{settings.API_V1_STR}/departments", tags=["Departments Management"])
app.include_router(employees.router, prefix=f"{settings.API_V1_STR}/employees", tags=["Employee Directory"])
app.include_router(categories.router, prefix=f"{settings.API_V1_STR}/categories", tags=["Asset Categories"])
app.include_router(assets.router, prefix=f"{settings.API_V1_STR}/assets", tags=["Asset Inventory"])
app.include_router(allocations.router, prefix=f"{settings.API_V1_STR}/allocations", tags=["Asset Allocations"])
app.include_router(transfers.router, prefix=f"{settings.API_V1_STR}/transfers", tags=["Asset Transfer Workflow"])
app.include_router(bookings.router, prefix=f"{settings.API_V1_STR}/bookings", tags=["Resource Bookings"])
app.include_router(maintenance.router, prefix=f"{settings.API_V1_STR}/maintenance", tags=["Maintenance Records"])
app.include_router(audits.router, prefix=f"{settings.API_V1_STR}/audits", tags=["Asset Audit Tracking"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard Metrics"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["Data Export Reports"])
app.include_router(logs_notifs.router, prefix=f"{settings.API_V1_STR}/system", tags=["System logs & Notifications"])

# Statically feed root web pages from '../frontend' directory
frontend_static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_static_dir):
    app.mount("/", StaticFiles(directory=frontend_static_dir, html=True), name="frontend")
else:
    print(f"Warn: static frontend path not found at recursive query trace: '{frontend_static_dir}'")
