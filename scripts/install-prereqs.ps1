# 開発に必要なツールを一括で入れる（Windows 10 / 11、winget を使う。すべて無料のソフト）
#   install-prereqs.cmd をダブルクリック、または:
#   powershell -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1          入れるものを表示して確認してから入れる
#   powershell -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1 -Yes     確認なしで入れる
#   powershell -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1 -Check   入っているかを調べるだけ（終了コード 0 = 全部ある / 1 = 足りない）
#   powershell -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1 -DryRun  何を入れるかを表示するだけ（確認なし・何も変えない。CI でも使う）
# 入っているものは飛ばす（何度実行してもよい）。WSL2 の有効化だけは管理者の権限と再起動が要る
param([switch]$Yes, [switch]$Check, [switch]$DryRun)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:WSL_UTF8 = "1"   # wsl.exe の出力を UTF-8 にする（既定は UTF-16 で文字化けする）

# 外部コマンドを実行して、標準出力と標準エラーをまとめた文字列と終了コードを返す。
# Windows PowerShell 5.1 は $ErrorActionPreference = "Stop" のとき、外部コマンドが標準エラーに書くだけで例外にするため、cmd.exe を通す
function Invoke-Native([string]$line) {
    $out = cmd.exe /d /c "$line 2>&1" | Out-String
    return @{ Out = $out; Code = $LASTEXITCODE }
}

function Get-JavaMajor {
    if (-not (Get-Command java -ErrorAction SilentlyContinue)) { return 0 }
    $r = Invoke-Native "java -version"
    if ($r.Out -match 'version "(\d+)(?:\.(\d+))?') {
        $major = [int]$Matches[1]
        if ($major -eq 1 -and $Matches[2]) { $major = [int]$Matches[2] }   # 1.8 → 8
        return $major
    }
    return 0
}

function Test-Wsl2 {
    # wsl --status が成功するだけでは足りない（仮想マシン プラットフォームが無効・再起動待ちでも 0 を返す）
    if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) { return @{ Ok = $false; Note = "wsl コマンドがありません" } }
    $r = Invoke-Native "wsl --status"
    if ($r.Code -ne 0) { return @{ Ok = $false; Note = "WSL が入っていません" } }
    if ($r.Out -match 'Virtual Machine Platform|仮想マシン プラットフォーム|enablevirtualization') {
        return @{ Ok = $false; Note = "WSL2 を実行できません（再起動待ち、または BIOS の仮想化が無効）" }
    }
    try {
        $vmp = Get-CimInstance Win32_OptionalFeature -Filter "Name='VirtualMachinePlatform'" -ErrorAction Stop
        if ($vmp -and $vmp.InstallState -ne 1) { return @{ Ok = $false; Note = "仮想マシン プラットフォームが無効です" } }
    } catch { Write-Verbose "仮想マシン プラットフォームの状態を読めませんでした: $_" }
    return @{ Ok = $true; Note = "" }
}

function Test-WingetInstalled([string]$id) {
    $r = Invoke-Native "winget list --id $id --exact --accept-source-agreements"
    return $r.Out -match [regex]::Escape($id)
}

# Test: 入っているか（$true / $false）。Note: 入っていないときの補足
$tools = @(
    @{ Name = "Git";                Id = "Git.Git";                    Why = "リポジトリの取得";
       Test = { [bool](Get-Command git -ErrorAction SilentlyContinue) } },
    @{ Name = "Python 3.12";        Id = "Python.Python.3.12";         Why = "devtools の CLI";
       Test = { [bool](Get-Command py -ErrorAction SilentlyContinue) -or (Test-WingetInstalled "Python.Python.3.12") } },
    @{ Name = "Amazon Corretto 17"; Id = "Amazon.Corretto.17.JDK";     Why = "sample-app のビルド（Java 17 以上が要る）";
       Test = { (Get-JavaMajor) -ge 17 } },
    @{ Name = "Node.js LTS";        Id = "OpenJS.NodeJS.LTS";          Why = "slide-tool";
       Test = { [bool](Get-Command node -ErrorAction SilentlyContinue) } },
    @{ Name = "VS Code";            Id = "Microsoft.VisualStudioCode"; Why = "エディタと Copilot";
       Test = { [bool](Get-Command code -ErrorAction SilentlyContinue) } },
    # Rancher Desktop はマシン全体に入れる版しかないため --scope machine が要る（付けないと「適用できるインストーラーがない」で失敗する）
    @{ Name = "Rancher Desktop";    Id = "SUSE.RancherDesktop";        Why = "DB と S3 エミュレータ（docker compose）"; Scope = "machine";
       Test = { [bool](Get-Command rdctl -ErrorAction SilentlyContinue) -or (Test-WingetInstalled "SUSE.RancherDesktop") } }
)
$extensions = @("vscjava.vscode-java-pack", "vmware.vscode-boot-dev-pack", "GitHub.copilot-chat", "ms-python.python")

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "winget がありません。Microsoft Store で「アプリ インストーラー」を入れてから、もう一度実行してください。" -ForegroundColor Red
    exit 2
}

