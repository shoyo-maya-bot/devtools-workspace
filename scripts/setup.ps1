# ワークスペースのセットアップ（Windows）
#   .\setup.cmd                          repos.yaml の org（shoyo-maya-bot）から全リポジトリを取得（取得済みのものは最新にする）
#   .\scripts\setup.ps1 -Org other-org   別の組織から取得するとき
#   .\setup.cmd -Only devtools-common,doc-to-markdown   一部のリポジトリだけ取得・インストールする（カンマ区切り）
param([string]$Org = "", [string]$Only = "")
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Split-Path $PSScriptRoot -Parent)

$py = $null; $pyArgs = @()
foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; if ($c -eq "py") { $pyArgs = @("-3") }; break }
}
if (-not $py) { Write-Host "Python 3.11 以上をインストールしてください: https://www.python.org/downloads/" -ForegroundColor Red; exit 1 }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Host "Git をインストールしてください: https://git-scm.com/" -ForegroundColor Red; exit 1 }

$bs = @("scripts\bootstrap.py"); if ($Only) { $bs += @("--only", $Only) }
$cloneArgs = $bs + @("clone"); if ($Org) { $cloneArgs += @("--org", $Org) }
& $py @pyArgs @cloneArgs
if ($LASTEXITCODE -ne 0) { exit 1 }
# 取得済みのリポジトリは最新にする（手元に変更があって進められないものは知らせて先へ進む）
& $py @pyArgs @bs pull
if ($LASTEXITCODE -ne 0) { Write-Host "最新にできなかったリポジトリがあります（上の表示を確かめてください）。セットアップは続けます。" -ForegroundColor Yellow }
& $py @pyArgs @bs install
if ($LASTEXITCODE -ne 0) { exit 1 }
# doc2md の動作環境の確認（doc-to-markdown を取得していないときは飛ばす）
if (Test-Path ..\.venv\Scripts\doc2md.exe) { & ..\.venv\Scripts\doc2md.exe --check-env }
Write-Host ""
Write-Host "完了しました。VS Code で devtools.code-workspace を開き、Copilot Chat で / を入力してください。" -ForegroundColor Green
