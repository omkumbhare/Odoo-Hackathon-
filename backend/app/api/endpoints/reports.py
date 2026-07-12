from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import pandas as pd
from datetime import datetime
from typing import Optional

from app.db.session import get_db
from app.models.models import Asset, AssetCategory, User
from app.core.security import get_current_user, RoleChecker

# ReportLab libraries for PDF export
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as RLTable, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

router = APIRouter()

def get_filtered_assets_df(db: Session, category_id: Optional[int] = None, status: Optional[str] = None):
    query = db.query(Asset)
    if category_id:
        query = query.filter(Asset.category_id == category_id)
    if status:
        query = query.filter(Asset.status == status)
        
    assets = query.all()
    
    asset_list = []
    for a in assets:
        asset_list.append({
            "ID": a.id,
            "Asset Tag": a.asset_tag,
            "Name": a.name,
            "Category": a.category.name if a.category else "N/A",
            "Model": a.model or "",
            "Serial Number": a.serial_number or "",
            "Purchase Date": a.purchase_date.strftime("%Y-%m-%d") if a.purchase_date else "",
            "Purchase Cost": a.purchase_cost,
            "Status": a.status,
            "Current Location": a.current_location or ""
        })
        
    df = pd.DataFrame(asset_list)
    if df.empty:
        df = pd.DataFrame(columns=["ID", "Asset Tag", "Name", "Category", "Model", "Serial Number", "Purchase Date", "Purchase Cost", "Status", "Current Location"])
    return df

@router.get("/export/csv")
def export_csv(
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    df = get_filtered_assets_df(db, category_id, status)
    
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename=asset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return response

@router.get("/export/excel")
def export_excel(
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    df = get_filtered_assets_df(db, category_id, status)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Assets Inventory")
        
    output.seek(0)
    response = StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response.headers["Content-Disposition"] = f"attachment; filename=asset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return response

@router.get("/export/pdf")
def export_pdf(
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin", "Asset Manager"]))
):
    df = get_filtered_assets_df(db, category_id, status)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom colors matching dark theme
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor('#0d6efd'),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        name='SubTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#6c757d'),
        spaceAfter=25
    )
    
    # Title & Subtitle Headers
    story.append(Paragraph("AssetFlow - Enterprise Asset Report", title_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Filter status: {status or 'All'} | Categories: {category_id or 'All'}", subtitle_style))
    
    # Table data mapping
    table_data = [["Asset Tag", "Asset Name", "Category", "Cost", "Status", "Location"]]
    for _, row in df.iterrows():
        table_data.append([
            str(row["Asset Tag"]),
            str(row["Name"]),
            str(row["Category"]),
            f"${row['Purchase Cost']:.2f}",
            str(row["Status"]),
            str(row["Current Location"])
        ])
        
    t = RLTable(table_data, colWidths=[80, 130, 90, 60, 80, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#212529')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(t)
    doc.build(story)
    
    buffer.seek(0)
    response = StreamingResponse(
        buffer,
        media_type="application/pdf"
    )
    response.headers["Content-Disposition"] = f"attachment; filename=asset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return response
