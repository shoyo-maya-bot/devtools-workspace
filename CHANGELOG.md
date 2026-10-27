# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、版は [SemVer](https://semver.org/lang/ja/) に従います。


## 2026-10-28 ruff を 0.16 系にそろえる、ドキュメントと動きのずれ（第 8 回）

- 共通 CI（`python-ci.yml`）・`python-release.yml`・`ci.yml` の `RUFF_VERSION` を 0.15.11 から 0.16.10（各ツールの `constraints.txt` と同じ）に上げた。
  `ci-repos.yaml` の版の全リポジトリで `ruff check .`・`ruff format --check .` が 0.16.10 で通ることを確かめた。3 つのワークフローの版の一致をテストで確かめる
- `bootstrap.py clone`: 1 件の clone の失敗・`ref:` を取り出せないことで全体を止めていた（README は「ほかの取得は続ける」）。知らせて続け、最後に終了コード 1
- `bootstrap.py pull`: detached HEAD のリポジトリは理由（既定ブランチへの戻し方）を表示して飛ばす。README の「clone / pull は既定ブランチを取り出す」を、
  実際（pull はいまのブランチのまま fast-forward）に直した
- README: Pages の公開は Settings → Pages → Source を「GitHub Actions」にしたときだけ pages.yml が使われることと、その手順を書いた
- learning-materials の章の数を 73 章と付録 3 に直した（README・repos.yaml・武具屋）。3 か所の一致と、latest-mains で main の実物との一致をテストで確かめる（`tests/test_learning_materials.py`）

## 2026-10-22 doc-to-markdown の Python 3.11 以上への追随、空のフォルダを黙って外さない

- `.github/ci-repos.yaml`: doc-to-markdown を 28ee561（`requires-python = ">=3.11"`）に上げた。ほかのリポジトリの ref はそのまま（固定 SHA はそろっている）
- README: ツールごとの `requires-python` の一覧で、doc-to-markdown を 3.10 から 3.11 に移した
- 統合 CI（`ci.yml` の setup-sh・windows、`latest-mains.yml`）: setup のあとに `ReadmeFactsTest` を、兄弟のリポジトリが無ければ失敗にする設定
  （`README_FACTS_REQUIRE_CHECKOUTS=1`）で流す。これまで README の一覧と実物の照合は兄弟のリポジトリが無い単体テストの段で飛んでいて、CI では一度も確かめていなかった
- `bootstrap.py clone`: 空のフォルダを「取得済み」とみなさず、そのまま clone する。中身があって Git のリポジトリでないフォルダは知らせて終了コード 1（ほかの取得は続ける）
- `bootstrap.py install`: フォルダはあるのに `pyproject.toml` が無い Python のリポジトリ（空のフォルダなど）を黙って外して 0 で終わっていたのを、理由を表示して 1 で止める。
  未取得のリポジトリは「未取得」と表示して飛ばす（終了コードはこれまでどおり）
- docs/ARCHITECTURE.md: ruff の設定の説明（line-length・Python の版）を実際の各リポジトリの値に合わせた
- README: macOS ランナーが割り当てられずに cancelled になったときの扱いを書いた

## 2026-10-21 最新 main の組み合わせの週 1 回の確認、パイプライン例の終了コード、winget の版の固定

- `.github/workflows/latest-mains.yml`（新規）: 週 1 回（月曜）と手動で、`repos.yaml` の Python のリポジトリを各 main の最新どうしで
  setup し（ubuntu・Windows）、各 CLI の `--help`・import・check-python・check-pins・パイプライン例を流す。落ちたら Issue を起こす
  （同じ題の Issue が開いていればコメントを足す）。PR の CI（`ci.yml`）はこれまでどおり `ci-repos.yaml` の SHA に固定
- examples/expense-pipeline.sh・.ps1: 終了コードで段を区別する（0 なし / 1 指摘 / 2 前提の誤り / 3 実行時エラー / 4 変換の警告 / 5 変換の警告と指摘）。
  これまでは doc2md `--strict` の警告（変換ロスなど）で 1 を返して fieldcheck を流さず、指摘ありと区別できなかった。
  いまは警告があっても Markdown ができていれば fieldcheck を流し、4・5 で知らせる。前回の Markdown は変換の前に消す（変換できなかったのに古い出力を検証しない）。
  .sh の冒頭のコメント（ツールを探す順）を実際の順（仮想環境 → PATH）に直した
