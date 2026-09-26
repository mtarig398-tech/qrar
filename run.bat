@echo off
title قرار (Qrar)
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [خطأ] لم يتم العثور على بيئة التثبيت.
    echo الرجاء تشغيل install.bat أولاً.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
streamlit run app.py
pause
