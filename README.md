# AssetFlow ERP — Enterprise Asset & Resource Management System

AssetFlow is a production-quality, full-stack Enterprise Resource Planning (ERP) platform designed for automating asset lifecycles, bookable corporate resources, inter-departmental transfers, and hardware status auditing.

---

## 🏛️ System Architecture

The project consists of a high-performance backend API serving a modern, glassmorphic bootstrap user interface:

* **Backend Stack:** FastAPI (Python), SQLAlchemy (ORM), JWT Authentication (`python-jose`), Password Hashing (`bcrypt`), SQLite (Local database), and Pandas & ReportLab (Report Export engines).
* **Frontend Stack:** Bootstrap 5 (CSS framework), Chart.js (Interactive dashboards), Vanilla JS (App lifecycle & state controller).

---

## ⚙️ Installation & Local Setup

### 📋 Prerequisites
Ensure you have the following installed on your machine:
* Python 3.10 or higher
* Node.js / npm (Optional, only for local package serving)

### 📥 Step 1: Install Dependencies
Open your terminal in the backend directory and install all requirements:
```bash
cd e:/odoo/backend
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 🗄️ Step 2: Database Setup & Seeding
The application is pre-configured to check for the SQLite database (`asset_flow.db`) upon launching. If the database is missing or empty, **FastAPI initiates automatic model reflection and runs the seed sequence**:
* Rebuilds all tables (`Users`, `Departments`, `AssetCategory`, `Asset`, `AssetAllocation`, `TransferRequest`, `ResourceBookable`, `ResourceBooking`, `MaintenanceRecord`, `AuditRecord`, `Notification`, `ActivityLog`).
* Adds default departments (`IT`, `HR`, `Operations`).
* Creates core hierarchal workflow accounts (Admin, Asset Manager, Department Head, Employee).
* Seeds bookable resources (meeting rooms, projectors, vehicles).

---

## 🚀 Running the ERP

### Starting the FastAPI Server (Fast detached wrapper)
You can spawn the uvicorn web process directly. Under Windows, we leverage PowerShell's `Start-Process` tool to run the process in a clean detached background worker:

```powershell
# Execute in e:/odoo/backend
Start-Process python -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -NoNewWindow
```

### Access Ports and Interfaces
* **Web UI URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Redoc UI Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔐 Configuration & Environment Variables

For security and deployment upgrades, you can customize the core variables inside `backend/app/core/config.py` or export them as environment variables:

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `"AssetFlow ERP"` | Title metadata for Swagger documentation. |
| `API_V1_STR` | `"/api/v1"` | Base path router prefix for all requests. |
| `SECRET_KEY` | `"SUPER_SECRET_KEY_ASSET_FLOW_2026_ERP_SYSTEM"` | Used to encode/decode JWT authorization payloads. |
| `DATABASE_URL` | `"sqlite:///./asset_flow.db"` | SQLAlchemy connection URI. Change to PostgreSQL in production. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT Lifespan (24 Hours). |

---

## 👥 Seed Accounts for Testing

Log in to the web interface with the corresponding credentials to examine specific workflows:

| User Account | Access Role | Password | Targeted E2E Use Cases |
| :--- | :--- | :--- | :--- |
| `admin@assetflow.com` | **Admin** | `admin123` | Complete visibility across employee profiles, department adjustments, and server security log tables. |
| `manager@assetflow.com` | **Asset Manager** | `manager123` | Asset onboarding, check-out allocations, scheduling audits, resolving maintenance tickets, downloads. |
| `head@assetflow.com` | **Department Head** | `head123` | Department approval queues, inter-department transfers, booking shared resources. |
| `employee@assetflow.com` | **Employee** | `employee123` | View assigned hardware models, request brand new transfers, and check status feeds. |

---

## 👨‍💻 Key Workflows Implemented

1. **Asset Allocation Lifecycle:** Register an asset $\rightarrow$ Allocate to Employee/Dept (shifts status to *Allocated*) $\rightarrow$ Return Asset (shifts status to *Available*).
2. **Resource Booking Scheduler:** Request room booking $\rightarrow$ Conflict engine checks for time overlaps $\rightarrow$ Pending approval alert sent to Admin dashboard.
3. **Maintenance Ticket Workflow:** Log defect (shifts status to *Under Maintenance*) $\rightarrow$ Start repair (shifts status to *In Progress*) $\rightarrow$ Complete/Cancel (accumulates cost and returns asset status to *Available*).
4. **Data Exports:** Filter inventory records by category or status and download in **PDF**, **Excel**, or **CSV** formats dynamically.
