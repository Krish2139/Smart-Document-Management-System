@echo off
title Smart Document Manager - Backend Server
echo Starting Smart Document Manager on http://127.0.0.1:8000 ...
cd /d "%~dp0"
call .\venv\Scripts\activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
