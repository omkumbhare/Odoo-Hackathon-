from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from app.db.session import get_db
from app.models.models import Asset, AssetAllocation, MaintenanceRecord, ResourceBooking, ActivityLog, User, TransferRequest
from app.schemas.schemas import DashboardStats, KPIItem, ActivityLogResponse, MaintenanceRecordResponse, ResourceBookingResponse
from app.core.security import get_current_user

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Total Assets Count
    total_assets = db.query(Asset).count()
    
    # 2. Allocated Assets Count
    allocated_assets = db.query(Asset).filter(Asset.status == "Allocated").count()
    
    # 3. Maintenance Assets Count
    maintenance_assets = db.query(Asset).filter(Asset.status == "Under Maintenance").count()
    
    # 4. Total Cost/Value of Assets
    total_value = db.query(func.sum(Asset.purchase_cost)).scalar() or 0.0
    
    # 5. Build standard KPIs list
    kpis = [
        KPIItem(
            title="Total Assets",
            value=str(total_assets),
            change="+10% from last month",
            icon="bi-box-seam",
            color="primary"
        ),
        KPIItem(
            title="Allocated Assets",
            value=str(allocated_assets),
            change=f"{round((allocated_assets/total_assets)*100 if total_assets > 0 else 0, 1)}% allocation rate",
            icon="bi-person-check",
            color="success"
        ),
        KPIItem(
            title="Under Maintenance",
            value=str(maintenance_assets),
            change="Active repair tickets",
            icon="bi-wrench",
            color="warning"
        ),
        KPIItem(
            title="Total Valuation",
            value=f"${round(total_value, 2):,}",
            change="Capital asset value",
            icon="bi-currency-dollar",
            color="info"
        )
    ]
    
    # 6. Fetch Recent Activity Logs
    recent_logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(8).all()
    
    # 7. Fetch Pending Maintenance
    pending_maint = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.status == "Scheduled"
    ).order_by(MaintenanceRecord.scheduled_date.asc()).limit(5).all()
    
    # 8. Fetch Pending Bookings
    pending_bookings = db.query(ResourceBooking).filter(
        ResourceBooking.status == "Pending"
    ).order_by(ResourceBooking.start_time.asc()).limit(5).all()
    
    return DashboardStats(
        kpis=kpis,
        recent_activities=recent_logs,
        maintenance_pending=pending_maint,
        bookings_pending=pending_bookings
    )

@router.get("/charts/category-distribution")
def get_category_distribution(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Group assets by category
    results = db.query(
        Asset.category_id,
        func.count(Asset.id).label("count")
    ).group_by(Asset.category_id).all()
    
    from app.models.models import AssetCategory
    chart_data = []
    for cat_id, count in results:
        cat = db.query(AssetCategory).filter(AssetCategory.id == cat_id).first()
        chart_data.append({
            "label": cat.name if cat else "Unsorted",
            "value": count
        })
    return chart_data

@router.get("/charts/status-distribution")
def get_status_distribution(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    results = db.query(
        Asset.status,
        func.count(Asset.id).label("count")
    ).group_by(Asset.status).all()
    
    return [{"label": status, "value": count} for status, count in results]
