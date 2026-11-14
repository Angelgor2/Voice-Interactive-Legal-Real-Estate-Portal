@echo off
title Evon + Timbre Legal Portal - Starting Services
color 0B

echo =====================================================================
echo           EVON + TIMBRE: VOICE LEGAL & REAL ESTATE PORTAL
echo           The Great Indian AI Internship Challenge
echo =====================================================================
echo.
echo [1/3] Checking environment & dependencies...
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
    echo [ERROR] Backend virtual environment not found!
    echo Please install dependencies in backend\ using: uv venv --python 3.11 ^& uv pip install -r requirements.txt
    pause
    exit /b 1
)

echo [2/3] Launching FastAPI Backend Server on port 8000...
start "Evon-Timbre Backend (FastAPI)" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo [3/3] Launching Next.js Frontend Dashboard on port 3000...
start "Evon-Timbre Frontend (Next.js)" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 4 /nobreak >nul

echo.
echo =====================================================================
echo   Both services started successfully!
echo   - Backend API Docs:   http://localhost:8000/docs
echo   - Client Dashboard:   http://localhost:3000
echo =====================================================================
echo Opening dashboard in your browser...
start http://localhost:3000

echo.
echo Press any key to stop all portal background windows...
pause >nul

taskkill /FI "WINDOWTITLE eq Evon-Timbre Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Evon-Timbre Frontend*" /T /F >nul 2>&1
echo Done.
