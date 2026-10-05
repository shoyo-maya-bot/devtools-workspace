# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、版は [SemVer](https://semver.org/lang/ja/) に従います。


## 2026-10-05 Windows の CI

- CI に `windows` ジョブを追加: Windows のランナーで install-prereqs.cmd（`-Check`・`-DryRun`）と setup.cmd を実際に動かし、単体テスト・PSScriptAnalyzer・CRLF の確認もする
- setup.cmd / install-prereqs.cmd: 環境変数 `CI` か `DEVTOOLS_NO_PAUSE` があれば最後の `pause` をしない。PowerShell の終了コードを返す
- install-prereqs: `-DryRun`（何を入れるかを表示するだけ）を追加
- setup / bootstrap.py: `-Only`（`--only`）で一部のリポジトリだけ扱えるようにした。doc-to-markdown を取得していないときは `doc2md --check-env` を飛ばす
- ワークフローの Actions をコミット SHA で固定し、ジョブに timeout-minutes を付けた
- checkout に `persist-credentials: false` を付けた。SHA 固定と合わせて単体テストで確かめる
- setup.ps1: py ランチャーなどが 3.11 未満を選んだときは次の候補を試す。Python の入出力を UTF-8 にする
- bootstrap.py: 出力先の文字コードで日本語を書けなくても止まらないようにした（CI の Windows ランナーは cp1252）

## 2026-10-04 Windows 11 の実機で環境構築を通しで試した結果の修正

- install-prereqs: Java は「java コマンドがあるか」ではなく 17 以上かで判定する（Java 8 だけの PC で Corretto 17 を飛ばしていた）
- install-prereqs: WSL2 の判定を直した（PowerShell 5.1 で `2>$null` が例外になり常に「なし」、再起動前でも「OK」になっていた）
- install-prereqs: Rancher Desktop を `--scope machine` で入れる（付けないと 0x8A150010「適用できるインストーラーがない」で失敗した）
- install-prereqs: Rancher Desktop 1.23.1 / 1.24.0 の docker が止まる不具合の回避策（provisioning スクリプト）を置く
- install-prereqs: VS Code の拡張機能が入らなかったときに `[追加]` と出さず `[失敗]` と出す。失敗があれば終了コード 1
- setup.ps1: 冒頭のコメントを実際の動き（repos.yaml の org を使う）に合わせた
- setup: 取得済みのリポジトリを飛ばすだけだったのを、`bootstrap.py pull` で最新にするようにした（setup.cmd の再実行で更新できる）
- bootstrap.py pull: 進められなかったリポジトリを知らせ、終了コード 1 を返す（これまでは失敗を表示しなかった）

## 2026-10-03 再構成

- リポジトリを用途別の 13 個に作り直した（repos.yaml）: dev-environment、ai-coding、office-review、design-diff、quality-analytics、
  office-replace、backlog-report、slack-agenda-bot、slide-tool、learning-materials を追加
- field-validation は office-review に、spec-trace は ai-coding に同梱。devtools-template・ai-prompt-kb は廃止（.github は今後のために残す）
- README・AGENTS.md・ARCHITECTURE・NEW_TOOL・VS Code ワークスペース・パイプライン例を新しい構成に合わせた
## [Unreleased]

### Added

- spec-trace を一覧（repos.yaml・README・VS Code ワークスペース）に追加
- Copilot への指示に AI エージェントの約束
- devtools 武具屋（armory/index.html）: リポジトリを装備に見立てて選び、clone / pull するマクロを作るページ。各道具の使い方（装備スキル）つき。repos.yaml とのずれはテストで検知
- GitHub Pages に武具屋を出すワークフロー（.github/workflows/pages.yml）。サイトのトップは armory/ へ転送

## [0.2.0] - 2026-09-30

### Added

- setup.cmd / setup.sh（全リポの clone と一括インストール）
- Copilot: `.github/copilot-instructions.md`、`/check-excel`（doc2md → fieldcheck を通しで）
- docs/AI_USAGE.md（clone + Copilot で使う方針、MCP を見送った理由、情報の扱い）

## [0.1.0] - 2026-09-28

### Added

- 初版
