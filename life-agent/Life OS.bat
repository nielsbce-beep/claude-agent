@echo off
rem Start Life OS en open het dashboard in de browser (http://localhost:8765)
cd /d "%~dp0"
title Life OS
python server.py
pause
