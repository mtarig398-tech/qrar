@echo off
chcp 65001 >nul
title Qrar
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Installation not found.
    echo Please run install.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
streamlit run app.py
pause
