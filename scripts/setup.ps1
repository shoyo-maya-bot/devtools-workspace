# ワークスペースのセットアップ（Windows）
#   .\setup.cmd                 組織名を聞かれます
#   .\scripts\setup.ps1 -Org other-org   （省略時は repos.yaml の org）
param([string]$Org = "")
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Split-Path $PSScriptRoot -Parent)

$py = $null; $pyArgs = @()
foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; if ($c -eq "py") { $pyArgs = @("-3") }; break }
}
if (-not $py) { Write-Host "Python 3.11 以上をインストールしてください: https://www.python.org/downloads/" -ForegroundColor Red; exit 1 }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Host "Git をインストールしてください: https://git-scm.com/" -ForegroundColor Red; exit 1 }

$cloneArgs = @("scripts\bootstrap.py", "clone"); if ($Org) { $cloneArgs += @("--org", $Org) }
& $py @pyArgs @cloneArgs
if ($LASTEXITCODE -ne 0) { exit 1 }
& $py @pyArgs scripts\bootstrap.py install
if ($LASTEXITCODE -ne 0) { exit 1 }
& ..\.venv\Scripts\doc2md.exe --check-env
Write-Host ""
Write-Host "完了しました。VS Code で devtools.code-workspace を開き、Copilot Chat で / を入力してください。" -ForegroundColor Green
