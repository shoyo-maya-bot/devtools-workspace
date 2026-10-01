# 08 → 09 パイプライン例（Windows PowerShell。UTF-8 BOM 付きで保存）
#   .\examples\expense-pipeline.ps1 [-InputFile 入力.xlsx] [-Rules ルール.yaml] [-Table 申請一覧]
param(
    [string]$InputFile = "",
    [string]$Rules = "",
    [string]$Table = "申請一覧",
    [string]$Out = "out"
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
if (-not $InputFile) { $InputFile = Join-Path $Root "doc-to-markdown\samples\expense-list.xlsx" }
if (-not $Rules) { $Rules = Join-Path $Root "field-validation\samples\rules.yaml" }
$Stem = [System.IO.Path]::GetFileNameWithoutExtension($InputFile)

Write-Host "== 1/2 doc2md: $InputFile"
doc2md $InputFile -d $Out --strict -f json -o (Join-Path $Out "$Stem.convert.json")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== 2/2 fieldcheck: $Out\$Stem.md"
fieldcheck validate (Join-Path $Out "$Stem.md") -r $Rules --table $Table -f html -o (Join-Path $Out "$Stem.validation.html")
$rc = $LASTEXITCODE
fieldcheck validate (Join-Path $Out "$Stem.md") -r $Rules --table $Table
Write-Host "レポート: $Out\$Stem.validation.html"
exit $rc
