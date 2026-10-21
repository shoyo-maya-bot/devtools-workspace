# doc2md → fieldcheck パイプライン例（Windows PowerShell。UTF-8 BOM 付きで保存）
#   .\examples\expense-pipeline.ps1 [-InputFile 入力.xlsx] [-Rules ルール.yaml] [-Table 申請一覧] [-Venv 仮想環境]
# 前提: ワークスペースの setup（setup.cmd）で、兄弟フォルダの ..\.venv に doc-to-markdown と office-review が入っていること。
# doc2md・fieldcheck は ..\.venv\Scripts（-Venv で変えられる）にあればそれを、無ければ PATH のものを使う（有効化は要らない）。
# 終了コード（examples/expense-pipeline.sh と同じ）:
#   0 変換の警告なし・指摘なし / 1 fieldcheck の指摘あり（変換の警告なし） / 2 前提の誤り（ツール・入力が無い、引数・入力・ルールの誤り）
#   3 実行時エラー（変換結果の Markdown ができなかったときも） / 4 doc2md --strict の変換の警告あり・指摘なし / 5 変換の警告あり・指摘あり
#   変換の警告があるときは、fieldcheck の結果を信じる前に <Out>\<名前>.convert.json の警告を確かめて元ファイルと突き合わせる
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

$Md = Join-Path $Out "$Stem.md"
# 前回の出力が残っていると、変換できなかったのに古い Markdown を検証してしまうので消しておく
if (Test-Path -LiteralPath $Md) { Remove-Item -LiteralPath $Md -Force }

Write-Host "== 1/2 doc2md: $InputFile"
& $Doc2md $InputFile -d $Out --strict -f json -o (Join-Path $Out "$Stem.convert.json")
$conv = $LASTEXITCODE
if ($conv -eq 1) {
    # --strict の警告（変換ロスなど）でも Markdown はできている. 項目間の検証は続け、最後に 4・5 で知らせる
    if (-not (Test-Path -LiteralPath $Md)) {
        Write-Host "doc2md: 変換できませんでした（$Out\$Stem.convert.json を確かめてください）" -ForegroundColor Red
        exit 3
    }
    Write-Host "doc2md: 変換の警告があります（$Out\$Stem.convert.json）。fieldcheck は続けますが、元ファイルと突き合わせてください" -ForegroundColor Yellow
} elseif ($conv -eq 2) {
    Write-Host "doc2md: 引数・入力の誤りで止まりました（終了コード 2）" -ForegroundColor Red
    exit 2
} elseif ($conv -ne 0) {
    Write-Host "doc2md: 実行時エラーで止まりました（終了コード $conv）" -ForegroundColor Red
    exit 3
}

Write-Host "== 2/2 fieldcheck: $Md"
& $Fieldcheck validate $Md -r $Rules --table $Table -f html -o (Join-Path $Out "$Stem.validation.html")
$rc = $LASTEXITCODE
& $Fieldcheck validate $Md -r $Rules --table $Table
if ($rc -eq 2) {
    Write-Host "fieldcheck: ルール・列名・入力の誤りで止まりました（終了コード 2）" -ForegroundColor Red
    exit 2
} elseif ($rc -ne 0 -and $rc -ne 1) {
    Write-Host "fieldcheck: 実行時エラーで止まりました（終了コード $rc）" -ForegroundColor Red
    exit 3
}
Write-Host "レポート: $Out\$Stem.convert.json, $Out\$Stem.validation.html"
if ($conv -eq 1) { exit (4 + $rc) }
exit $rc
