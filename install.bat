@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Qrar Installer
cd /d "%~dp0"

echo ===============================================
echo   Qrar - AI Data Analyst for Power BI
echo   Installer
echo ===============================================
echo.

where py >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found on this computer.
    echo Please install Python 3.10 or newer from:
    echo https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation,
    echo then run this file again.
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
py -3 --version

echo.
echo [2/4] Creating an isolated Python environment (venv)...
if not exist ".venv" (
    py -3 -m venv .venv
)
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Failed to create the virtual environment.
    pause
    exit /b 1
)

echo.
echo [3/4] Installing required packages, this can take a few minutes...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Package installation failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo [4/4] Initial setup...
if not exist ".env" (
    copy ".env.example" ".env" >nul
)
python setup_wizard.py

echo.
echo Creating a desktop shortcut...
set "ICON_CMD="
if exist "assets\logo.ico" set "ICON_CMD=$s.IconLocation='%~dp0assets\logo.ico';"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\Qrar.lnk'); $s.TargetPath='%~dp0run.bat'; $s.WorkingDirectory='%~dp0'; %ICON_CMD% $s.Save()" >nul 2>nul

echo.
echo ===============================================
echo   Installation complete!
echo   Launch the app from the "Qrar" shortcut on
echo   your Desktop, or by running run.bat directly.
echo ===============================================
pause
