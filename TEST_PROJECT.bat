@echo off
setlocal
set "PROJECT_DIR=%~dp0"
if not exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
  echo Virtual environment not found. Run START_PROJECT.bat first.
  pause
  exit /b 1
)
echo Running tests...
"%PROJECT_DIR%.venv\Scripts\python.exe" -m pytest "%PROJECT_DIR%tests" -v
if %errorlevel% neq 0 (
  echo Tests failed.
  pause
  exit /b 1
)
echo Tests passed.
pause
endlocal
