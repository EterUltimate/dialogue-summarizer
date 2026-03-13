@echo off
setlocal enabledelayedexpansion

REM ============================================
REM Change to script's directory
REM ============================================
cd /d "%~dp0"

chcp 65001 >nul 2>&1
echo ========================================
echo  Dialogue Summarizer System
echo ========================================
echo.
echo Working directory: %CD%
echo.

REM ============================================
REM Auto-detect Python installation
REM ============================================
echo Detecting Python installation...

set PYTHON_CMD=
set PYTHON_FOUND=0

REM Method 1: Use py launcher (most reliable on Windows)
py --version >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
    set PYTHON_FOUND=1
    goto :python_found
)

REM Method 2: Check python3
python3 --version >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python3
    set PYTHON_FOUND=1
    goto :python_found
)

REM Method 3: Check python (may be Windows Store alias)
python --version >nul 2>&1
if %errorlevel%==0 (
    python -c "import sys; sys.exit(0)" >nul 2>&1
    if %errorlevel%==0 (
        set PYTHON_CMD=python
        set PYTHON_FOUND=1
        goto :python_found
    )
)

REM Method 4: Search in common AppData paths
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%d\python.exe" (
        set PYTHON_CMD=%%d\python.exe
        set PYTHON_FOUND=1
        goto :python_found
    )
)

for /d %%d in ("%APPDATA%\Programs\Python\Python*") do (
    if exist "%%d\python.exe" (
        set PYTHON_CMD=%%d\python.exe
        set PYTHON_FOUND=1
        goto :python_found
    )
)

for %%e in (python.exe python3.exe) do (
    for /f "tokens=*" %%p in ('where %%e 2^>nul ^| findstr /v "WindowsApps"') do (
        if exist "%%p" (
            set PYTHON_CMD=%%p
            set PYTHON_FOUND=1
            goto :python_found
        )
    )
)

for /d %%d in ("%ProgramFiles%\Python*\Python*") do (
    if exist "%%d\python.exe" (
        set PYTHON_CMD=%%d\python.exe
        set PYTHON_FOUND=1
        goto :python_found
    )
)

for /d %%d in ("%ProgramFiles(x86)%\Python*\Python*") do (
    if exist "%%d\python.exe" (
        set PYTHON_CMD=%%d\python.exe
        set PYTHON_FOUND=1
        goto :python_found
    )
)

for /d %%d in ("C:\Python*") do (
    if exist "%%d\python.exe" (
        set PYTHON_CMD=%%d\python.exe
        set PYTHON_FOUND=1
        goto :python_found
    )
)

REM ============================================
REM Python not found
REM ============================================
echo.
echo ========================================
echo  ERROR: Python not found!
echo ========================================
echo.
echo Python 3.9+ is required.
echo Download from: https://www.python.org/downloads/
echo.
pause
exit /b 1

REM ============================================
REM Python found
REM ============================================
:python_found
echo Found Python: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

%PYTHON_CMD% -c "import sys; v=sys.version_info; sys.exit(0 if v.major==3 and v.minor>=9 else 1)" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Python 3.9+ is required.
    pause
)

REM ============================================
REM Create virtual environment
REM ============================================
if not exist "venv" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM ============================================
REM Activate virtual environment
REM ============================================
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM ============================================
REM Install dependencies (with real-time output)
REM ============================================
echo.
echo ========================================
echo  Installing dependencies...
echo ========================================
echo.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Some dependencies failed to install
    echo Please check the error messages above.
    echo.
)

REM ============================================
REM Check .env configuration
REM ============================================
if not exist ".env" (
    echo.
    echo ========================================
    echo  Configuration Required
    echo ========================================
    echo.
    echo Creating .env from .env.example...
    copy .env.example .env >nul
    echo.
    echo Please edit .env to configure:
    echo   - DIALOGUE_BACKEND: ollama or openai
    echo   - Your model settings
    echo.
    notepad .env
    echo.
    echo Run this script again after configuration.
    pause
    exit /b 1
)

REM ============================================
REM Start application
REM ============================================
echo.
echo ========================================
echo  Starting application...
echo  Visit http://localhost:7860
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
