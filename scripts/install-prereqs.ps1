# 開発に必要なツールを一括で入れる（Windows 10 / 11、winget を使う。すべて無料のソフト）
#   install-prereqs.cmd をダブルクリック、または:
#   powershell -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1          入れるものを表示して確認してから入れる
#   powershell -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1 -Yes     確認なしで入れる
#   powershell -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1 -Check   入っているかを調べるだけ
# 入っているものは飛ばす（何度実行してもよい）。WSL2 の有効化だけは管理者の権限と再起動が要る
param([switch]$Yes, [switch]$Check)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$tools = @(
    @{ Name = "Git";                 Id = "Git.Git";                    Cmd = "git";     Why = "リポジトリの取得" },
    @{ Name = "Python 3.12";         Id = "Python.Python.3.12";         Cmd = "py";      Why = "devtools の CLI" },
    @{ Name = "Amazon Corretto 17";  Id = "Amazon.Corretto.17.JDK";     Cmd = "java";    Why = "sample-app のビルド" },
    @{ Name = "Node.js LTS";         Id = "OpenJS.NodeJS.LTS";          Cmd = "node";    Why = "slide-tool" },
    @{ Name = "VS Code";             Id = "Microsoft.VisualStudioCode"; Cmd = "code";    Why = "エディタと Copilot" },
    @{ Name = "Rancher Desktop";     Id = "SUSE.RancherDesktop";        Cmd = "docker";  Why = "DB と S3 エミュレータ（docker compose）" }
)
$extensions = @("vscjava.vscode-java-pack", "vmware.vscode-boot-dev-pack", "GitHub.copilot-chat", "ms-python.python")

function Test-Installed($t) {
    if (Get-Command $t.Cmd -ErrorAction SilentlyContinue) { return $true }
    $out = winget list --id $t.Id --exact --accept-source-agreements 2>$null | Out-String
    return $out -match [regex]::Escape($t.Id)
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "winget がありません。Microsoft Store で「アプリ インストーラー」を入れてから、もう一度実行してください。" -ForegroundColor Red
    exit 2
}

$missing = @()
Write-Host "=== 確認 ==="
foreach ($t in $tools) {
    $ok = Test-Installed $t
    $mark = if ($ok) { "OK  " } else { "なし" }
    Write-Host ("[{0}] {1,-20} {2}" -f $mark, $t.Name, $t.Why)
    if (-not $ok) { $missing += $t }
}
$wsl = $false
try { $null = wsl --status 2>$null; $wsl = ($LASTEXITCODE -eq 0) } catch { $wsl = $false }
Write-Host ("[{0}] {1,-20} {2}" -f $(if ($wsl) { "OK  " } else { "なし" }), "WSL2", "Rancher Desktop が使う")

if ($Check) { if ($missing.Count -or -not $wsl) { exit 1 } else { exit 0 } }

if ($missing.Count -eq 0 -and $wsl) {
    Write-Host "すべて入っています。" -ForegroundColor Green
} else {
    if (-not $Yes) {
        $ans = Read-Host "足りないものを入れますか？ (y/N)"
        if ($ans -notmatch '^[yY]') { Write-Host "やめました。"; exit 0 }
    }
    foreach ($t in $missing) {
        Write-Host "=== $($t.Name) を入れます ==="
        winget install --id $t.Id --exact --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { Write-Host "$($t.Name) のインストールに失敗しました（終了コード $LASTEXITCODE）。" -ForegroundColor Yellow }
    }
    if (-not $wsl) {
        Write-Host "=== WSL2 を有効にします（管理者の確認が出ます。終わったら再起動してください） ==="
        Start-Process wsl -ArgumentList "--install", "--no-distribution" -Verb RunAs -Wait
    }
}

# 入れたばかりのツールをこのウィンドウで使えるよう、PATH を読み直す
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

if (Get-Command code -ErrorAction SilentlyContinue) {
    Write-Host "=== VS Code の拡張機能 ==="
    $have = (code --list-extensions) -join "`n"
    foreach ($e in $extensions) {
        if ($have -match [regex]::Escape($e)) { Write-Host "[OK  ] $e" } else { code --install-extension $e --force | Out-Null; Write-Host "[追加] $e" }
    }
}

Write-Host ""
Write-Host "次にやること:" -ForegroundColor Green
Write-Host "  1. 再起動が必要と表示されたら再起動する（WSL2）"
Write-Host "  2. Rancher Desktop を一度起動し、Container Engine を dockerd (moby) にする"
Write-Host "  3. setup.cmd をダブルクリック（全リポジトリの取得と Python のツールのインストール）"
Write-Host "  4. VS Code で GitHub にサインインし、Copilot を有効にする"
