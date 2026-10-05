@echo off
rem ダブルクリックでセットアップ（全リポジトリの取得と一括インストール）
rem   setup.cmd -Only devtools-common,doc-to-markdown   一部のリポジトリだけ取得する
rem   環境変数 CI（GitHub Actions では自動で入る）か DEVTOOLS_NO_PAUSE があれば、最後の pause をしない
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
if not defined CI if not defined DEVTOOLS_NO_PAUSE pause
exit /b %RC%
