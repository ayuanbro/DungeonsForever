@echo off
chcp 65001 >nul
cd /d "%~dp0"
python _temp\fc_update.py %*
pause
