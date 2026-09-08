@echo off
echo ========================================================
echo         Starting Smart CRM AI System...
echo ========================================================
cd /d "%~dp0"
call .\venv\Scripts\activate
python main.py
pause
