@echo off
REM RentalAI — 在 rental_app 目录启动 FastAPI + 静态前端（Phase 6）
cd /d "%~dp0"
python run.py
if errorlevel 1 pause
