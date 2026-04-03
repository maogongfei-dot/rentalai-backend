@echo off
REM 从 scripts 目录启动：工作目录切到 rental_app 后执行 run.py
cd /d "%~dp0.."
python run.py
if errorlevel 1 pause
