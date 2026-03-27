@echo off
echo ===================================================
echo Starting Eco-Tracker Application...
echo ===================================================

cd %~dp0
call .\venv\Scripts\activate.bat
python app.py

pause
