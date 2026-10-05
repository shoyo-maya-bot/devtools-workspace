@echo off
rem Install the tools needed for development (Git, Python, Java, Node.js, VS Code, Rancher Desktop)
rem   install-prereqs.cmd -Check    only report what is installed (exit 0 = all present / 1 = missing)
rem   install-prereqs.cmd -DryRun   show what would be installed, change nothing
rem   No pause at the end when CI (set by GitHub Actions) or DEVTOOLS_NO_PAUSE is defined
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-prereqs.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
if not defined CI if not defined DEVTOOLS_NO_PAUSE pause
exit /b %RC%
