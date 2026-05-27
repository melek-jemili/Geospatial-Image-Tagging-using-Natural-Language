@echo off
REM ========================================
REM Geospatial Image Analysis - Windows Launcher
REM ========================================

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║     🌍  Geospatial Image Analysis with Quantum Computing    ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo ✅ Python found

REM Check if venv exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate venv
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo 📥 Installing dependencies...
pip install -q -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed

REM Check if .env exists
if not exist ".env" (
    echo 📝 Creating .env file...
    (
        echo OPENAI_API_KEY=your_api_key_here
        echo IBM_QUANTUM_CHANNEL=ibm_quantum
        echo FLASK_ENV=development
    ) > .env
    echo ⚠️  Created .env file - Please update with your API keys
)

REM Create necessary directories
if not exist "uploads" mkdir uploads
if not exist "output" mkdir output
if not exist "chroma_db" mkdir chroma_db

echo.
echo 🚀 Starting Flask Server...
echo 📍 Access the application at: http://localhost:5000
echo.
echo Press CTRL+C to stop the server
echo.

python app.py

pause
