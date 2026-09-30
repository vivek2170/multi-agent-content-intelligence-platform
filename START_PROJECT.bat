@echo off
setlocal enabledelayedexpansion
set "PROJECT_DIR=%~dp0"
if not exist "%PROJECT_DIR%" (
  echo Cannot determine project directory.
  pause
  exit /b 1
)
echo [1/6] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
  echo Python is not installed or not in PATH. Install Python 3.12+.
  pause
  exit /b 1
)
echo [2/6] Preparing virtual environment...
if not exist "%PROJECT_DIR%.venv\" python -m venv "%PROJECT_DIR%.venv"
if not exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
  echo Failed to create virtual environment.
  pause
  exit /b 1
)
"%PROJECT_DIR%.venv\Scripts\python.exe" -m pip install -q --upgrade pip
"%PROJECT_DIR%.venv\Scripts\python.exe" -m pip install -q -r "%PROJECT_DIR%requirements.txt"
echo [3/6] Loading configuration...
if not exist "%PROJECT_DIR%.env" if exist "%PROJECT_DIR%.env.example" copy /y "%PROJECT_DIR%.env.example" "%PROJECT_DIR%.env" >nul
echo [4/6] Ensuring data directory...
if not exist "%PROJECT_DIR%data\" mkdir "%PROJECT_DIR%data"
if not exist "%PROJECT_DIR%logs\" mkdir "%PROJECT_DIR%logs"
echo [5/6] Starting backend...
set "HEALTH_URL=http://localhost:8000/health"
set "APP_URL=http://localhost:8000/"
set "BACKEND_CMD=%PROJECT_DIR%.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --log-level info --no-access-log"
start /B "ContentForge Backend" cmd /c "%BACKEND_CMD%" > "%PROJECT_DIR%logs\backend.log" 2>&1
echo [6/6] Waiting for health check...
set /a "TIMEOUT=60"
set /a "ELAPSED=0"
:wait_loop
timeout /t 1 /nobreak >nul
set /a "ELAPSED+=1"
"%PROJECT_DIR%.venv\Scripts\python.exe" -c "import httpx; import sys; r=httpx.get('%HEALTH_URL%', timeout=3); sys.exit(0 if r.status_code==200 and 'ok' in r.text else 1)" >nul 2>&1
if %errorlevel% neq 0 if %ELAPSED% lss %TIMEOUT% goto wait_loop
if %ELAPSED% geq %TIMEOUT% (
  echo.
  echo [ERROR] Backend did not become healthy within %TIMEOUT% seconds.
  echo [ERROR] Check logs\backend.log for the actual traceback.
  echo.
  pause
  exit /b 1
)
echo.
echo [OK] Backend is healthy.
echo [OK] Opening browser...
start "" "%APP_URL%"
endlocal
