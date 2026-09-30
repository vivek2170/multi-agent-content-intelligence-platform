@echo off
setlocal
set "PROJECT_DIR=%~dp0"
echo Stopping ContentForge processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
  echo Killing PID %%a
  taskkill /F /PID %%a >nul 2>&1
)
echo Stop sequence complete.
endlocal
