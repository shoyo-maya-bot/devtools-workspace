# doc2md → fieldcheck パイプライン例（Windows PowerShell。UTF-8 BOM 付きで保存）
#   .\examples\expense-pipeline.ps1 [-InputFile 入力.xlsx] [-Rules ルール.yaml] [-Table 申請一覧] [-Venv 仮想環境]
# 前提: ワークスペースの setup（setup.cmd）で、兄弟フォルダの ..\.venv に doc-to-markdown と office-review が入っていること。
# doc2md・fieldcheck は ..\.venv\Scripts（-Venv で変えられる）にあればそれを、無ければ PATH のものを使う（有効化は要らない）。
param(
    [string]$InputFile = "",
    [string]$Rules = "",
    [string]$Table = "申請一覧",
    [string]$Out = "out",
    [string]$Venv = ""
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
if (-not $InputFile) { $InputFile = Join-Path $Root "doc-to-markdown\samples\expense-list.xlsx" }
if (-not $Rules) { $Rules = Join-Path $Root "office-review\fieldcheck\samples\rules.yaml" }
if (-not $Venv) { $Venv = Join-Path $Root ".venv" }
$Stem = [System.IO.Path]::GetFileNameWithoutExtension($InputFile)

# ツールの場所: 仮想環境（既定 ..\.venv）の Scripts → PATH の順に探す
function Find-Tool([string]$Name) {
    $exe = Join-Path $Venv "Scripts\$Name.exe"
    if (Test-Path $exe) { return $exe }
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}
$Doc2md = Find-Tool "doc2md"
$Fieldcheck = Find-Tool "fieldcheck"
$missing = @(); if (-not $Doc2md) { $missing += "doc2md" }; if (-not $Fieldcheck) { $missing += "fieldcheck" }
if ($missing) {
    Write-Host "$($missing -join ', ') が見つかりません（探した場所: $Venv\Scripts と PATH）。" -ForegroundColor Red
    Write-Host "先にワークスペースの setup.cmd を流して ..\.venv に入れるか、-Venv <仮想環境> を付けて実行してください。" -ForegroundColor Red
    exit 2
}
foreach ($f in @($InputFile, $Rules)) {
    if (-not (Test-Path $f)) { Write-Host "ファイルがありません: $f（doc-to-markdown・office-review を兄弟フォルダに取得してください）" -ForegroundColor Red; exit 2 }
}

Write-Host "== 1/2 doc2md: $InputFile"
& $Doc2md $InputFile -d $Out --strict -f json -o (Join-Path $Out "$Stem.convert.json")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== 2/2 fieldcheck: $Out\$Stem.md"
& $Fieldcheck validate (Join-Path $Out "$Stem.md") -r $Rules --table $Table -f html -o (Join-Path $Out "$Stem.validation.html")
$rc = $LASTEXITCODE
& $Fieldcheck validate (Join-Path $Out "$Stem.md") -r $Rules --table $Table
Write-Host "レポート: $Out\$Stem.validation.html"
exit $rc
