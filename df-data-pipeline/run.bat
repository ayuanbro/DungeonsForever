@echo off
chcp 65001 >nul
python -B "%~dp0_temp\fc_update.py" %*
exit /b %errorlevel%
