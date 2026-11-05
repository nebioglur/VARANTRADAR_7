@echo off
chcp 65001 >nul
title Verdent Otomatik Deploy
cd /d "%~dp0"
echo ========================================================
echo   VARANTRADAR PRO - VERDENT OTOMATIK DEPLOY
echo ========================================================
python deploy_verdent.py
echo.
pause
