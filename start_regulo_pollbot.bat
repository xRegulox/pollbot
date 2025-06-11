@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    Regulo PollBot - Windows Launcher
echo ========================================
echo.

:: Check if Python is installed
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8 or higher from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% found!

:: Check Python version (basic check for 3.x)
echo %PYTHON_VERSION% | findstr /r "^3\." >nul
if %errorlevel% neq 0 (
    echo ERROR: Python 3.x is required. Found version %PYTHON_VERSION%
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

:: Check if pip is available
echo [2/6] Checking pip installation...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip is not available!
    echo Please reinstall Python with pip included
    pause
    exit /b 1
)
echo pip is available!

:: Check if virtual environment exists, create if not
echo [3/6] Setting up virtual environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created!
) else (
    echo Virtual environment already exists!
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)

:: Check if requirements.txt exists, create if not
echo [4/6] Checking dependencies...
if not exist "requirements.txt" (
    echo Creating requirements.txt...
    (
        echo Flask==2.3.3
        echo Flask-SQLAlchemy==3.0.5
        echo Flask-Login==0.6.3
        echo Werkzeug==2.3.7
        echo discord.py==2.3.2
        echo matplotlib==3.7.2
        echo APScheduler==3.10.4
        echo python-dotenv==1.0.0
    ) > requirements.txt
    echo requirements.txt created!
)

:: Install/upgrade dependencies
echo Installing/upgrading dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies!
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo Dependencies installed successfully!

:: Initialize database if needed
echo [5/6] Initializing database...
if not exist "regulo_pollbot.db" (
    echo Database not found, initializing...
    python init_db.py
    if %errorlevel% neq 0 (
        echo ERROR: Failed to initialize database!
        pause
        exit /b 1
    )
    echo Database initialized!
) else (
    echo Database already exists!
)

:: Check if .env file exists and create template if not
if not exist ".env" (
    echo Creating .env template...
    (
        echo # Discord Bot Configuration
        echo DISCORD_BOT_TOKEN=your_bot_token_here
        echo.
        echo # Flask Configuration
        echo FLASK_ENV=production
        echo SECRET_KEY=your_secret_key_here
        echo.
        echo # Database Configuration
        echo DATABASE_URL=sqlite:///regulo_pollbot.db
    ) > .env
    echo .env template created! Please edit it with your bot token.
)

:: Start the application
echo [6/6] Starting Regulo PollBot...
echo.
echo ========================================
echo Bot is starting...
echo Web dashboard will be available at: http://localhost:5000
echo Default login: admin / admin
echo ========================================
echo.
echo Press Ctrl+C to stop the bot
echo.

python main.py

:: If we get here, the bot has stopped
echo.
echo ========================================
echo Bot has stopped.
echo ========================================
pause