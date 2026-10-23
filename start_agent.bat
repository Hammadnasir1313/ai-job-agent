@echo off
title Job Agent - WhatsApp replies
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python start_agent.py
pause
