@echo off
chcp 65001 >nul
title Reagent-ology 시작

echo ============================================================
echo 🧪 Reagent-ology 시작
echo ============================================================
echo.

cd /d "%~dp0"

python run_app.py

if errorlevel 1 (
    echo.
    echo ❌ 오류가 발생했습니다.
    pause
)
