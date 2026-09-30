@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build Jellyfin Media Organizer Installer

set "VERSION=0.4.0"
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
if not exist release mkdir release

if "%PYTHON_KIND%"=="py" (py -3 -m venv .build-venv) else (python -m venv .build-venv)
if errorlevel 1 goto :error
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -e . pyinstaller
if errorlevel 1 goto :error

echo.
echo ================================================================
echo  Building main desktop application
echo ================================================================
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

echo.
echo ================================================================
echo  Building lightweight background monitor
echo ================================================================
python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name JellyfinMediaMonitor ^
    monitor_entry.py
if errorlevel 1 goto :error

if not exist "dist\JellyfinMediaOrganizer\JellyfinMediaOrganizer.exe" goto :app_build_missing
if not exist "dist\JellyfinMediaMonitor\JellyfinMediaMonitor.exe" goto :monitor_build_missing
if not exist "jellyfin_organizer\assets\JellyfinMediaOrganizer.ico" goto :icon_missing
if not exist "installer\windows\JellyfinMediaOrganizer.iss" goto :iss_missing

set "ISCC="
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
if exist "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC goto :inno_missing

set "JMO_PROJECT_ROOT=%CD%"
set "JMO_VERSION=%VERSION%"
echo.
echo ================================================================
echo  Building installer
echo ================================================================
echo Project root: %JMO_PROJECT_ROOT%
echo App build:    %JMO_PROJECT_ROOT%\dist\JellyfinMediaOrganizer
echo Monitor:      %JMO_PROJECT_ROOT%\dist\JellyfinMediaMonitor
echo Inno Setup:   %ISCC%
echo.
"%ISCC%" "installer\windows\JellyfinMediaOrganizer.iss"
if errorlevel 1 goto :error

if not exist "release\JellyfinMediaOrganizer-Setup-%VERSION%.exe" goto :installer_missing

echo.
echo ================================================================
echo  Release installer built successfully.
echo ================================================================
echo.
echo Installer:
echo   %CD%\release\JellyfinMediaOrganizer-Setup-%VERSION%.exe
echo.
echo The finished installer includes both the desktop app and the
echo lightweight background monitoring process.
echo.
pause
exit /b 0

:python_missing
echo.
echo ================================================================
echo  Python 3.10 or newer is required on the BUILD computer only.
echo ================================================================
echo.
echo End users of the finished Setup EXE do NOT need Python installed.
echo.
echo Download Python for Windows from the official site:
echo   https://www.python.org/downloads/windows/
echo.
echo During installation, enable the option to add Python to PATH.
echo After installation, double-click this build script again.
echo.
echo Opening the official Python download page now...
start "" "https://www.python.org/downloads/windows/"
echo.
pause
exit /b 1

:inno_missing
echo.
echo ================================================================
echo  Inno Setup 6 or 7 is required to create the Windows Setup EXE.
echo ================================================================
echo.
echo Install Inno Setup from its official site:
echo   https://jrsoftware.org/isdl.php
echo.
where winget >nul 2>nul
if not errorlevel 1 (
    echo You can also install it from a terminal with:
    echo   winget install --id JRSoftware.InnoSetup --exact
    echo.
)
echo Opening the official Inno Setup download page now...
start "" "https://jrsoftware.org/isdl.php"
echo.
pause
exit /b 1

:app_build_missing
echo ERROR: Main application EXE was not found:
echo   %CD%\dist\JellyfinMediaOrganizer\JellyfinMediaOrganizer.exe
goto :error

:monitor_build_missing
echo ERROR: Background monitor EXE was not found:
echo   %CD%\dist\JellyfinMediaMonitor\JellyfinMediaMonitor.exe
goto :error

:icon_missing
echo ERROR: Installer icon is missing:
echo   %CD%\jellyfin_organizer\assets\JellyfinMediaOrganizer.ico
goto :error

:iss_missing
echo ERROR: Inno Setup script is missing:
echo   %CD%\installer\windows\JellyfinMediaOrganizer.iss
goto :error

:installer_missing
echo ERROR: Inno Setup completed, but the expected installer was not found:
echo   %CD%\release\JellyfinMediaOrganizer-Setup-%VERSION%.exe
goto :error

:error
echo.
echo Build failed. Review the messages above.
echo.
pause
exit /b 1
