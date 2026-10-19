@echo off
setlocal
cd /d "%~dp0.."
if errorlevel 1 exit /b 1

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\tasks.py run %*
) else (
    python scripts\tasks.py run %*
)
exit /b %errorlevel%
