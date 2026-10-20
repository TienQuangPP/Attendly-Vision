@echo off
cd /d "%~dp0"
py -3.11 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r attendance_system\requirements.txt
if errorlevel 1 goto error
echo Setup complete. Open run.bat to start Attendly Vision.
pause
exit /b 0
:error
echo Setup failed. Install Python 3.11 x64 and retry. See README.md.
pause
exit /b 1
