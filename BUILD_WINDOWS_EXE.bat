@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build Jellyfin Media Organizer EXE

set "PYTHON_KIND="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 set "PYTHON_KIND=py"
if not defined PYTHON_KIND (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_KIND=python"
)
if not defined PYTHON_KIND goto :python_missing

if exist .build-venv rmdir /s /q .build-venv
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist JellyfinMediaOrganizer.spec del /q JellyfinMediaOrganizer.spec
if exist JellyfinMediaMonitor.spec del /q JellyfinMediaMonitor.spec

if "%PYTHON_KIND%"=="py" (py -3 -m venv .build-venv) else (python -m venv .build-venv)
if errorlevel 1 goto :error
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -e . pyinstaller
if errorlevel 1 goto :error

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name JellyfinMediaOrganizer ^
    --icon "jellyfin_organizer\assets\JellyfinMediaOrganizer.ico" ^
    --add-data "jellyfin_organizer\assets;jellyfin_organizer\assets" ^
    --collect-all PySide6 ^
    windows_entry.py
if errorlevel 1 goto :error

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name JellyfinMediaMonitor ^
    monitor_entry.py
if errorlevel 1 goto :error

if not exist "dist\JellyfinMediaOrganizer\monitor" mkdir "dist\JellyfinMediaOrganizer\monitor"
xcopy /e /i /y "dist\JellyfinMediaMonitor\*" "dist\JellyfinMediaOrganizer\monitor\" >nul
if errorlevel 1 goto :error

echo.
echo Build complete:
echo   %CD%\dist\JellyfinMediaOrganizer\JellyfinMediaOrganizer.exe
echo.
echo The monitor is bundled under:
echo   %CD%\dist\JellyfinMediaOrganizer\monitor\
echo.
pause
exit /b 0

:python_missing
echo.
echo Python 3.10+ is required on the build computer.
echo End users of the compiled program do not need Python.
echo.
echo Download Python from:
echo   https://www.python.org/downloads/windows/
echo.
echo Opening the official Python download page now...
start "" "https://www.python.org/downloads/windows/"
pause
exit /b 1

:error
echo.
echo Build failed. Review the messages above.
pause
exit /b 1
