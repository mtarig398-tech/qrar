@echo off
setlocal enabledelayedexpansion
title تثبيت قرار (Qrar)
cd /d "%~dp0"

echo ===============================================
echo   تثبيت قرار - AI Data Analyst for Power BI
echo ===============================================
echo.

where py >nul 2>nul
if %errorlevel% neq 0 (
    echo [خطأ] لم يتم العثور على Python على هذا الجهاز.
    echo الرجاء تثبيت Python 3.10 او احدث من:
    echo https://www.python.org/downloads/
    echo تأكد من تفعيل خيار "Add Python to PATH" أثناء التثبيت، ثم أعد تشغيل هذا الملف.
    pause
    exit /b 1
)

echo [1/4] التحقق من إصدار Python...
py -3 --version

echo.
echo [2/4] إنشاء بيئة بايثون معزولة (venv)...
if not exist ".venv" (
    py -3 -m venv .venv
)
if not exist ".venv\Scripts\activate.bat" (
    echo [خطأ] فشل إنشاء بيئة venv.
    pause
    exit /b 1
)

echo.
echo [3/4] تثبيت المكتبات المطلوبة (قد يستغرق بضع دقائق)...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [خطأ] فشل تثبيت المكتبات. راجع الرسائل أعلاه.
    pause
    exit /b 1
)

echo.
echo [4/4] إعداد الإعدادات الأولية...
if not exist ".env" (
    copy ".env.example" ".env" >nul
)
python setup_wizard.py

echo.
echo إنشاء اختصار على سطح المكتب...
set "ICON_CMD="
if exist "assets\logo.ico" set "ICON_CMD=$s.IconLocation='%~dp0assets\logo.ico';"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\قرار.lnk'); $s.TargetPath='%~dp0run.bat'; $s.WorkingDirectory='%~dp0'; %ICON_CMD% $s.Save()" >nul 2>nul

echo.
echo ===============================================
echo   تم التثبيت بنجاح!
echo   شغّل التطبيق من اختصار "قرار" على سطح المكتب،
echo   أو بتشغيل run.bat مباشرة من هذا المجلد.
echo ===============================================
pause
