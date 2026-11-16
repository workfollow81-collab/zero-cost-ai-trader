@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\streamlit.exe" (
  echo لم يتم تثبيت المكتبات بعد. اتبع README_AR.md أولاً.
  pause
  exit /b 1
)
".venv\Scripts\streamlit.exe" run dashboard\app.py
pause
