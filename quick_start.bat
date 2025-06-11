@echo off
echo ========================================
echo    Regulo PollBot - Quick Start
echo ========================================
echo.

:: Check if setup has been run before
if not exist "venv" (
    echo Running first-time setup...
    call start_regulo_pollbot.bat
) else (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    
    echo Starting Regulo PollBot...
    echo Web dashboard: http://localhost:5000
    echo Default login: admin / admin
    echo.
    echo Press Ctrl+C to stop the bot
    echo.
    
    python main.py
    pause
)