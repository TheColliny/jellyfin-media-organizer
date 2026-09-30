@echo off
setlocal
cd /d "%~dp0"
title Jellyfin Media Organizer

rem Find Python 3.10+ rather than merely checking whether a launcher/stub exists.
set "PYTHON_KIND="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 set "PYTHON_KIND=py"

if not defined PYTHON_KIND (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_KIND=python"
)

if not defined PYTHON_KIND goto :python_missing

if "%PYTHON_KIND%"=="py" (
    py -3 run.py
) else (
    python run.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The application exited with an error.
    echo If this was the first run, review any installation error shown above.
    echo.
    pause
)
exit /b %ERRORLEVEL%

:python_missing
echo.
echo ================================================================
echo  Python 3.10 or newer is required to run the source version.
echo ================================================================
echo.
echo Download Python for Windows from the official site:
echo   https://www.python.org/downloads/windows/
echo.
echo During installation, enable the option to add Python to PATH.
echo After installation, double-click this file again.
echo.
echo Opening the official Python download page now...
start "" "https://www.python.org/downloads/windows/"
echo.
pause
exit /b 1
