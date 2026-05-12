@echo off
title HAPS Server
echo ============================================
echo   HAPS Production Server
echo   Starting on http://127.0.0.1:5000
echo ============================================
echo.

:: Change to the script's own directory (where app.py lives)
cd /d "%~dp0"

:: Wait for network/PostgreSQL to be ready (10 seconds after boot)
timeout /t 10 /nobreak >nul

:: Start the Waitress production server on 127.0.0.1:5000
waitress-serve --host=127.0.0.1 --port=5000 app:app

:: If server crashes, pause so the window stays open for debugging
echo.
echo Server stopped unexpectedly. Press any key to exit...
pause >nul
