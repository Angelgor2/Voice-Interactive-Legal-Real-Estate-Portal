@echo off
title LexiVoice Legal Portal - Starting Services
color 0B

echo =====================================================================
echo           LEXIVOICE: VOICE LEGAL & REAL ESTATE PORTAL
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
start "LexiVoice Backend (FastAPI)" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn main:app --port 8000"

timeout /t 3 /nobreak >nul

echo [3/3] Launching Next.js Frontend Dashboard on port 3000...
start "LexiVoice Frontend (Next.js)" cmd /k "cd /d %~dp0frontend && npm run start"

timeout /t 4 /nobreak >nul

echo.
echo =====================================================================
echo   Both services started successfully!
echo   - Client Dashboard:   http://localhost:3000
echo   - Backend API Docs:   http://localhost:8000/docs
echo =====================================================================
echo Opening dashboard in your browser...
start http://localhost:3000

echo.
echo Press any key to stop all portal background windows...
pause >nul

taskkill /FI "WINDOWTITLE eq LexiVoice Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq LexiVoice Frontend*" /T /F >nul 2>&1
echo Done.
