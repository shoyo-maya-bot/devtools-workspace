# devtools-workspace

開発の現場で使う **AI 活用ツール・開発環境・ガイドライン・教材** の親ワークスペースです。
各リポジトリは用途ごとに独立していて（マルチレポ）、このリポジトリはその一覧（マニフェスト）・一括操作・ツール間の連携例をまとめます。

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
| 教材 | [learning-materials](https://github.com/shoyo-maya-bot/learning-materials) | – | 環境構築・基礎・実ソース読解（演習と解答）・API・非同期・設計品質の全 52 章 |
| 土台 | [devtools-common](https://github.com/shoyo-maya-bot/devtools-common) | – | 共有ライブラリ（CLI の終了コード・レポート形式・ログ・一時ファイル・HTTP） |
| 土台 | devtools-workspace（このリポ） | – | マニフェスト・一括操作・パイプライン例・共通 CI |

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

1. 使いたいリポジトリを clone する（Python のツールは `devtools-common` も同じフォルダに clone しておくと、GitHub の認証なしでセットアップできます）
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

全リポジトリを兄弟フォルダに clone し、Python のツールを共有の仮想環境（1 つ上の `.venv`）にまとめて入れます。
VS Code で `devtools.code-workspace` を開くと全リポジトリを 1 画面で扱えます。

### パイプライン例（doc2md → fieldcheck）

```bash
./examples/expense-pipeline.sh                   # macOS / Linux
.\examples\expense-pipeline.ps1                  # Windows PowerShell
```

### CLI の共通の約束

Python の CLI は `-f json` の機械可読レポート（[仕様](https://github.com/shoyo-maya-bot/devtools-common/blob/main/docs/REPORT_FORMAT.md)）と、
そろった終了コード（0 問題なし / 1 指摘あり / 2 前提の誤り / 3 実行時エラー）を返します。Python は 3.12 にそろえています。

## 開発する（全リポをローカルに並べる）

```bash
python scripts/bootstrap.py clone                    # 兄弟フォルダに全リポを clone
python scripts/bootstrap.py install                  # ../.venv に Python のツールを editable で一括インストール
python scripts/bootstrap.py status                   # 各リポのブランチ・未コミット・最新タグ
code devtools.code-workspace                         # VS Code で全リポを 1 ウィンドウに
```

`install` は各ツールの `devtools-common @ git+…@<SHA>` 依存を **ローカルの devtools-common で置き換えて** 入れます。
共有ライブラリとツールを同時に変更して試せます。新しいツールの追加手順は [docs/NEW_TOOL.md](docs/NEW_TOOL.md) を参照してください。

## 初期設定チェックリスト（組織に導入するとき）

別の組織に移すときは、各リポジトリの `shoyo-maya-bot` を置き換えてください（`pyproject.toml`、`ci.yml`、README、`repos.yaml`、`mkdocs.yml`）。

- [x] リポジトリを作成して push（13 個）
- [x] 各ツールは `devtools-common` をコミット SHA で固定して依存（タグ不要）
- [ ] learning-materials: Settings → Pages → Source を **GitHub Actions** にする（教材サイトの公開）
- [ ] 各リポの `main` にブランチ保護（CI 必須・レビュー必須）
- [ ] 各リポの LICENSE を決めて反映
- [ ] 社内の AI 利用規程・Copilot の契約で、業務文書を扱ってよい範囲を確認（[docs/AI_USAGE.md](docs/AI_USAGE.md)）
- [ ] LLM API・Backlog・Slack・AWS を使う場合は、それぞれの利用ルールと費用の承認を確認
