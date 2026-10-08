# devtools-workspace

開発の現場で使う **AI 活用ツール・開発環境・ガイドライン・教材** の親ワークスペースです。
各リポジトリは用途ごとに独立していて（マルチレポ）、このリポジトリはその一覧（マニフェスト）・一括操作・ツール間の連携例をまとめます。

**[▶ devtools 武具屋を開く](https://shoyo-maya-bot.github.io/devtools-workspace/armory/)** ── 使いたいリポジトリを選ぶと、まとめて clone / pull するマクロと各ツールの使い方が出ます（[使いかた](#選んで取ってくるdevtools-武具屋)）

> 固有の社名・システム名を含まない汎用版です。実案件では会社の GitHub に複製し、設定（設計書の様式・観点・置換表など）を合わせて使います。

## リポジトリ一覧

| 用途 | リポジトリ | CLI | 何をするか |
|---|---|---|---|
| 開発環境 | [dev-environment](https://github.com/shoyo-maya-bot/dev-environment) | – | ローカル（docker compose: PostgreSQL・S3 エミュレータ）とクラウド（Terraform: ECS・Aurora・S3・SQS・Step Functions）、Spring Boot のサンプルアプリ |
| コーディング・単体テスト | [ai-coding](https://github.com/shoyo-maya-bot/ai-coding) | – | 設計 → 実装 → 単体テスト → レビューを AI と進める手順、品質ゲート、Copilot のエージェント、対応表（spec-trace） |
| 文書の Markdown 化 | [doc-to-markdown](https://github.com/shoyo-maya-bot/doc-to-markdown) | `doc2md` | Office / PDF / draw.io を Markdown に。変換ロスの検知、llms.txt、YAML から draw.io の図（figspec） |
| 設計書のレビュー | [office-review](https://github.com/shoyo-maya-bot/office-review) | `harness` / `fieldcheck` | 観点のチェックリスト・マルチロールのレビュー・指摘の蓄積とダッシュボード。表の項目間検証 |
| 設計書の差分 | [design-diff](https://github.com/shoyo-maya-bot/design-diff) | `design-diff` | Excel 設計書の新旧差分、API 定義書と OpenAPI の整合 |
| 指摘の分析 | [quality-analytics](https://github.com/shoyo-maya-bot/quality-analytics) | `qa` | 指摘表・PR コメント・レビュー結果を分類（欠陥・ノイズ・確認／観点／真因）して傾向を見る |
| Office の一括置換 | [office-replace](https://github.com/shoyo-maya-bot/office-replace) | `office-replace` | 文字列・図形・シート名・ファイル名をワイルドカードで置換（VBA 版は参考） |
| 進捗レポート | [backlog-report](https://github.com/shoyo-maya-bot/backlog-report) | `backlog-report` | Backlog の遅延・担当者別・ガント・バーンダウンを Slack と Wiki へ |
| 会議のアジェンダ | [slack-agenda-bot](https://github.com/shoyo-maya-bot/slack-agenda-bot) | – | `/agenda` で議題を集め、Canvas にまとめる Slack ボット |
| スライド | [slide-tool](https://github.com/shoyo-maya-bot/slide-tool) | `npm run` | Marp + Tailwind のテーマ・レイアウト 20 種・はみ出しチェック・PDF / PPTX |
| 教材 | [learning-materials](https://github.com/shoyo-maya-bot/learning-materials) | – | 環境構築・基礎・実ソース読解（演習と解答）・API・非同期・設計品質・クラウドの全 62 章 |
| 実験 | [agent-lab](https://github.com/shoyo-maya-bot/agent-lab) | – | AI エージェントに任せられる範囲の実験（MCP・自律度・マルチモデルの相互レビュー）。設計の段階 |
| 基盤 | [review-platform](https://github.com/shoyo-maya-bot/review-platform) | – | 設計書とコードの差分の AI レビュー基盤（API・MCP、ローカル・AWS・Azure、Terraform）。クラウドと MCP の学習の題材 |
| 土台 | [devtools-common](https://github.com/shoyo-maya-bot/devtools-common) | – | 共有ライブラリ（CLI の終了コード・レポート形式・ログ・一時ファイル・HTTP） |
| 土台 | devtools-workspace（このリポ） | – | マニフェスト・一括操作・パイプライン例・共通 CI |
| 土台 | [.github](https://github.com/shoyo-maya-bot/.github) | – | アカウント共通の既定ファイル（PR・Issue テンプレートなど。今後のために残している） |

一覧の正は [repos.yaml](repos.yaml) です（`python scripts/bootstrap.py list` で表を出力）。

## どれから使うか

```text
新しく参加した  → learning-materials（教材）→ dev-environment（環境を作る）
作る            → ai-coding（手順とゲート）＋ dev-environment の sample-app
設計書を読む    → doc-to-markdown（Markdown に）→ design-diff（何が変わったか）
設計書を見る    → office-review（観点でレビュー）→ quality-analytics（指摘の傾向）
資料を作る      → slide-tool（スライド）／ office-replace（社名・年度の差し替え）
チームを回す    → backlog-report（進捗）／ slack-agenda-bot（定例のアジェンダ）
```

## 使う（利用者）— clone して Copilot から呼ぶ

MCP などの追加設定は不要です。**使うリポジトリを 1 つ clone するだけ** で使えます。

0. まだツールが入っていなければ、Windows では `install-prereqs.cmd` をダブルクリック（Git・Python 3.12・Corretto 17・Node.js・VS Code・Rancher Desktop を winget で入れる。入っているものは飛ばす）
   - Python は **3.12 以上** が要ります（各ツールの `pyproject.toml` の `requires-python` の下限に合わせている。ずれていないかは `bootstrap.py check-python` とテストで確かめる）。`py` や `python` があっても古い版なら「なし」と表示し、3.12 を追加で入れます。
     必要な版の判定は `scripts/python_version.py` の 1 か所にあり、`setup.cmd`・`setup.sh`・`bootstrap.py` も同じものを使います（古い Python では理由を表示して止まります）
   - `install-prereqs.cmd -Check` で入っているかだけを調べられる（Java は 17 以上か、WSL2 は実際に動くかまで見る）
   - `install-prereqs.cmd -DryRun` で、何を入れるかを表示するだけにできる（確認を出さず、何も変えない）
   - 別の版の Java（8 など）が入っていても消さずに 17 を追加する。WSL2 を有効にしたときは再起動が要る
   - Rancher Desktop 1.23.1 / 1.24.0 の不具合（docker が `timed out dialing Hyper-V socket` になる）の回避策も置く（[rancher-desktop#10780](https://github.com/rancher-sandbox/rancher-desktop/issues/10780)）
1. 使いたいリポジトリを clone する（Python のツールは、各ツールが `pyproject.toml` でコミット SHA を固定した devtools-common を、セットアップのときに GitHub から取ってきます。
   ただし **doc-to-markdown の `setup.cmd`・`setup.sh`（`scripts/install_deps.py`）は、隣のフォルダに devtools-common があればそれを editable で入れて固定の代わりに使います**（GitHub の認証が無くても入れられるようにするため。隣の checkout がどのコミットかはそのまま使われます）。
   固定した版で入れたいときは、隣に devtools-common を置かないか、下の「全部まとめて使う」の `setup`（各ツールの固定 SHA を使う）を使います。
   ほかのツールの `setup.cmd`・`setup.sh` は隣の devtools-common を使わず、固定した版を入れます。ワークスペースの `setup` で全ツールのローカルの devtools-common を使いたいときは開発者向けの `--dev` を使います）
2. **Windows**: `setup.cmd` をダブルクリック ／ **macOS・Linux**: `./setup.sh`
3. VS Code でそのフォルダを開き、Copilot Chat で `/` と入力 → プロンプトを選ぶ

| Copilot のプロンプト | リポジトリ | 何をするか |
|---|---|---|
| `/ai-plan` → `/ai-code` → `/ai-test` → `/ai-review` → `/ai-pr` | ai-coding | 設計書から計画 → 実装 → 単体テスト → レビュー → PR |
| `/doc2md-convert`・`/figspec-draw` | doc-to-markdown | 文書を Markdown に／YAML から draw.io の図を作る |
| `/review`・`/review-improve` | office-review | 観点に沿って設計資料をレビュー／指摘から観点を育てる |
| `/design-diff-review` | design-diff | 設計書の差分を取り、レビューの観点で要約 |
| `/classify-findings`・`/analyze-findings` | quality-analytics | 指摘を分類（追加費用なし）／傾向から改善策を考える |
| `/office-replace` | office-replace | 置換表を作り、試行で確認してから一括置換 |
| `/progress-summary` | backlog-report | 進捗の要点を 5 行に |
| `/slide-create` | slide-tool | 骨子 → レイアウト → 本文の順にスライドを作る |
| `/env-troubleshoot`・`/add-sample-api` | dev-environment | 環境のトラブル調査／サンプル API の追加 |
| `/check-excel` | devtools-workspace | Excel を Markdown 化 → 表をルールでチェック（doc2md → fieldcheck） |

ツールは基本的に PC の中だけで動きます。外部に接続するのは、利用者が明示的に使ったときだけです
（quality-analytics の LLM API 分類、backlog-report の Backlog / Slack、slack-agenda-bot の Slack / AWS）。
業務で使うときの情報の扱いは [docs/AI_USAGE.md](docs/AI_USAGE.md) を参照してください。

### 全部まとめて使う

```bash
mkdir devtools && cd devtools
git clone https://github.com/shoyo-maya-bot/devtools-workspace.git
cd devtools-workspace
setup.cmd                     # Windows
./setup.sh                    # macOS / Linux
```

全リポジトリを兄弟フォルダに clone し（取得済みのものは `git pull --ff-only` で最新にする）、Python のツールを共有の仮想環境（1 つ上の `.venv`）にまとめて入れます。
最新にしたいときも、もう一度 `setup.cmd` を実行すれば足ります。
一部だけ取りたいときは `setup.cmd -Only devtools-common,doc-to-markdown`（macOS・Linux は `./setup.sh --only …`）のようにカンマ区切りで名前を渡します。
VS Code で `devtools.code-workspace` を開くと全リポジトリを 1 画面で扱えます。

### 選んで取ってくる（devtools 武具屋）

**[devtools 武具屋](https://shoyo-maya-bot.github.io/devtools-workspace/armory/)** は、リポジトリを RPG の装備に見立てて選ぶページです（ソースは [armory/index.html](armory/index.html)。ダウンロードしてブラウザで開いても動きます。main の `armory/` が変わると `.github/workflows/pages.yml` がデプロイするので、Settings → Pages の Source は「GitHub Actions」にしておく）。

- 道具を「そうびする」と、選んだリポジトリだけを clone（取得済みなら `git pull --ff-only`）する **詠唱マクロ** が PowerShell 版と bash 版でできる
- 各道具の **装備スキル** に、その README の使い方をコマンド付きでまとめている
- マクロはコピーして貼りつけるか、`equip-macro.ps1` / `equip-macro.sh` として保存して実行する
  （PowerShell の実行ポリシーで止まるときは `powershell -ExecutionPolicy Bypass -File .\equip-macro.ps1`）

保存先は既定で `~/devtools`。`setup` や `bootstrap.py` と同じく兄弟フォルダに並べる前提です。
リポジトリを増やしたら、repos.yaml と一緒に `armory/index.html` の `ITEMS` にも 1 件足してください（ずれると CI のテストが落ちます）。

### パイプライン例（doc2md → fieldcheck）

```bash
./examples/expense-pipeline.sh                   # macOS / Linux
.\examples\expense-pipeline.ps1                  # Windows PowerShell
```

### CLI の共通の約束

Python の CLI は `-f json` の機械可読レポート（[仕様](https://github.com/shoyo-maya-bot/devtools-common/blob/main/docs/REPORT_FORMAT.md)）と、
そろった終了コード（0 問題なし / 1 指摘あり / 2 前提の誤り / 3 実行時エラー）を返します。
Python の版: `setup`（一括インストール）は **3.12 以上** が要ります（各ツールの `requires-python` の下限のうち最も高いもの）。
ツールごとの `requires-python` の下限はそろっていません: 3.10（devtools-common・doc-to-markdown・design-diff・spec-trace）、3.11（auto-review・devtools-mcp・review-platform）、3.12（office-review・quality-analytics・office-replace・backlog-report・slack-agenda-bot）（`bootstrap.py check-python` で setup の下限と矛盾しないことを確かめます）。
共通 CI（`python-ci.yml`）の既定は ubuntu で 3.10 と 3.12、Windows で 3.12 です（呼び出し側は `python-versions` で変えられます）。

## 開発する（全リポをローカルに並べる）

```bash
python scripts/bootstrap.py clone                    # 兄弟フォルダに全リポを clone
python scripts/bootstrap.py install                  # ../.venv に Python のツールを一括インストール（devtools-common は各ツールの固定 SHA）
python scripts/bootstrap.py install --dev            # 開発者向け: devtools-common をローカルの checkout で置き換えて入れる
python scripts/bootstrap.py status                   # 各リポのブランチ・未コミット・最新タグ
python scripts/bootstrap.py check-python             # 各ツールの requires-python と setup の最低版（3.12）が合っているか
python scripts/bootstrap.py check-pins               # 各ツールが固定した devtools-common などの SHA がそろっているか
code devtools.code-workspace                         # VS Code で全リポを 1 ウィンドウに
```

`install`（`setup.cmd`・`setup.sh` も同じ）は、各ツールが `devtools-common @ git+…@<SHA>` で固定した版を pip にそのまま解決させます。
手元の devtools-common の checkout がどのコミットでも、ツールはテスト済みの版の共有ライブラリで動きます。
ツールどうしで固定した SHA が食い違うと pip が衝突として止めるので、`setup` は一括インストールの前に `bootstrap.py check-pins` を流し、
食い違っていれば **どのツールの固定をどの SHA にそろえるか** を表示して止めます（`--dev` はローカルの checkout で置き換えるので見ない）。
見るのは各パッケージの `dependencies` の URL 固定（devtools-common・auto-review など）です。
pip が別の理由で失敗したときも、トレースバックではなく、原因の候補（ネットワーク・固定の食い違い・Python の版）を表示して終了コード 1 で止まります。

`install --dev`（`setup.cmd -Dev`・`setup.sh --dev`）は開発者向けです。固定を外し、**ローカルの devtools-common を editable で** 入れます
（ツールは `--no-deps` で入れ、ほかの依存と dev 用の依存は別に入れる）。共有ライブラリとツールを同時に変更して試せます。
あとで既定の `install` をやり直せば、固定した版に戻ります。

Python のパッケージがサブフォルダにあるリポジトリ（agent-lab の `auto-review`・`mcp-server`、ai-coding の `tools/spec-trace`）は、repos.yaml の `packages:` に相対パスを書きます。
ほかのツールが URL で固定しているパッケージ（review-platform が固定する auto-review、各ツールが固定する devtools-common）は、既定の `install` では手元の checkout を入れず、固定した版を使います。

`clone` / `pull` は既定ブランチを取り出します。repos.yaml の項目に `ref:`（ブランチ・タグ・コミット SHA）を書くと、そのリポジトリはその ref を取り出します。
マニフェストの行末の ` # コメント` は除きます（`"…"`・`'…'` で囲んだ値の中の `#` は値の一部）。読めない行・知らない項目・閉じていない引用符は、黙って読み飛ばさず、ファイル名と行番号を表示して終了コード 2 で止まります。
別のマニフェストを使うときは `bootstrap.py --manifest <ファイル>`（`setup.sh --manifest`・`setup.cmd -Manifest`）を渡します。
新しいツールの追加手順は [docs/NEW_TOOL.md](docs/NEW_TOOL.md) を参照してください。

## CI（Windows でも入口を動かして確かめる）

利用者の多くは Windows なので、`.github/workflows/ci.yml` の `windows` ジョブで、GitHub Actions の Windows ランナー（windows-latest、無料枠）を使って入口を実際に動かしています。

| 確かめること | どうやって |
|---|---|
| `.cmd`・`.bat`・`.ps1` が CRLF のまま取り出されるか | `git ls-files --eol` と単体テスト（`tests/test_entrypoints.py`。`.cmd` が BOM なしの cp932、`.ps1` が BOM 付きかも見る） |
| 単体テストが Windows でも通るか | `python -m unittest discover -s tests` |
| PowerShell のスクリプトに誤りがないか | PSScriptAnalyzer（Error と Warning。色付き表示に使っている `Write-Host` の警告だけは対象外） |
| `install-prereqs.cmd` が動くか | `-Check`（足りないものがあれば終了コード 1 になるのは正常。2 以上なら失敗）と `-DryRun` |
| `setup.cmd` で全 Python ツールを取得・インストールできるか | `setup.cmd -Manifest .github\ci-repos.yaml` を 2 回（2 回目は取得済みのものを最新にする流れ）。そのあと各 CLI の `--help`、全パッケージの import、`bootstrap.py check-python`・`check-pins`（setup の中でも check-pins を流す） |
| `setup.sh` で取得・インストールできるか（macOS・Linux） | `setup-sh` ジョブ（ubuntu-latest と macos-latest）で同じことをし、取り出した版が `ci-repos.yaml` の SHA と同じかも確かめる |
| 古い Python で分かりやすく止まるか | 単体テスト（`tests/test_python_version.py`。3.9 のふりをして `bootstrap.py` と `setup.sh` を動かす） |

統合のジョブが取り出す他のリポジトリ（repos.yaml の `python: true` の全リポジトリ。テストで確かめる）は、[.github/ci-repos.yaml](.github/ci-repos.yaml) の `ref:` で **コミット SHA に固定** しています。
他のリポジトリの main が変わってもこのリポジトリの CI は変わらず、同じ結果を再現できます。上げるときは `ci-repos.yaml` の SHA を書き換えて PR を出します。
CI で入れるツール（ruff・bandit・pip-audit・build）も版を固定しています（`ci.yml`・`python-ci.yml`・`python-release.yml` の先頭の `env` など）。
`python-release.yml` は build と build backend（setuptools・wheel など）の版を `PIP_CONSTRAINT` で固定し（呼び出し側に `constraints.txt` があればそれも使う）、wheel が固定した setuptools で作られたことを確かめます。

### 共通の再利用ワークフロー（python-ci.yml）

devtools-common と doc-to-markdown は `.github/workflows/python-ci.yml` を SHA で固定して呼びます（lint・ubuntu と Windows のテスト・bandit・pip-audit）。

```yaml
jobs:
  ci:
    uses: shoyo-maya-bot/devtools-workspace/.github/workflows/python-ci.yml@<コミット SHA>
    secrets:
      DEPS_TOKEN: ${{ secrets.DEPS_TOKEN }}   # 非公開の依存があるときだけ
```

- `secrets: inherit` は使いません（呼び出し側の全シークレットが渡るため）。`DEPS_TOKEN` だけを名前で渡します
- `DEPS_TOKEN` は依存を入れる手順の環境変数だけで使い、`~/.gitconfig` には書きません。bandit・pip-audit はトークンの無い手順で入れます
- `with:` の値（`extra-apt-packages`・`source-dir` など）は `run:` に直接埋め込まず、手順の `env:` で渡します（値でコマンドを注入されないため）。`extra-apt-packages` はパッケージ名の形のものだけを受け付けます
- `run-windows`（既定 `true`）で Windows（windows-latest、`windows-python-version` 既定 3.12）でもテストを流します
- リポジトリに `constraints.txt` があれば、`pip install` に `-c constraints.txt` を付けます

`setup.cmd`・`install-prereqs.cmd` は、環境変数 `CI`（GitHub Actions では自動で入る）か `DEVTOOLS_NO_PAUSE` があれば最後の `pause` をせず、PowerShell の終了コードをそのまま返します。ダブルクリックしたときの動きは変わりません。
CI で使う Actions はコミット SHA で固定しています（横にバージョンをコメントで書いています）。
checkout は `persist-credentials: false` にして、認証情報をランナーに残しません。どちらも単体テストで確かめています。
`setup.cmd` は 3.12 以上の Python を探して使います。日本語の出力で止まらないよう、Python の入出力を UTF-8 にしています。

確かめていないこと: winget で実際にインストールすること（ランナーにはすでに入っているものが多く、Rancher Desktop・WSL2 は再起動や仮想化が要るため）、日本語版 Windows（cp932）の画面での表示、Python でないリポジトリ（slide-tool・learning-materials など）の取得、各リポジトリの main の最新どうしの組み合わせ（CI は `ci-repos.yaml` の SHA で確かめる）。

## 初期設定チェックリスト（組織に導入するとき）

別の組織に移すときは、各リポジトリの `shoyo-maya-bot` を置き換えてください（`pyproject.toml`、`ci.yml`、README、`repos.yaml`、`mkdocs.yml`、`armory/index.html` の `ORG`）。

- [x] リポジトリを作成して push（15 個 + .github。一覧は `repos.yaml`）
- [x] 各ツールは `devtools-common` をコミット SHA で固定して依存（タグ不要）
- [ ] learning-materials: Settings → Pages → Source を **GitHub Actions** にする（教材サイトの公開）
- [ ] 各リポの `main` にブランチ保護（CI 必須・レビュー必須）
- [x] LICENSE: 全リポ MIT（著作権表示はアカウント名）
- [ ] 社内の AI 利用規程・Copilot の契約で、業務文書を扱ってよい範囲を確認（[docs/AI_USAGE.md](docs/AI_USAGE.md)）
- [ ] LLM API・Backlog・Slack・AWS を使う場合は、それぞれの利用ルールと費用の承認を確認

## セキュリティ・ライセンス

- 脆弱性を見つけたら、公開の Issue ではなく [SECURITY.md](SECURITY.md) の方法で知らせてください
- ライセンスは [MIT](LICENSE) です
