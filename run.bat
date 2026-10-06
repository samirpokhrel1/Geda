@echo off
rem One-command launcher: creates a virtualenv, installs Flask, starts the app.
cd /d "%~dp0"
if not exist .venv (python -m venv .venv)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python app.py %*
pause
