@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Using venv Python (has cryptography for MySQL)...
python app.py
pause