$missing = @()
Write-Host "=== 確認 ==="
foreach ($t in $tools) {
    $ok = & $t.Test
    $note = ""
    if ($t.Id -eq "Amazon.Corretto.17.JDK" -and -not $ok) {
        $major = Get-JavaMajor
        if ($major -gt 0) { $note = "（今の java は $major。17 を追加で入れます。$major は消しません）" }
    }
    Write-Host ("[{0}] {1,-20} {2}{3}" -f $(if ($ok) { "OK  " } else { "なし" }), $t.Name, $t.Why, $note)
    if (-not $ok) { $missing += $t }
}
$wsl = Test-Wsl2
Write-Host ("[{0}] {1,-20} {2}{3}" -f $(if ($wsl.Ok) { "OK  " } else { "なし" }), "WSL2", "Rancher Desktop が使う", $(if ($wsl.Note) { "（$($wsl.Note)）" } else { "" }))

if ($Check) { if ($missing.Count -or -not $wsl.Ok) { exit 1 } else { exit 0 } }

$failed = @()
if ($missing.Count -eq 0 -and $wsl.Ok) {
    Write-Host "すべて入っています。" -ForegroundColor Green
} else {
    if ($DryRun) { Write-Host "[dry-run] 確認なしで進めます（実際には入れません）" }
    elseif (-not $Yes) {
        $ans = Read-Host "足りないものを入れますか？ (y/N)"
        if ($ans -notmatch '^[yY]') { Write-Host "やめました。"; exit 0 }
    }
    foreach ($t in $missing) {
        Write-Host "=== $($t.Name) を入れます ==="
        $wingetArgs = @("install", "--id", $t.Id, "--exact", "--silent", "--accept-package-agreements", "--accept-source-agreements")
        if ($t.Scope) { $wingetArgs += @("--scope", $t.Scope) }
        if ($DryRun) { Write-Host ("[dry-run] winget " + ($wingetArgs -join " ")); continue }
        & winget @wingetArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Host ("{0} のインストールに失敗しました（終了コード 0x{1:X8}）。" -f $t.Name, $LASTEXITCODE) -ForegroundColor Yellow
            $failed += $t.Name
        }
    }
    if (-not $wsl.Ok) {
        if ($DryRun) {
            Write-Host "[dry-run] WSL2: $($wsl.Note)。実際には wsl --install --no-distribution を管理者で実行します"
        } elseif ($wsl.Note -match "再起動待ち") {
            Write-Host "WSL2 は入っていますが、まだ使えません。PC を再起動してください。再起動しても直らないときは、BIOS（UEFI）で仮想化（Intel VT-x / AMD-V）を有効にしてください。" -ForegroundColor Yellow
        } else {
            Write-Host "=== WSL2 を有効にします（管理者の確認が出ます。終わったら再起動してください） ==="
            Start-Process wsl -ArgumentList "--install", "--no-distribution" -Verb RunAs -Wait
        }
    }
}

# 入れたばかりのツールをこのウィンドウで使えるよう、PATH を読み直す
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

# Rancher Desktop 1.23.1 / 1.24.0 の不具合の回避策: docker の死活確認の URL（http://./_ping）を新しい curl が拒否し、
# docker が「timed out dialing Hyper-V socket」になる（起動直後から、または数分後）。起動のたびに URL を書き換えるスクリプトを置く。
#   https://github.com/rancher-sandbox/rancher-desktop/issues/10780 （修正版が出たら、この処理と置いたファイルは消してよい）
if (Get-Command rdctl -ErrorAction SilentlyContinue) {
    $prov = Join-Path $env:LOCALAPPDATA "rancher-desktop\provisioning"
    $fix = Join-Path $prov "fix-docker-healthcheck.start"
    if ($DryRun) { if (-not (Test-Path $fix)) { Write-Host "[dry-run] Rancher Desktop の不具合の回避策を置きます: $fix" } }
    elseif (-not (Test-Path $fix)) {
        New-Item -ItemType Directory -Force -Path $prov | Out-Null
        [IO.File]::WriteAllText($fix, "#!/bin/sh`nsed -i 's|http://\./_ping|http://localhost/_ping|g' /etc/init.d/docker`n")
        Write-Host "[追加] Rancher Desktop の不具合の回避策: $fix"
    }
}

if (Get-Command code -ErrorAction SilentlyContinue) {
    Write-Host "=== VS Code の拡張機能 ==="
    $have = (Invoke-Native "code --list-extensions").Out
    foreach ($e in $extensions) {
        if ($have -match [regex]::Escape($e)) { Write-Host "[OK  ] $e"; continue }
        if ($DryRun) { Write-Host "[dry-run] code --install-extension $e"; continue }
        $r = Invoke-Native "code --install-extension $e --force"
        $after = (Invoke-Native "code --list-extensions").Out
        if ($after -match [regex]::Escape($e)) { Write-Host "[追加] $e" }
        else {
            Write-Host "[失敗] $e（VS Code の拡張機能の画面で確かめてください）" -ForegroundColor Yellow
            Write-Host ("       " + ($r.Out.Trim() -split "`r?`n" | Select-Object -Last 1))
            $failed += $e
        }
    }
}

Write-Host ""
if ($failed.Count) { Write-Host ("入らなかったもの: " + ($failed -join ", ")) -ForegroundColor Yellow }
Write-Host "次にやること:" -ForegroundColor Green
Write-Host "  1. 再起動が必要と表示されたら再起動する（WSL2）"
Write-Host "  2. Rancher Desktop を一度起動し、Container Engine を dockerd (moby) にする（Kubernetes は使わないので無効でよい）"
Write-Host "  3. setup.cmd をダブルクリック（全リポジトリの取得と Python のツールのインストール）"
Write-Host "  4. VS Code で GitHub にサインインし、Copilot を有効にする"
Write-Host "  5. もう一度 install-prereqs.cmd -Check を実行し、全部 OK になることを確かめる"
if ($failed.Count) { exit 1 }
