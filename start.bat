@echo off
echo ========================================================
echo          Starting AssetFlow ERP System
echo ========================================================
echo.

:: Move to backend directory
cd /d "%~dp0backend"

:: Detect Python executable containing dependencies
if exist "venv\Scripts\python.exe" (
    set PYTHON_EXE=venv\Scripts\python.exe
    goto python_found
)

set PYTHON_EXE=python
py -3.10 -c "import uvicorn" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_EXE=py -3.10
    goto python_found
)

"C:\Users\mpatr\AppData\Local\Programs\Python\Python310\python.exe" -c "import uvicorn" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_EXE="C:\Users\mpatr\AppData\Local\Programs\Python\Python310\python.exe"
    goto python_found
)

:python_found
echo Using Python interpreter: %PYTHON_EXE%

:: Terminate any lingering uvicorn instances on port 8000
echo Checking for active servers...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /f /pid %%a >/nul 2>&1
)

:: Start Uvicorn backend server and redirect outputs to run.log
echo Starting FastAPI application server...
start "AssetFlow Web Server" cmd /k "%PYTHON_EXE% -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: Start Serveo SSH Tunnel for Firebase Hosting link
:: echo Starting persistent secure HTTPS tunnel...
:: start "Serveo HTTPS Tunnel" cmd /c "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:8000 serveo.net"


:: Wait for application server startup
timeout /t 3 /nobreak >nul

:: Open local dashboard in default browser
echo Opening AssetFlow in your default browser...
start http://127.0.0.1:8000

echo.
echo ========================================================
echo AssetFlow is ready! 
echo Dashboard URL: http://127.0.0.1:8000
echo Swagger Docs:  http://127.0.0.1:8000/docs
echo ========================================================
pause
