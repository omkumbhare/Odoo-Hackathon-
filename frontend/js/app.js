/* ================= GLOBAL CONTEXT & ROUTING ================= */
const API_BASE = window.location.origin && window.location.origin !== "null" && !window.location.origin.startsWith("file://")
    ? window.location.origin + "/api/v1"
    : "http://127.0.0.1:8000/api/v1";
let currentUser = null;
let charts = {};

// Handle Auth Header Injection
function getHeaders() {
    const token = localStorage.getItem("token");
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    };
}

// Display System Notifications / Alerts
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-white bg-${type} border-0 show mb-2 fade-in-section`;
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.setAttribute("aria-atomic", "true");
    
    let icon = "bi-check-circle-fill";
    if (type === "warning") icon = "bi-exclamation-triangle-fill";
    if (type === "danger") icon = "bi-x-circle-fill";
    if (type === "info") icon = "bi-info-circle-fill";

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi ${icon} me-2"></i>${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    container.appendChild(toast);
    
    // Automatically wipe alert after 4s
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 400);
    }, 4000);
}

// Global Response Interceptor helper
async function request(url, options = {}) {
    options.headers = {
        ...options.headers,
        "bypass-tunnel-reminder": "true"
    };
    try {
        const response = await fetch(url, options);
        if (response.status === 401) {
            handleLogout();
            showToast("Session expired. Please log in again.", "warning");
            throw new Error("Unauthorized");
        }
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const msg = errorData.detail || `HTTP Error ${response.status}`;
            throw new Error(msg);
        }
        if (response.status === 204) return null;
        return await response.json();
    } catch (e) {
        if (e.message !== "Unauthorized") {
            showToast(e.message, "danger");
        }
        throw e;
    }
}

// Page load initialization
window.addEventListener("DOMContentLoaded", () => {
    // Dark mode check
    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateDarkModeIcon(savedTheme === "dark");

    // Session cache check
    const token = localStorage.getItem("token");
    if (token) {
        verifySession();
    } else {
        showAuthPanel(true);
    }
    
    // Auto-update notifications check timer
    setInterval(() => {
        if (currentUser) fetchNotifications();
    }, 30000);
});

// Verify existing JWT credentials
async function verifySession() {
    try {
        currentUser = await request(`${API_BASE}/auth/me`, {
            method: "GET",
            headers: getHeaders()
        });
        showAuthPanel(false);
        setupPermissionsUI();
        switchView("dashboard");
        fetchNotifications();
    } catch (e) {
        handleLogout();
    }
}

function showAuthPanel(show) {
    if (show) {
        document.getElementById("auth-panel").style.display = "flex";
        document.getElementById("erp-panel").style.display = "none";
        loadAuthDepartments();
    } else {
        document.getElementById("auth-panel").style.display = "none";
        document.getElementById("erp-panel").style.display = "block";
        document.getElementById("user-display-name").innerText = currentUser.full_name;
        document.getElementById("user-display-role").innerText = currentUser.role;
    }
}

function toggleAuthMode(register) {
    if (register) {
        document.getElementById("form-login").style.display = "none";
        document.getElementById("form-register").style.display = "block";
        document.getElementById("auth-subtitle").innerText = "Employee Portal Registration";
    } else {
        document.getElementById("form-login").style.display = "block";
        document.getElementById("form-register").style.display = "none";
        document.getElementById("auth-subtitle").innerText = "Enterprise Asset & Resource ERP";
    }
}

async function loadAuthDepartments() {
    try {
        const depts = await request(`${API_BASE}/departments/`, { method: "GET" });
        const regDept = document.getElementById("reg-dept");
        regDept.innerHTML = depts.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join("");
    } catch(e) {}
}

/* ================= AUTHENTICATION ACTIONS ================= */
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
    
    try {
        const data = await request(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData
        });
        localStorage.setItem("token", data.access_token);
        showToast("Welcome back! Loading secure sessions...", "success");
        await verifySession();
    } catch (err) {}
}

async function handleRegister(e) {
    e.preventDefault();
    const email = document.getElementById("reg-email").value;
    const fullName = document.getElementById("reg-name").value;
    const role = document.getElementById("reg-role").value;
    const password = document.getElementById("reg-password").value;
    const department_id = parseInt(document.getElementById("reg-dept").value);
    
    try {
        await request(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, full_name: fullName, role, password, department_id, is_active: true })
        });
        showToast("Profile registered successfully. You can now login.", "success");
        toggleAuthMode(false);
    } catch (err) {}
}

function handleLogout() {
    localStorage.removeItem("token");
    currentUser = null;
    showAuthPanel(true);
}

// Adjust dashboard features depending on User role
function setupPermissionsUI() {
    const role = currentUser.role;
    
    // Toggle Admin actions visibility
    const adminActions = document.querySelectorAll(".text-admin-action");
    adminActions.forEach(el => el.style.display = role === "Admin" ? "table-cell" : "none");
    
    const addDeptBtn = document.getElementById("btn-add-department");
    if(addDeptBtn) addDeptBtn.style.display = role === "Admin" ? "block" : "none";
    
    // Toggle Manager elements visibility
    const mgrActions = document.querySelectorAll(".text-mgr-action");
    mgrActions.forEach(el => el.style.display = (role === "Admin" || role === "Asset Manager") ? "table-cell" : "none");
    
    const mgrBtns = document.querySelectorAll(".btn-mgr-action");
    mgrBtns.forEach(btn => btn.style.display = (role === "Admin" || role === "Asset Manager") ? "block" : "none");
    
    // Render Logs & Settings modules for admin only
    const logSidebar = document.getElementById("link-activity-logs");
    if(logSidebar) logSidebar.style.display = role === "Admin" ? "block" : "none";
    const settingsSidebar = document.getElementById("link-settings");
    if(settingsSidebar) settingsSidebar.style.display = role === "Admin" ? "block" : "none";
    
    // Render Booking Review Column for managers only
    const bookingsCol = document.getElementById("dashboard-bookings-col");
    if (bookingsCol) bookingsCol.style.display = (role === "Admin" || role === "Asset Manager" || role === "Department Head") ? "block" : "none";
}

/* ================= VIEW MANAGER ROUTING ================= */
function switchView(viewId) {
    // Hide all views
    const panels = document.querySelectorAll(".view-panel");
    panels.forEach(p => p.style.display = "none");
    
    // De-activate all sidebar status links
    const links = document.querySelectorAll("#sidebar .nav-link");
    links.forEach(l => l.classList.remove("active"));
    
    // Show chosen view
    const activeView = document.getElementById(`view-${viewId}`);
    if (activeView) activeView.style.display = "block";
    
    const activeLink = document.getElementById(`link-${viewId}`);
    if (activeLink) activeLink.classList.add("active");
    
    // Modify page Title
    let title = viewId.replace("-", " ");
    title = title.charAt(0).toUpperCase() + title.slice(1);
    document.getElementById("navbar-view-title").innerText = `${title} Workstation`;
    
    // Close sidebar on mobile
    document.getElementById("sidebar").classList.remove("show");
    
    // Trigger dynamic data fetchers
    switch(viewId) {
        case "dashboard":
            loadDashboard();
            break;
        case "departments":
            loadDepartments();
            break;
        case "employees":
            loadEmployees();
            break;
        case "categories":
            loadCategories();
            break;
        case "assets":
            loadAssets();
            break;
        case "allocations":
            loadAllocations();
            break;
        case "transfers":
            loadTransfers();
            break;
        case "bookings":
            loadBookings();
            break;
        case "maintenance":
            loadMaintenance();
            break;
        case "audits":
            loadAudits();
            break;
        case "reports":
            loadReportsSelectors();
            break;
        case "activity-logs":
            loadLogs();
            break;
        case "settings":
            loadSystemSettings();
            loadLookupOptionsList();
            break;
    }
}

function toggleSidebarMenu() {
    document.getElementById("sidebar").classList.toggle("show");
}

function toggleDarkMode() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const nextTheme = isDark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", nextTheme);
    localStorage.setItem("theme", nextTheme);
    updateDarkModeIcon(!isDark);
}

function updateDarkModeIcon(isDark) {
    const icon = document.getElementById("dark-mode-icon");
    if(icon) {
        icon.className = isDark ? "bi-sun-fill" : "bi-moon-fill";
    }
}

/* ================= VIEW 1: DASHBOARD DATA ================= */
async function loadDashboard() {
    try {
        const stats = await request(`${API_BASE}/dashboard/stats`, {
            method: "GET",
            headers: getHeaders()
        });
        
        // Render KPIs
        const kpiRow = document.getElementById("dashboard-kpi-row");
        kpiRow.innerHTML = stats.kpis.map(k => `
            <div class="col-md-6 col-lg-3">
                <div class="card glass-panel p-4 h-100 border-start border-4 border-${k.color}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-secondary fw-semibold fs-7">${k.title}</span>
                            <h2 class="fw-bold mt-2 mb-1">${k.value}</h2>
                            <small class="text-secondary">${k.change}</small>
                        </div>
                        <div class="bg-${k.color} bg-opacity-10 p-3 rounded text-${k.color} fs-3">
                            <i class="bi ${k.icon}"></i>
                        </div>
                    </div>
                </div>
            </div>
        `).join("");
        
        // Render Active Logs
        const actList = document.getElementById("dashboard-activities-list");
        if(stats.recent_activities.length === 0) {
            actList.innerHTML = `<div class="text-center text-muted py-3">No activity logs recorded.</div>`;
        } else {
            actList.innerHTML = stats.recent_activities.map(log => `
                <div class="custom-list-item">
                    <div class="d-flex justify-content-between">
                        <strong class="text-primary">${log.action}</strong>
                        <small class="text-muted">${new Date(log.created_at).toLocaleTimeString()}</small>
                    </div>
                    <p class="mb-0 text-secondary" style="font-size:0.85rem;">
                        ${log.details || ""} - by <em>${log.user ? log.user.full_name : 'System'}</em>
                    </p>
                </div>
            `).join("");
        }
        
        // Render Bookings queues if role warrants it
        const role = currentUser.role;
        if(role === "Admin" || role === "Asset Manager" || role === "Department Head") {
            const bookingList = document.getElementById("dashboard-bookings-list");
            document.getElementById("dashboard-bookings-count").innerText = stats.bookings_pending.length;
            
            if(stats.bookings_pending.length === 0) {
                bookingList.innerHTML = `<div class="text-center text-muted py-3">No resource bookings pending actions.</div>`;
            } else {
                bookingList.innerHTML = stats.bookings_pending.map(b => `
                    <div class="custom-list-item">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <strong class="text-gradient">${b.resource.name}</strong>
                            <small class="text-muted fs-8">${new Date(b.start_time).toLocaleDateString()}</small>
                        </div>
                        <p class="mb-2 text-secondary fs-8">Booked by <strong>${b.booked_by.full_name}</strong>: <em>${b.purpose}</em></p>
                        <div class="d-flex gap-2 justify-content-end">
                            <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="processBookingDecision(${b.id}, false)">Deny</button>
                            <button class="btn btn-sm btn-primary py-0 px-2" onclick="processBookingDecision(${b.id}, true)">Approve</button>
                        </div>
                    </div>
                `).join("");
            }
        }
        
        // Render Analytics Distributions Charts
        loadDistributionCharts();
        
    } catch (e) {}
}

async function loadDistributionCharts() {
    try {
        const catData = await request(`${API_BASE}/dashboard/charts/category-distribution`, {
            method: "GET",
            headers: getHeaders()
        });
        
        const statusData = await request(`${API_BASE}/dashboard/charts/status-distribution`, {
            method: "GET",
            headers: getHeaders()
        });
        
        // Cleanup existing chart objects
        if (charts.cats) charts.cats.destroy();
        if (charts.status) charts.status.destroy();
        
        // 1. Categories distribution bar chart
        const ctxCat = document.getElementById("chart-categories").getContext("2d");
        charts.cats = new Chart(ctxCat, {
            type: 'bar',
            data: {
                labels: catData.map(c => c.label),
                datasets: [{
                    label: 'Asset Count',
                    data: catData.map(c => c.value),
                    backgroundColor: 'rgba(13, 110, 253, 0.65)',
                    borderColor: '#0d6efd',
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                    x: { grid: { display: false } }
                }
            }
        });
        
        // 2. Status distribution polarArea/doughnut dynamic chart
        const ctxStatus = document.getElementById("chart-status").getContext("2d");
        charts.status = new Chart(ctxStatus, {
            type: 'doughnut',
            data: {
                labels: statusData.map(s => s.label),
                datasets: [{
                    data: statusData.map(s => s.value),
                    backgroundColor: [
                        '#198754', // Available
                        '#0d6efd', // Allocated
                        '#ffc107', // Under Maintenance
                        '#dc3545'  // Disposed
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    } catch(e) {}
}

async function processBookingDecision(bookingId, approve) {
    try {
        await request(`${API_BASE}/bookings/${bookingId}/decision?approve=${approve}`, {
            method: "PUT",
            headers: getHeaders()
        });
        showToast(approve ? "Booking application approved!" : "Booking request rejected.", approve ? "success" : "warning");
        loadDashboard();
    } catch(e) {}
}

/* ================= VIEW 2: DEPARTMENTS WORLD ================= */
async function loadDepartments() {
    try {
        const depts = await request(`${API_BASE}/departments/`, {
            method: "GET",
            headers: getHeaders()
        });
        
        const tbody = document.querySelector("#table-departments tbody");
        tbody.innerHTML = depts.map(d => `
            <tr class="fade-in-section">
                <td>${d.id}</td>
                <td><span class="badge bg-secondary">${d.code}</span></td>
                <td class="fw-semibold">${d.name}</td>
                <td>${d.manager ? d.manager.full_name : '<span class="text-muted">Unmanaged</span>'}</td>
                <td><span class="badge bg-light text-dark border">Static Query</span></td>
                <td class="text-end text-admin-action" style="display:${currentUser.role === 'Admin' ? 'table-cell' : 'none'};">
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteDepartment(${d.id})"><i class="bi-trash"></i></button>
                </td>
            </tr>
        `).join("");
    } catch (e) {}
}

function openCreateDepartmentModal() {
    // Fetch users of department head role for dropdown mapping
    const selectMgr = document.getElementById("dept-form-manager");
    fetch(`${API_BASE}/employees/`, { headers: getHeaders() })
        .then(res => res.json())
        .then(users => {
            selectMgr.innerHTML = '<option value="0">No Manager Assigned</option>' + 
                users.map(u => `<option value="${u.id}">${u.full_name} (${u.role})</option>`).join("");
            const modal = new bootstrap.Modal(document.getElementById("modal-create-dept"));
            modal.show();
        });
}

async function submitCreateDeptForm(e) {
    e.preventDefault();
    const name = document.getElementById("dept-form-name").value;
    const code = document.getElementById("dept-form-code").value;
    const managerIdVal = parseInt(document.getElementById("dept-form-manager").value);
    const manager_id = managerIdVal === 0 ? null : managerIdVal;
    
    try {
        await request(`${API_BASE}/departments/`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ name, code, manager_id })
        });
        showToast("Created department successfully!", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-create-dept")).hide();
        loadDepartments();
    } catch(err) {}
}

async function deleteDepartment(id) {
    if(!confirm("Are you sure you want to delete this department?")) return;
    try {
        await request(`${API_BASE}/departments/${id}`, {
            method: "DELETE",
            headers: getHeaders()
        });
        showToast("Department deleted successfully", "success");
        loadDepartments();
    } catch(e) {}
}

/* ================= VIEW 3: STAFF DIRECTORY ================= */
async function loadEmployees() {
    // Populate departments filter dropdown once
    const filterDept = document.getElementById("filter-emp-dept");
    if (filterDept.options.length <= 1) {
        const depts = await request(`${API_BASE}/departments/`, { method: "GET", headers: getHeaders() });
        filterDept.innerHTML = '<option value="">All Departments</option>' +
            depts.map(d => `<option value="${d.id}">${d.name}</option>`).join("");
    }
    
    const searchVal = document.getElementById("search-employees").value;
    const deptVal = document.getElementById("filter-emp-dept").value;
    
    let url = `${API_BASE}/employees/?limit=50`;
    if(searchVal) url += `&search=${encodeURIComponent(searchVal)}`;
    if(deptVal) url += `&department_id=${deptVal}`;
    
    try {
        const employees = await request(url, {
            method: "GET",
            headers: getHeaders()
        });
        
        const tbody = document.querySelector("#table-employees tbody");
        tbody.innerHTML = employees.map(emp => `
            <tr class="fade-in-section">
                <td>${emp.id}</td>
                <td><strong>${emp.full_name}</strong></td>
                <td>${emp.email}</td>
                <td><span class="badge bg-secondary bg-opacity-10 text-secondary">${emp.role}</span></td>
                <td>${emp.department_id ? `<span class="fw-semibold">${emp.department_id}</span>` : '<span class="text-muted">General Pool</span>'}</td>
                <td>
                    <span class="badge bg-${emp.is_active ? 'success' : 'danger'} bg-opacity-10 text-${emp.is_active ? 'success' : 'danger'}">
                        ${emp.is_active ? 'Active' : 'Deactivated'}
                    </span>
                </td>
                <td class="text-end text-admin-action" style="display:${currentUser.role === 'Admin' ? 'table-cell' : 'none'};">
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="openEditEmployeeModal(${emp.id})"><i class="bi-pencil"></i></button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteEmployee(${emp.id})"><i class="bi-trash"></i></button>
                </td>
            </tr>
        `).join("");
    } catch (e) {}
}

async function deleteEmployee(id) {
    if(!confirm("Wipe this employee profile? All allocations histories will remain logged.")) return;
    try {
        await request(`${API_BASE}/employees/${id}`, {
            method: "DELETE",
            headers: getHeaders()
        });
        showToast("Employee account purged from directories.", "success");
        loadEmployees();
    } catch(e) {}
}

/* ================= VIEW 4: ASSETS CLASSIFICATION ================= */
async function loadCategories() {
    try {
        const cats = await request(`${API_BASE}/categories/`, {
            method: "GET",
            headers: getHeaders()
        });
        
        const tbody = document.querySelector("#table-categories tbody");
        tbody.innerHTML = cats.map(c => `
            <tr class="fade-in-section">
                <td>${c.id}</td>
                <td><span class="badge bg-info bg-opacity-25 text-info">${c.code}</span></td>
                <td class="fw-bold">${c.name}</td>
                <td>${c.description || '<span class="text-muted">No description</span>'}</td>
                <td class="text-end text-mgr-action" style="display:${(currentUser.role === 'Admin' || currentUser.role === 'Asset Manager') ? 'table-cell' : 'none'};">
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteCategory(${c.id})"><i class="bi-trash"></i></button>
                </td>
            </tr>
        `).join("");
    } catch (e) {}
}

function openCreateCategoryModal() {
    const modal = new bootstrap.Modal(document.getElementById("modal-create-cat"));
    modal.show();
}

async function submitCreateCatForm(e) {
    e.preventDefault();
    const name = document.getElementById("cat-form-name").value;
    const code = document.getElementById("cat-form-code").value;
    const description = document.getElementById("cat-form-desc").value;
    
    try {
        await request(`${API_BASE}/categories/`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ name, code, description })
        });
        showToast("New asset category defined!", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-create-cat")).hide();
        loadCategories();
    } catch(err) {}
}

async function deleteCategory(id) {
    if(!confirm("Are you sure? This action is irrevocable if empty.")) return;
    try {
        await request(`${API_BASE}/categories/${id}`, {
            method: "DELETE",
            headers: getHeaders()
        });
        showToast("Category definition purged.", "success");
        loadCategories();
    } catch(e) {}
}

/* ================= VIEW 5: ASSET RECORDS INVENTORIES ================= */
async function loadAssets() {
    // Populate classifications options list
    const filterCat = document.getElementById("filter-asset-cat");
    if(filterCat.options.length <= 1) {
        const cats = await request(`${API_BASE}/categories/`, { method: "GET", headers: getHeaders() });
        filterCat.innerHTML = '<option value="">All Categories</option>' +
            cats.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    }
    
    const searchVal = document.getElementById("search-assets").value;
    const catVal = document.getElementById("filter-asset-cat").value;
    const statusVal = document.getElementById("filter-asset-status").value;
    
    let url = `${API_BASE}/assets/?limit=50`;
    if(searchVal) url += `&search=${encodeURIComponent(searchVal)}`;
    if(catVal) url += `&category_id=${catVal}`;
    if(statusVal) url += `&status=${statusVal}`;
    
    try {
        const assets = await request(url, { method: "GET", headers: getHeaders() });
        const tbody = document.querySelector("#table-assets tbody");
        
        tbody.innerHTML = assets.map(a => {
            const role = currentUser.role;
            const isManager = role === "Admin" || role === "Asset Manager";
            const dateStr = new Date(a.purchase_date).toLocaleDateString();
            
            // Workflow Actions depending on active state
            let workflowHTML = "";
            
            if(a.status === "Available" && isManager) {
                workflowHTML = `
                    <button class="btn btn-xs btn-outline-success py-1 px-2 mb-1" onclick="openAllocateAssetModal(${a.id}, '${a.name}')"><i class="bi-person-plus me-1"></i>Allocate</button>
                    <button class="btn btn-xs btn-outline-warning py-1 px-2" onclick="openMaintAssetModal(${a.id}, '${a.name}')"><i class="bi-wrench me-1"></i>Repair</button>
                `;
            } else if (a.status === "Allocated") {
                workflowHTML = `
                    <button class="btn btn-xs btn-outline-info py-1 px-2" onclick="openTransferAssetModal(${a.id}, '${a.name}')"><i class="bi-arrow-left-right me-1"></i>Request Transfer</button>
                `;
            } else if (a.status === "Under Maintenance" && isManager) {
                workflowHTML = `<span class="text-warning fw-semibold fs-8"><i class="bi-hourglass-split me-1"></i>Being Repaired</span>`;
            }
            
            // Add audit / delete items
            const auditBtn = isManager ? `<button class="btn btn-link text-decoration-none text-secondary p-0 me-2" title="Manual audit verify" onclick="openAuditAssetModal(${a.id}, '${a.name}')"><i class="bi-patch-check"></i></button>` : "";
            const deleteBtn = isManager ? `<button class="btn btn-link text-decoration-none text-danger p-0" title="Retire Asset" onclick="retireAsset(${a.id})"><i class="bi-trash"></i></button>` : "";
            
            return `
                <tr class="fade-in-section">
                    <td><strong class="text-primary">${a.asset_tag}</strong></td>
                    <td class="fw-semibold">${a.name}</td>
                    <td><span class="badge bg-light text-dark border">${a.category.name}</span></td>
                    <td class="fs-8">Mod: ${a.model || 'N/A'}<br>S/N: ${a.serial_number || 'N/A'}</td>
                    <td>${dateStr}<br><strong>$${a.purchase_cost.toLocaleString()}</strong></td>
                    <td>
                        <span class="badge-status status-${a.status.toLowerCase().replace(' ', '')}">
                            ${a.status}
                        </span>
                    </td>
                    <td class="fs-8">${a.current_location || '<span class="text-muted">Unset</span>'}</td>
                    <td class="text-end">
                        <div class="d-flex flex-column align-items-end mb-2">
                            ${workflowHTML}
                        </div>
                        <div class="d-flex justify-content-end">
                            ${auditBtn}
                            ${deleteBtn}
                        </div>
                    </td>
                </tr>
            `;
        }).join("");
    } catch(e) {}
}

async function retireAsset(id) {
    if(!confirm("Move asset state to Disposed? This will delete the catalog index if acceptable.")) return;
    try {
        await request(`${API_BASE}/assets/${id}`, {
            method: "DELETE",
            headers: getHeaders()
        });
        showToast("Asset registration retired.", "success");
        loadAssets();
    } catch (e) {}
}

// Open modals loaders
async function openCreateAssetModal() {
    const listCat = document.getElementById("asset-form-cat");
    const cats = await request(`${API_BASE}/categories/`, { method: "GET", headers: getHeaders() });
    listCat.innerHTML = cats.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    
    document.getElementById("asset-form-date").value = new Date().toISOString().substring(0, 10);
    const modal = new bootstrap.Modal(document.getElementById("modal-create-asset"));
    modal.show();
}

async function submitCreateAssetForm(e) {
    e.preventDefault();
    const name = document.getElementById("asset-form-name").value;
    const asset_tag = document.getElementById("asset-form-tag").value;
    const category_id = parseInt(document.getElementById("asset-form-cat").value);
    const model = document.getElementById("asset-form-model").value;
    const serial_number = document.getElementById("asset-form-serial").value;
    const purchase_date = new Date(document.getElementById("asset-form-date").value).toISOString();
    const purchase_cost = parseFloat(document.getElementById("asset-form-cost").value);
    const current_location = document.getElementById("asset-form-loc").value;
    
    try {
        await request(`${API_BASE}/assets/`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ name, asset_tag, category_id, model, serial_number, purchase_date, purchase_cost, current_location })
        });
        showToast("Asset registered into system catalog!", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-create-asset")).hide();
        loadAssets();
    } catch(err) {}
}

/* ================= VIEW 6: ASSET ALLOCATIONS SIGN-OUT ================= */
async function loadAllocations() {
    const statusVal = document.getElementById("filter-allocations").value;
    let url = `${API_BASE}/allocations/`;
    if (statusVal) url += `?status=${statusVal}`;
    
    try {
        const allocations = await request(url, { method: "GET", headers: getHeaders() });
        const tbody = document.querySelector("#table-allocations tbody");
        const isManager = currentUser.role === "Admin" || currentUser.role === "Asset Manager";
        
        tbody.innerHTML = allocations.map(a => {
            const dateAlloc = new Date(a.allocation_date).toLocaleDateString();
            const dateDue = a.return_due_date ? new Date(a.return_due_date).toLocaleDateString() : '<span class="text-muted">Open Ended</span>';
            const dateRet = a.return_date ? new Date(a.return_date).toLocaleDateString() : '';
            
            const assigneeName = a.allocated_to ? a.allocated_to.full_name : (a.allocated_dept ? `${a.allocated_dept.name} Division` : 'Global Store');
            const returnButton = (a.status === "Active" && isManager) ? 
                `<button class="btn btn-sm btn-outline-success py-1 px-3" onclick="processReturnAsset(${a.id})"><i class="bi-check-all me-1"></i>Process return</button>` : '';
                
            return `
                <tr class="fade-in-section">
                    <td>${a.id}</td>
                    <td><strong>${a.asset.name}</strong><br><small class="text-secondary">${a.asset.asset_tag}</small></td>
                    <td class="fw-semibold">${assigneeName}</td>
                    <td><small class="text-muted">Staff ID ${a.allocated_by_id}</small></td>
                    <td>${dateAlloc}</td>
                    <td>${a.status === 'Active' ? dateDue : `Ret: ${dateRet}`}</td>
                    <td>
                        <span class="badge bg-${a.status === 'Active' ? 'primary' : 'secondary'}">
                            ${a.status}
                        </span>
                    </td>
                    <td class="text-end">${returnButton}</td>
                </tr>
            `;
        }).join("");
    } catch (e) {}
}

async function openAllocateAssetModal(assetId, name) {
    document.getElementById("alloc-form-asset-id").value = assetId;
    document.getElementById("alloc-lbl-asset-name").innerText = name;
    
    // Fetch users & depts list for selections option mapping
    const userSel = document.getElementById("alloc-form-user");
    const deptSel = document.getElementById("alloc-form-dept");
    
    const users = await request(`${API_BASE}/employees/`, { headers: getHeaders() });
    const depts = await request(`${API_BASE}/departments/`, { headers: getHeaders() });
    
    userSel.innerHTML = users.map(u => `<option value="${u.id}">${u.full_name} (${u.email})</option>`).join("");
    deptSel.innerHTML = depts.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join("");
    
    // Set default due returns to 6 months
    const dateDue = new Date();
    dateDue.setMonth(dateDue.getMonth() + 6);
    document.getElementById("alloc-form-due").value = dateDue.toISOString().substring(0, 10);
    
    const modal = new bootstrap.Modal(document.getElementById("modal-allocate-asset"));
    modal.show();
}

function toggleAllocFormFields() {
    const isUser = document.getElementById("allocTypeUser").checked;
    document.getElementById("alloc-user-select-block").style.display = isUser ? "block" : "none";
    document.getElementById("alloc-dept-select-block").style.display = isUser ? "none" : "block";
}

async function submitAllocateAssetForm(e) {
    e.preventDefault();
    const asset_id = parseInt(document.getElementById("alloc-form-asset-id").value);
    const return_due_date = new Date(document.getElementById("alloc-form-due").value).toISOString();
    
    const isUser = document.getElementById("allocTypeUser").checked;
    const allocated_to_id = isUser ? parseInt(document.getElementById("alloc-form-user").value) : null;
    const allocated_dept_id = !isUser ? parseInt(document.getElementById("alloc-form-dept").value) : null;
    
    try {
        await request(`${API_BASE}/allocations/`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ asset_id, allocated_to_id, allocated_dept_id, return_due_date })
        });
        showToast("Asset successfully allocated!", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-allocate-asset")).hide();
        loadAssets();
    } catch(err) {}
}

async function processReturnAsset(id) {
    if(!confirm("Process Return check-in for this asset?")) return;
    try {
        await request(`${API_BASE}/allocations/${id}/return`, {
            method: "POST",
            headers: getHeaders()
        });
        showToast("Asset returned back to available pool.", "success");
        loadAllocations();
    } catch(e) {}
}

/* ================= VIEW 7: TRANSFERS FLOWS ================= */
async function loadTransfers() {
    try {
        const trans = await request(`${API_BASE}/transfers/`, { method: "GET", headers: getHeaders() });
        const tbody = document.querySelector("#table-transfers tbody");
        
        tbody.innerHTML = trans.map(t => {
            const dateStr = new Date(t.created_at).toLocaleDateString();
            
            // Decides actions block
            let actionsHTML = "";
            const canApprove = (currentUser.role === "Admin" || currentUser.role === "Asset Manager" || currentUser.role === "Department Head");
            if (t.status === "Pending") {
                if (canApprove) {
                    actionsHTML = `
                        <button class="btn btn-sm btn-outline-danger py-0 px-2 me-1" onclick="processTransfer(${t.id}, 'Rejected')">Reject</button>
                        <button class="btn btn-sm btn-success py-0 px-2" onclick="processTransfer(${t.id}, 'Approved')">Approve</button>
                    `;
                } else {
                    actionsHTML = `<span class="text-muted fs-8">Awaiting manager</span>`;
                }
            } else {
                actionsHTML = `<small class="text-secondary">Handled by User ID ${t.approved_by_id}</small>`;
            }
            
            return `
                <tr class="fade-in-section">
                    <td>${t.id}</td>
                    <td><strong>${t.asset.name}</strong><br><small class="text-secondary">${t.asset.asset_tag}</small></td>
                    <td>${t.requested_by.full_name}</td>
                    <td>${t.source_dept ? `<span class="badge border text-dark">${t.source_dept.code}</span>` : 'N/A'}</td>
                    <td><span class="badge bg-primary">${t.target_dept.code}</span></td>
                    <td class="fs-8">"${t.reason}"</td>
                    <td>
                        <span class="badge bg-${t.status === 'Pending' ? 'warning text-dark' : (t.status === 'Approved' ? 'success' : 'danger')}">
                            ${t.status}
                        </span>
                    </td>
                    <td>${t.approved_by ? t.approved_by.full_name : ''}</td>
                    <td class="text-end">${actionsHTML}</td>
                </tr>
            `;
        }).join("");
    } catch(e) {}
}

async function openTransferAssetModal(assetId, name) {
    document.getElementById("trans-form-asset-id").value = assetId;
    document.getElementById("trans-lbl-asset-name").innerText = name;
    
    // Load departments
    const deptSel = document.getElementById("trans-form-target-dept");
    const depts = await request(`${API_BASE}/departments/`, { method: "GET", headers: getHeaders() });
    deptSel.innerHTML = depts.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join("");
    
    const modal = new bootstrap.Modal(document.getElementById("modal-transfer-asset"));
    modal.show();
}

async function submitTransferAssetForm(e) {
    e.preventDefault();
    const asset_id = parseInt(document.getElementById("trans-form-asset-id").value);
    const target_dept_id = parseInt(document.getElementById("trans-form-target-dept").value);
    const reason = document.getElementById("trans-form-reason").value;
    
    try {
        await request(`${API_BASE}/transfers/`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ asset_id, target_dept_id, reason })
        });
        showToast("Transfer requested in queue", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-transfer-asset")).hide();
        loadAssets();
    } catch(e) {}
}

async function processTransfer(transferId, status) {
    const comments = prompt("Decision notes (Optional):") || "";
    try {
        await request(`${API_BASE}/transfers/${transferId}`, {
            method: "PUT",
            headers: getHeaders(),
            body: JSON.stringify({ status, comments })
        });
        showToast(`Transfer decision set to: ${status}`, "success");
        loadTransfers();
    } catch(e) {}
}

/* ================= VIEW 8: BOOKABLE RESOURCES ================= */
async function loadBookings() {
    try {
        // Load resources cards
        const resources = await request(`${API_BASE}/bookings/resources`, { method: "GET", headers: getHeaders() });
        const grid = document.getElementById("bookings-resource-grid");
        
        grid.innerHTML = resources.map(r => `
            <div class="col-md-4">
                <div class="card glass-panel p-4 h-100 border-top border-3 border-${r.status === 'Available' ? 'success' : 'danger'}">
                    <span class="badge bg-secondary align-self-start mb-2">${r.type}</span>
                    <h6 class="fw-bold">${r.name}</h6>
                    <p class="text-secondary fs-8 mb-3">${r.description || 'No inventory notes.'}</p>
                    <div class="d-flex justify-content-between align-items-center mt-auto">
                        <span class="fs-8 fw-semibold text-${r.status === 'Available' ? 'success' : 'danger'}">
                            <i class="bi bi-circle-fill me-1" style="font-size:0.5rem;"></i>${r.status}
                        </span>
                        <button class="btn btn-sm btn-primary" onclick="openBookResourceModal(${r.id}, '${r.name}')" ${r.status !== 'Available' ? 'disabled' : ''}>Reserve</button>
                    </div>
                </div>
            </div>
        `).join("");
        
        // Load Bookings list
        const bookings = await request(`${API_BASE}/bookings/`, { method: "GET", headers: getHeaders() });
        const tbody = document.querySelector("#table-bookings tbody");
        
        tbody.innerHTML = bookings.map(b => {
            const start = new Date(b.start_time).toLocaleString();
            const end = new Date(b.end_time).toLocaleString();
            const sameUser = currentUser.id === b.booked_by_id;
            const isManager = currentUser.role === "Admin" || currentUser.role === "Asset Manager" || currentUser.role === "Department Head";
            
            let actionHTML = "";
            if (b.status === "Pending") {
                if (isManager) {
                    actionHTML = `
                        <button class="btn btn-sm btn-outline-danger py-0 px-2 me-1" onclick="processBookingDecision(${b.id}, false)">Deny</button>
                        <button class="btn btn-sm btn-success py-0 px-2" onclick="processBookingDecision(${b.id}, true)">Approve</button>
                    `;
                } else if(sameUser) {
                    actionHTML = `<button class="btn btn-sm btn-outline-secondary py-0 px-2" disabled>Pending Review</button>`;
                }
            } else {
                actionHTML = `<span class="badge bg-light text-dark border">${b.status}</span>`;
            }
            
            return `
                <tr class="fade-in-section">
                    <td>${b.id}</td>
                    <td class="fw-bold">${b.resource.name}</td>
                    <td>${b.booked_by.full_name}</td>
                    <td class="fs-8">${start}<br>to <strong>${end}</strong></td>
                    <td class="fs-8">"${b.purpose}"</td>
                    <td>
                        <span class="badge bg-${b.status === 'Pending' ? 'warning text-dark' : (b.status === 'Approved' ? 'success' : 'danger')}">
                            ${b.status}
                        </span>
                    </td>
                    <td class="text-end">${actionHTML}</td>
                </tr>
            `;
        }).join("");
    } catch(e) {}
}

function openCreateResourceModal() {
    const modal = new bootstrap.Modal(document.getElementById("modal-create-res"));
    modal.show();
}

async function submitCreateResForm(e) {
    e.preventDefault();
    const name = document.getElementById("res-form-name").value;
    const type = document.getElementById("res-form-type").value;
    const description = document.getElementById("res-form-desc").value;
    
    try {
        await request(`${API_BASE}/bookings/resources`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ name, type, description, status: "Available" })
        });
        showToast("Bookable resource added to index", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-create-res")).hide();
        loadBookings();
    } catch(err) {}
}

function openBookResourceModal(id, name) {
    document.getElementById("book-form-res-id").value = id;
    document.getElementById("book-lbl-res-name").innerText = name;
    
    // Set default time to today in 1 hour increments
    const start = new Date();
    start.setHours(start.getHours() + 1, 0, 0, 0);
    const end = new Date(start);
    end.setHours(end.getHours() + 2);
    
    document.getElementById("book-form-start").value = new Date(start.getTime() - start.getTimezoneOffset()*60000).toISOString().substring(0, 16);
    document.getElementById("book-form-end").value = new Date(end.getTime() - end.getTimezoneOffset()*60000).toISOString().substring(0, 16);
    
    const modal = new bootstrap.Modal(document.getElementById("modal-book-resource"));
    modal.show();
}

async function submitBookResourceForm(e) {
    e.preventDefault();
    const resource_id = parseInt(document.getElementById("book-form-res-id").value);
    const start_time = new Date(document.getElementById("book-form-start").value).toISOString();
    const end_time = new Date(document.getElementById("book-form-end").value).toISOString();
    const purpose = document.getElementById("book-form-purpose").value;
    
    try {
        await request(`${API_BASE}/bookings/`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ resource_id, start_time, end_time, purpose })
        });
        showToast("Booking application submitted. Subject to manager review.", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-book-resource")).hide();
        loadBookings();
    } catch(err) {}
}

/* ================= VIEW 9: MAINTENANCE TICKETS ================= */
async function loadMaintenance() {
    try {
        const records = await request(`${API_BASE}/maintenance/`, { method: "GET", headers: getHeaders() });
        const tbody = document.querySelector("#table-maintenance tbody");
        const isManager = currentUser.role === "Admin" || currentUser.role === "Asset Manager";
        
        tbody.innerHTML = records.map(r => {
            const dateSched = new Date(r.scheduled_date).toLocaleDateString();
            const dateComp = r.completion_date ? new Date(r.completion_date).toLocaleDateString() : '';
            
            let actionsHTML = "";
            if(r.status === 'Scheduled' && isManager) {
                actionsHTML = `<button class="btn btn-sm btn-outline-warning py-1 px-3" onclick="processStartMaint(${r.id})"><i class="bi-play"></i> Start repairs</button>`;
            } else if (r.status === 'In Progress' && isManager) {
                actionsHTML = `<button class="btn btn-sm btn-success py-1 px-3" onclick="openCompleteMaintModal(${r.id})"><i class="bi-check2-circle"></i> Resolve Ticket</button>`;
            }
            
            return `
                <tr class="fade-in-section">
                    <td>${r.id}</td>
                    <td><strong>${r.asset.name}</strong><br><small class="text-secondary">${r.asset.asset_tag}</small></td>
                    <td><span class="badge bg-light text-dark border">${r.maintenance_type}</span></td>
                    <td>${dateSched}</td>
                    <td>${dateComp}</td>
                    <td><strong>$${r.cost.toFixed(2)}</strong></td>
                    <td>
                        <span class="badge bg-${r.status === 'Completed' ? 'success' : (r.status === 'Cancelled' ? 'danger' : 'warning text-dark')}">
                            ${r.status}
                        </span>
                    </td>
                    <td class="text-end">${actionsHTML}</td>
                </tr>
            `;
        }).join("");
    } catch(e) {}
}

async function openMaintAssetModal(assetId, name) {
    document.getElementById("maint-form-asset-id").value = assetId;
    document.getElementById("maint-lbl-asset-name").innerText = name;
    
    const sched = new Date();
    sched.setHours(sched.getHours() + 24);
    document.getElementById("maint-form-date").value = new Date(sched.getTime() - sched.getTimezoneOffset()*60000).toISOString().substring(0, 16);
    
    const modal = new bootstrap.Modal(document.getElementById("modal-maint-asset"));
    modal.show();
}

async function submitMaintAssetForm(e) {
    e.preventDefault();
    const asset_id = parseInt(document.getElementById("maint-form-asset-id").value);
    const maintenance_type = document.getElementById("maint-form-type").value;
    const description = document.getElementById("maint-form-desc").value;
    const scheduled_date = new Date(document.getElementById("maint-form-date").value).toISOString();
    
    try {
        await request(`${API_BASE}/maintenance/`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ asset_id, maintenance_type, description, scheduled_date })
        });
        showToast("Maintenance ticket queued successfully.", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-maint-asset")).hide();
        loadAssets();
    } catch(err) {}
}

async function processStartMaint(id) {
    try {
        await request(`${API_BASE}/maintenance/${id}/start`, { method: "PUT", headers: getHeaders() });
        showToast("Repairs ticket set dynamically: In Progress.", "success");
        loadMaintenance();
    } catch(e) {}
}

function openCompleteMaintModal(id) {
    document.getElementById("comp-form-rec-id").value = id;
    const modal = new bootstrap.Modal(document.getElementById("modal-complete-maint"));
    modal.show();
}

async function submitCompleteMaintForm(e) {
    e.preventDefault();
    const id = parseInt(document.getElementById("comp-form-rec-id").value);
    const statusVal = document.getElementById("comp-form-status").value;
    const costVal = parseFloat(document.getElementById("comp-form-cost").value);
    const notesVal = document.getElementById("comp-form-notes").value;
    
    try {
         await request(`${API_BASE}/maintenance/${id}/complete`, {
             method: "PUT",
             headers: getHeaders(),
             body: JSON.stringify({ completion_date: new Date().toISOString(), cost: costVal, notes: notesVal, status: statusVal })
         });
         showToast("Maintenance log closed", "success");
         bootstrap.Modal.getInstance(document.getElementById("modal-complete-maint")).hide();
         loadMaintenance();
    } catch(e) {}
}

/* ================= VIEW 10: ASSETS AUDITS ================= */
async function loadAudits() {
    try {
        const records = await request(`${API_BASE}/audits/`, { method: "GET", headers: getHeaders() });
        const tbody = document.querySelector("#table-audits tbody");
        
        tbody.innerHTML = records.map(r => `
            <tr class="fade-in-section">
                <td>${r.id}</td>
                <td><strong>${r.asset.name}</strong><br><small class="text-secondary">${r.asset.asset_tag}</small></td>
                <td><span class="badge border text-dark">${r.condition}</span></td>
                <td><span class="badge bg-${r.status === 'Verified' ? 'success' : 'danger'}">${r.status}</span></td>
                <td>${r.auditor.full_name}</td>
                <td>${new Date(r.audit_date).toLocaleDateString()}</td>
                <td style="font-size:0.85rem;" class="text-secondary">"${r.notes || ''}"</td>
            </tr>
        `).join("");
    } catch(e) {}
}

function openAuditAssetModal(id, name) {
    document.getElementById("audit-form-asset-id").value = id;
    document.getElementById("audit-lbl-asset-name").innerText = name;
    document.getElementById("audit-form-notes").value = "";
    
    const modal = new bootstrap.Modal(document.getElementById("modal-audit-asset"));
    modal.show();
}

async function submitAuditAssetForm(e) {
    e.preventDefault();
    const asset_id = parseInt(document.getElementById("audit-form-asset-id").value);
    const condition = document.getElementById("audit-form-cond").value;
    const status = document.getElementById("audit-form-status").value;
    const notes = document.getElementById("audit-form-notes").value;
    
    try {
         await request(`${API_BASE}/audits/`, {
             method: "POST",
             headers: getHeaders(),
             body: JSON.stringify({ asset_id, condition, status, notes })
         });
         showToast("Physical audit cataloged.", "success");
         bootstrap.Modal.getInstance(document.getElementById("modal-audit-asset")).hide();
         loadAssets();
    } catch(e) {}
}

/* ================= VIEW 11: REPORTS EXPORT ================= */
async function loadReportsSelectors() {
    const catsSelect = document.getElementById("report-filter-cat");
    if(catsSelect.options.length <= 1) {
        const cats = await request(`${API_BASE}/categories/`, { method: "GET", headers: getHeaders() });
        catsSelect.innerHTML = '<option value="">All Categories</option>' +
            cats.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    }
}

function triggerReportExport(format) {
    const cat = document.getElementById("report-filter-cat").value;
    const status = document.getElementById("report-filter-status").value;
    
    let url = `${API_BASE}/reports/export/${format}?`;
    if(cat) url += `category_id=${cat}&`;
    if(status) url += `status=${status}&`;
    
    // Build direct credentials attachment header link triggering download directly
    const token = localStorage.getItem("token");
    url += `token=${token}`;
    
    // Standard trigger direct download in user browser frame window
    // Since we require JWT authentication, report endpoints check either token parameter or standard Bearer header.
    // Let's modify our backend report download endpoints to parse direct tokens if passed in query!
    window.location.href = url;
}

/* ================= VIEW 12: MASTER SECURITY AUDIT LOGS ================= */
async function loadLogs() {
    try {
        const logs = await request(`${API_BASE}/system/logs?limit=100`, { method: "GET", headers: getHeaders() });
        const tbody = document.querySelector("#table-logs tbody");
        
        tbody.innerHTML = logs.map(l => {
            const time = new Date(l.created_at).toLocaleString();
            return `
                <tr class="fade-in-section">
                    <td class="fs-8">${time}</td>
                    <td class="fw-semibold">${l.user ? l.user.full_name : 'System/Anonymous'}</td>
                    <td><span class="text-primary fw-medium">${l.action}</span></td>
                    <td><small class="text-secondary">${l.category}</small></td>
                    <td class="fs-8">"${l.details || ''}"</td>
                    <td class="fs-8">${l.ip_address || ''}</td>
                </tr>
            `;
        }).join("");
    } catch(e) {}
}

/* ================= SYSTEM SYSTEM NOTIFICATION FEEDS ================= */
async function fetchNotifications() {
    try {
        const list = await request(`${API_BASE}/system/notifications`, { method: "GET", headers: getHeaders() });
        const unreadCount = list.filter(n => !n.is_read).length;
        
        const countBadge = document.getElementById("notif-count");
        if(unreadCount > 0) {
            countBadge.innerText = unreadCount;
            countBadge.style.display = "inline-block";
        } else {
            countBadge.style.display = "none";
        }
        
        const listEl = document.getElementById("notification-list");
        
        if (list.length === 0) {
            listEl.innerHTML = `
                <li><h6 class="dropdown-header text-primary border-bottom pb-2">User Notifications</h6></li>
                <li class="p-3 text-center text-muted fw-light">No new alerts.</li>
            `;
            return;
        }
        
        let html = `<li><h6 class="dropdown-header text-primary border-bottom pb-2">User Notifications</h6></li>`;
        html += list.map(n => `
            <li class="custom-list-item px-3 py-2 ${n.is_read ? 'opacity-75' : 'bg-light bg-opacity-10'}" style="cursor:pointer;" onclick="markNotificationRead(${n.id})">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <strong class="fs-8">${n.title}</strong>
                    <small class="text-secondary" style="font-size:0.65rem;">${new Date(n.created_at).toLocaleTimeString()}</small>
                </div>
                <p class="mb-0 text-secondary" style="font-size:0.75rem;">${n.message}</p>
            </li>
        `).join("");
        
        listEl.innerHTML = html;
    } catch(e) {}
}

async function markNotificationRead(id) {
    try {
        await request(`${API_BASE}/system/notifications/${id}/read`, { method: "PUT", headers: getHeaders() });
        fetchNotifications();
    } catch(e) {}
}

/* ================= VIEW 13: SYSTEM CONTROL PANEL & ADMIN CONTROLS ================= */
async function loadSystemSettings() {
    try {
        const settings = await request(`${API_BASE}/system/settings`, {
            method: "GET",
            headers: getHeaders()
        });
        
        settings.forEach(s => {
            if (s.key === "company_name") document.getElementById("set-company-name").value = s.value;
            if (s.key === "address") document.getElementById("set-address").value = s.value;
            if (s.key === "timezone") document.getElementById("set-timezone").value = s.value;
            if (s.key === "currency") document.getElementById("set-currency").value = s.value;
            if (s.key === "session_timeout_minutes") document.getElementById("set-timeout").value = s.value;
            if (s.key === "password_min_length") document.getElementById("set-limit-pass").value = s.value;
        });
    } catch (e) {}
}

async function submitSystemSettingsForm(e) {
    e.preventDefault();
    const company = document.getElementById("set-company-name").value;
    const address = document.getElementById("set-address").value;
    const timezone = document.getElementById("set-timezone").value;
    const currency = document.getElementById("set-currency").value;
    const timeout = document.getElementById("set-timeout").value;
    const limitPass = document.getElementById("set-limit-pass").value;
    
    try {
        await Promise.all([
            request(`${API_BASE}/system/settings`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ key: "company_name", value: company })
            }),
            request(`${API_BASE}/system/settings`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ key: "address", value: address })
            }),
            request(`${API_BASE}/system/settings`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ key: "timezone", value: timezone })
            }),
            request(`${API_BASE}/system/settings`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ key: "currency", value: currency })
            }),
            request(`${API_BASE}/system/settings`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ key: "session_timeout_minutes", value: timeout })
            }),
            request(`${API_BASE}/system/settings`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ key: "password_min_length", value: limitPass })
            })
        ]);
        
        showToast("System configurations committed successfully!", "success");
        loadSystemSettings();
    } catch(err) {}
}

async function loadLookupOptionsList() {
    const category = document.getElementById("lookup-category-select").value;
    try {
        const options = await request(`${API_BASE}/system/lookup-options?category=${category}`, {
            method: "GET",
            headers: getHeaders()
        });
        
        const tbody = document.querySelector("#table-lookups tbody");
        tbody.innerHTML = options.map(opt => `
            <tr>
                <td>${opt.id}</td>
                <td><span class="badge bg-secondary">${opt.category}</span></td>
                <td><strong>${opt.name}</strong></td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteLookupOption(${opt.id})"><i class="bi-trash"></i></button>
                </td>
            </tr>
        `).join("");
    } catch(e) {}
}

function openAddLookupModal() {
    const category = document.getElementById("lookup-category-select").value;
    document.getElementById("lookup-add-cat-label").value = category;
    document.getElementById("lookup-add-cat-value").value = category;
    document.getElementById("lookup-add-name").value = "";
    
    const modal = new bootstrap.Modal(document.getElementById("modal-add-lookup"));
    modal.show();
}

async function submitAddLookupForm(e) {
    e.preventDefault();
    const category = document.getElementById("lookup-add-cat-value").value;
    const name = document.getElementById("lookup-add-name").value;
    
    try {
        await request(`${API_BASE}/system/lookup-options`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ category, name, value: name, is_active: true })
        });
        showToast("Lookup Option registered successfully!", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-add-lookup")).hide();
        loadLookupOptionsList();
    } catch(err) {}
}

async function deleteLookupOption(id) {
    if (!confirm("Are you sure you want to delete this lookup item option?")) return;
    try {
        await request(`${API_BASE}/system/lookup-options/${id}`, {
            method: "DELETE",
            headers: getHeaders()
        });
        showToast("Lookup option purged.", "success");
        loadLookupOptionsList();
    } catch (e) {}
}

/* ================= EMPLOYEE EDIT MODAL FUNCTIONALITY ================= */
async function openEditEmployeeModal(id) {
    try {
        const depts = await request(`${API_BASE}/departments/`, { method: "GET", headers: getHeaders() });
        const deptSelect = document.getElementById("emp-edit-dept");
        deptSelect.innerHTML = '<option value="0">General Pool (Unassigned)</option>' +
            depts.map(d => `<option value="${d.id}">${d.name}</option>`).join("");
            
        const emp = await request(`${API_BASE}/employees/${id}`, { method: "GET", headers: getHeaders() });
        
        document.getElementById("emp-edit-id").value = emp.id;
        document.getElementById("emp-edit-name").value = emp.full_name;
        document.getElementById("emp-edit-email").value = emp.email;
        document.getElementById("emp-edit-dept").value = emp.department_id || "0";
        document.getElementById("emp-edit-active").checked = emp.is_active;
        document.getElementById("emp-edit-password").value = "";
        
        // Reset role checkboxes
        const checkboxes = document.querySelectorAll(".emp-role-checkbox");
        checkboxes.forEach(chk => chk.checked = false);
        
        // Check current roles
        if (emp.role) {
            const roles = emp.role.split(",").map(r => r.trim());
            roles.forEach(r => {
                if (r === "Employee") document.getElementById("role-chk-employee").checked = true;
                if (r === "Department Head") document.getElementById("role-chk-head").checked = true;
                if (r === "Asset Manager") document.getElementById("role-chk-manager").checked = true;
                if (r === "Admin") document.getElementById("role-chk-admin").checked = true;
            });
        }
        
        const modal = new bootstrap.Modal(document.getElementById("modal-edit-employee"));
        modal.show();
    } catch(e) {}
}

async function submitEditEmployeeForm(e) {
    e.preventDefault();
    const id = document.getElementById("emp-edit-id").value;
    const full_name = document.getElementById("emp-edit-name").value;
    const email = document.getElementById("emp-edit-email").value;
    const deptVal = parseInt(document.getElementById("emp-edit-dept").value);
    const department_id = deptVal === 0 ? 0 : deptVal;
    const is_active = document.getElementById("emp-edit-active").checked;
    
    // Roles list compilation
    const checkboxes = document.querySelectorAll(".emp-role-checkbox");
    const rolesArr = [];
    checkboxes.forEach(chk => {
        if(chk.checked) rolesArr.push(chk.value);
    });
    
    if (rolesArr.length === 0) {
        showToast("Please assign at least one role to the employee profile", "warning");
        return;
    }
    const role = rolesArr.join(",");
    
    const body = {
        full_name,
        email,
        role,
        department_id,
        is_active
    };
    
    const pass = document.getElementById("emp-edit-password").value;
    if (pass) {
        body.password = pass;
    }
    
    try {
        await request(`${API_BASE}/employees/${id}`, {
            method: "PUT",
            headers: getHeaders(),
            body: JSON.stringify(body)
        });
        showToast("Employee profile updated successfully!", "success");
        bootstrap.Modal.getInstance(document.getElementById("modal-edit-employee")).hide();
        loadEmployees();
    } catch(err) {}
}
