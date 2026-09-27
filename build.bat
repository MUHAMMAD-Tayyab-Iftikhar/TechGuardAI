@echo off
title TechGuardAI — Build Tool
color 0A

echo ============================================================
echo   TechGuardAI — Packaging as Standalone EXE
echo ============================================================
echo.

:: ── Check Python is available ────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: ── Install build dependencies ───────────────────────────────────────────────
echo [1/3] Installing build dependencies...
pip install pyinstaller pyinstaller-hooks-contrib --quiet
pip install -r requirements.txt --quiet
echo       Done.
echo.

:: ── Run PyInstaller ──────────────────────────────────────────────────────────
echo [2/3] Building standalone EXE (this takes 1-3 minutes)...
pyinstaller TechGuardAI.spec --noconfirm --clean
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check the output above for details.
    pause
    exit /b 1
)
echo       Done.
echo.

:: ── Copy README into dist for distribution ───────────────────────────────────
echo [3/3] Preparing distribution folder...
copy /Y README.md dist\TechGuardAI\README.txt >nul
echo       Done.
echo.

echo ============================================================
echo   BUILD SUCCESSFUL!
echo   Your distributable is in:  dist\TechGuardAI\
echo   Share that entire folder — users just double-click
echo   TechGuardAI.exe to get started. No install needed!
echo ============================================================
echo.
pause
