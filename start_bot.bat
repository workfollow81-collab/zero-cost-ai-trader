@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo لم يتم تثبيت البيئة بعد. اتبع README_AR.md أولاً.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
pause
