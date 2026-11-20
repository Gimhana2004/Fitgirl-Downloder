@echo off
title Building FitGirl Multi-Part Downloader for Windows
echo ============================================================
echo   Building FitGirl Multi-Part Downloader EXE
echo ============================================================
echo.

:: Detect Python or Py launcher
set PYTHON_CMD=
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python was not found on this PC!
    echo.
    echo Please install Python:
    echo 1. Go to: https://www.python.org/downloads/
    echo 2. Download and run the installer.
    echo 3. VERY IMPORTANT: Check the box "Add Python to PATH" at the bottom!
    echo 4. Click Install Now, then run this batch file again.
    echo.
    pause
    exit /b 1
)

echo Found Python using: %PYTHON_CMD%
echo.
echo Installing / Updating PyInstaller...
%PYTHON_CMD% -m pip install --upgrade pyinstaller
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install PyInstaller. Make sure your internet is connected.
    pause
    exit /b 1
)

echo.
echo Compiling to single standalone .exe...
%PYTHON_CMD% -m PyInstaller --noconsole --onefile --name "FitGirlDownloader" downloader.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   BUILD COMPLETED SUCCESSFULLY!
echo   You can find the EXE inside the "dist" folder:
echo   dist\FitGirlDownloader.exe
echo   (Send this single EXE file to your friends!)
echo ============================================================
echo.
pause
