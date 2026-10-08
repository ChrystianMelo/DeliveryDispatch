@echo off
setlocal
cd /d "%~dp0.."
if errorlevel 1 exit /b 1

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" scripts\tasks.py setup
exit /b %errorlevel%
