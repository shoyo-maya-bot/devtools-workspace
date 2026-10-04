@echo off
rem Install the tools needed for development (Git, Python, Java, Node.js, VS Code, Rancher Desktop)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-prereqs.ps1" %*
echo.
pause
