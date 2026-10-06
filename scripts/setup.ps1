# ワークスペースのセットアップ（Windows）
#   .\setup.cmd                          repos.yaml の org（shoyo-maya-bot）から全リポジトリを取得（取得済みのものは最新にする）
#   .\scripts\setup.ps1 -Org other-org   別の組織から取得するとき
#   .\setup.cmd -Only devtools-common,doc-to-markdown   一部のリポジトリだけ取得・インストールする（カンマ区切り）
#   .\setup.cmd -Dev                     開発者向け: devtools-common をローカルの checkout で置き換えて入れる（既定は各ツールが固定した版）
param([string]$Org = "", [string]$Only = "", [switch]$Dev)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Split-Path $PSScriptRoot -Parent)

# 日本語の表示が化けたり、出力先の文字コードで書けずに止まったりしないよう、Python の入出力を UTF-8 にする
$env:PYTHONUTF8 = "1"

# 3.11 以上の Python を探す（py ランチャーが古い版を選ぶこともあるので、版を確かめてから使う）
$py = $null; $pyArgs = @()
foreach ($c in @("py", "python", "python3")) {
    if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { continue }
    $a = @(); if ($c -eq "py") { $a = @("-3") }
    & $c @a -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
    if ($LASTEXITCODE -eq 0) { $py = $c; $pyArgs = $a; break }
}
if (-not $py) { Write-Host "Python 3.11 以上をインストールしてください: https://www.python.org/downloads/" -ForegroundColor Red; exit 1 }
& $py @pyArgs --version
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Host "Git をインストールしてください: https://git-scm.com/" -ForegroundColor Red; exit 1 }

$bs = @("scripts\bootstrap.py"); if ($Only) { $bs += @("--only", $Only) }
$cloneArgs = $bs + @("clone"); if ($Org) { $cloneArgs += @("--org", $Org) }
& $py @pyArgs @cloneArgs
if ($LASTEXITCODE -ne 0) { exit 1 }
# 取得済みのリポジトリは最新にする（手元に変更があって進められないものは知らせて先へ進む）
& $py @pyArgs @bs pull
if ($LASTEXITCODE -ne 0) { Write-Host "最新にできなかったリポジトリがあります（上の表示を確かめてください）。セットアップは続けます。" -ForegroundColor Yellow }
$installArgs = $bs + @("install"); if ($Dev) { $installArgs += @("--dev") }
& $py @pyArgs @installArgs
if ($LASTEXITCODE -ne 0) { exit 1 }
# doc2md の動作環境の確認（doc-to-markdown を取得していないときは飛ばす）
if (Test-Path ..\.venv\Scripts\doc2md.exe) { & ..\.venv\Scripts\doc2md.exe --check-env }
Write-Host ""
Write-Host "完了しました。VS Code で devtools.code-workspace を開き、Copilot Chat で / を入力してください。" -ForegroundColor Green
