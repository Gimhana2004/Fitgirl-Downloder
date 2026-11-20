@echo off
title Building FitGirl Multi-Part Downloader for Windows
echo ============================================================
echo   Building FitGirl Multi-Part Downloader EXE
echo ============================================================
echo.
echo Installing PyInstaller if not present...
pip install pyinstaller
echo.
echo Compiling to single standalone .exe...
pyinstaller --noconsole --onefile --name "FitGirlDownloader" downloader.py
echo.
echo ============================================================
echo   BUILD COMPLETED!
echo   You can find the EXE inside the "dist" folder:
echo   dist\FitGirlDownloader.exe
echo   (Send this single EXE file to your friends!)
echo ============================================================
pause