- scripts/install-prereqs.ps1: winget で入れる Rancher Desktop を 1.24.0（回避策を確かめた版）に固定（`--version`）。版を固定したものが入らないときは入れられる版の調べ方を表示する
- README: learning-materials の章の数を当時の実際（60 章と付録）に直した（その後 73 章になり、第 8 回で直した）
- `.github/ci-repos.yaml`: 全リポジトリを 2026-10-21 の最新に上げた（devtools-common 04f3915、doc-to-markdown a10ad87、agent-lab 08e9689 など）

## 2026-10-09 ref にそろわないまま install しない、requires-python の判定、トークンを pip に渡さない、リリース前のテスト

- `bootstrap.py install`（`setup.sh`・`setup.cmd` も）: マニフェストで `ref` を指定したリポジトリの HEAD が ref のコミットと違えば、
  理由を表示してインストールせずに 1 で止める（clone 直後の checkout や pull で ref にそろえられないまま、既定ブランチの版を入れていた）。
  clone 直後に ref を取り出せないときも、何を取り出せなかったかを表示して止める
- `bootstrap.py` の requires-python の判定（check-python）: PEP 440 の指定子として判定する（`~=3.12.1` は 3.13 を受け付けない、`>3.12` は 3.12.1 以降を受け付ける）。依存は増やしていない
- python-ci.yml: `DEPS_TOKEN` を git 依存の取得（git clone）だけに使い、`pip install` の手順の環境からは消す（第三者の sdist のビルドからトークンが読めないように）
- python-release.yml: 公開の前に python-ci.yml と同じ lint・test（ubuntu・Windows）を流し、通ったときだけ Release を作る。
  inputs（`python-versions`・`extra-apt-packages`・`run-windows`・`windows-python-version`）は省略可で、既定は python-ci.yml と同じ
- examples/expense-pipeline.sh・.ps1: `../.venv` の `doc2md`・`fieldcheck` を直接使う（有効化は不要）。見つからなければ何をすればよいかを表示して 2。
  統合 CI（setup-sh・windows）で setup のあとに 1 回動かす
- docs/NEW_TOOL.md: 登録の手順に `armory/index.html` の `ITEMS` と `.github/ci-repos.yaml`（Python のとき）を足した

## 2026-10-08 固定 SHA の食い違いをセットアップ前に検出、pip の失敗の案内、マニフェストのコメントの扱い

- `bootstrap.py check-pins`（新しいサブコマンド。check-python と同じ形）: 取得済みの各パッケージが `dependencies` で URL 固定した
  devtools-common・auto-review などの版が食い違っていないかを確かめる。食い違えば、どのツールの固定をどの SHA にそろえるかを表示して 1。
  `setup.sh`・`setup.cmd` は一括インストールの前に流して止める（`--dev`・`-Dev` では流さない）。統合 CI（windows・setup-sh）でも流す
- `bootstrap.py install`: pip が失敗したとき、トレースバックではなく原因の候補（ネットワーク・固定の食い違い・Python の版）を表示して 1 で終わる
- repos.yaml の読み込み: 行末の ` # コメント` を、引用符で囲んだ値の中では切らない。閉じていない引用符・読めない行・知らない項目・
  重複した name は、ファイル名と行番号を表示して終了コード 2 で止める（以前は黙って読み飛ばしていた）
- README: doc-to-markdown の `setup`（`scripts/install_deps.py`）は隣の devtools-common を editable で使う、と実際に合わせて書いた

## 2026-10-08 Python は 3.12 以上、全 Python ツールの一括インストールを CI で、python-ci の inputs を env で渡す

- Python の最低版を 3.12 に（`scripts/python_version.py` の `MIN_VERSION`）。3.11 で「OK」と表示した直後に、
  `requires-python = ">=3.12"` のツール（office-review など）を pip が入れられなかった。
  `bootstrap.py check-python` で各ツールの requires-python と一致するか確かめる（テストと統合 CI でも流す）
