@echo off
python -B "%~dp0_temp\fc_update.py" %*
exit /b %errorlevel%
