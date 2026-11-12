@echo off
set "GUI_PYTHON=%USERPROFILE%\AppData\Local\wechat-chat-export\venv\Scripts\pythonw.exe"
if exist "%GUI_PYTHON%" goto launch
set "SETUP_SCRIPT=%~dp0scripts\setup.ps1"
if exist "%SETUP_SCRIPT%" goto setup
set "SETUP_SCRIPT=%USERPROFILE%\.codex\skills\wechat-chat-export\scripts\setup.ps1"
:setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SETUP_SCRIPT%"
if errorlevel 1 goto failed
:launch
wscript.exe "%~dp0launcher.vbs"
exit /b 0
:failed
echo Setup failed. Python 3.11 or newer is required.
pause
exit /b 1