- repos.yaml: ai-coding（`tools/spec-trace`）・agent-lab（`auto-review`・`mcp-server`）・review-platform も `python: true`。
  サブフォルダのパッケージは新しい項目 `packages:` に書く。**既定の `setup`・`install` でこれらも入る**
- bootstrap.py install: ほかのツールが URL で固定しているパッケージ（review-platform → auto-review）は手元の checkout を入れない（pip の衝突を避ける）
- CI: `.github/ci-repos.yaml` に Python の全リポジトリを入れ、windows・setup-sh（ubuntu・macOS）で `--only` なしの一括インストールと各 CLI の `--help`・import を確かめる。
  ci-repos.yaml の SHA を各リポジトリの今の main に上げた。取り出すリポジトリはすべて公開なので DEPS_TOKEN は使わない
- python-ci.yml: `extra-apt-packages`・`source-dir` を `run:` に直接埋め込まず、手順の `env:` で渡す（スクリプト注入対策）。
  `extra-apt-packages` はパッケージ名の形だけを受け付ける。inputs の名前・型・既定値は変えていない（呼び出し側はそのまま使える）

## 2026-10-07 Python の版の確認を 1 か所に、CI の再現性とシークレットの渡し方

- Python の版の確認を `scripts/python_version.py` の 1 か所にまとめた（3.11 以上）。install-prereqs.ps1・setup.ps1・setup.sh・bootstrap.py が使う
  - install-prereqs: `py` があるだけで「Python OK」にしていた。3.11 以上の Python があるかで判定し、古い版なら今の版を表示して 3.12 を入れる
  - setup.sh: 版を確かめずに python3 を呼んでいた。python3.13 → python3.12 → python3.11 → python3 → python の順に 3.11 以上を探し、無ければ理由を出して止まる
  - bootstrap.py: tomllib を import する前に版を確かめ、古い Python ではトレースバックではなく理由を出して終了コード 1 で終わる
- setup.sh `--manifest`・setup.cmd `-Manifest`: repos.yaml の代わりに使うマニフェストを渡せる
- CI: 統合のジョブ（windows・新しい setup-sh）は `.github/ci-repos.yaml` の `ref:`（コミット SHA）で他のリポジトリを取り出す（以前は最新の main）。
  setup-sh ジョブ（ubuntu・macOS）で setup.sh を実際に動かす。ruff・bandit・pip-audit・build の版を固定。ci.yml に bandit を追加
- python-ci.yml（**呼び出し側の書き方が変わる**）: 使い方の例を `secrets: inherit` から `secrets: DEPS_TOKEN: ${{ secrets.DEPS_TOKEN }}` に変えた。
  `DEPS_TOKEN` は依存を入れる手順の環境変数だけで使い、`git config --global` に書かない。bandit・pip-audit はトークンの無い手順で入れる。
  入力 `run-windows`（既定 `true`）・`windows-python-version`（既定 3.12）を追加し、Windows でもテストを流す（呼び出し側が Windows で落ちるようになることがある）。
  リポジトリに `constraints.txt` があれば `-c constraints.txt` を付ける
- docs/ARCHITECTURE.md: 共通 CI を使っているのは devtools-common と doc-to-markdown だけ、と実態に合わせた
- README: 「devtools-common を同じフォルダに clone すると認証なしで入る」は今の install の動き（各ツールが固定した SHA を取りに行く）と違うので直した
- tests: armory/index.html の各道具の CLI 名が repos.yaml の `cli` と同じかを確かめる

## 2026-10-06 install が各ツールの固定した devtools-common を使う

- bootstrap.py install: 既定では各ツールを通常の依存解決で入れ、ツールが `devtools-common @ git+…@<SHA>` で固定した版を使う
  （これまでは固定を外し、手元の devtools-common の checkout を、どのコミットでも editable で入れていた）
- bootstrap.py install `--dev`（setup.cmd `-Dev`・setup.sh `--dev`）: これまでの動き（ローカルの devtools-common で置き換える）は開発者向けに残した
- bootstrap.py clone / pull: repos.yaml の項目に `ref:`（ブランチ・タグ・コミット SHA）を書けば、その ref を取り出す（書かなければ既定ブランチ）
- 単体テスト: 既定のモードで固定した依存を置き換えないこと、`--dev` で置き換えること、`ref:` を取り出すことを確かめる

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
