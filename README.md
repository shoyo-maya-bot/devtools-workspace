# devtools-workspace

エンジニアが **どのプロジェクトでも流用できる AI 活用ツール群** の親ワークスペースです。
ツールは **1 ツール = 1 リポジトリ（マルチレポ）** で管理し、このリポジトリはその一覧（マニフェスト）・
一括操作・ツール間の連携例をまとめます。

> 公開情報・OSS で裏取りできる一般的なベストプラクティスで新規に設計したものです。特定企業の資産の写しではありません。

## ツール一覧

| リポジトリ | 役割 | CLI | 何をするか |
|---|---|---|---|
| [doc-to-markdown](https://github.com/shoyo-maya-bot/doc-to-markdown) | ツール | `doc2md` | Office / PDF / draw.io を Markdown + 抽出図に変換（変換のみ）。変換ロスを検知 |
| [field-validation](https://github.com/shoyo-maya-bot/field-validation) | ツール | `fieldcheck` | 表 / YAML / JSON の項目間整合性を YAML の宣言的ルールで検証（検証のみ） |
| [devtools-common](https://github.com/shoyo-maya-bot/devtools-common) | 共有ライブラリ | – | CLI 規約（終了コード・出力形式）・ログ・一時ファイル・HTTP（レート制限/リトライ）・レポート |
| [devtools-template](https://github.com/shoyo-maya-bot/devtools-template) | テンプレート | – | 新規ツールの雛形（Use this template → `init_tool.py`） |
| [.github](https://github.com/shoyo-maya-bot/.github) | 組織標準 | – | 共通 CI / リリースの再利用ワークフロー、PR・Issue テンプレート |

一覧の正は [repos.yaml](repos.yaml) です（`python scripts/bootstrap.py list` で表を出力）。
設計の考え方は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照してください。

## 使う（利用者）— GitHub から clone して Copilot から呼ぶ

MCP などの追加設定は不要です。**必要なツールのリポジトリを 1 つ clone するだけ** で使えます。

1. 使いたいツールのリポジトリ（例: `doc-to-markdown`）を clone する。
   `devtools-common` も同じフォルダに clone しておくと、GitHub の認証なしでセットアップできます
2. **Windows**: そのフォルダの `setup.cmd` をダブルクリック ／ **macOS・Linux**: `./setup.sh`
3. VS Code でそのフォルダを開き、Copilot Chat で `/` と入力 → プロンプトを選ぶ

| Copilot のプロンプト | リポジトリ | 何をするか |
|---|---|---|
| `/doc2md-convert` | doc-to-markdown | 文書を Markdown に変換し、注意点と概要を報告 |
| `/doc2md-investigate-loss` | doc-to-markdown | 変換で欠けた内容の原因を調べる |
| `/fieldcheck-write-rules` | field-validation | 文章の業務ルールから検証ルール（YAML）を作って試す |
| `/fieldcheck-run` | field-validation | 検証して「どの行の何をどう直すか」を報告 |
| `/check-excel` | devtools-workspace | Excel を変換 → 表を選ぶ → ルールでチェック → 報告（上の 2 つを通しで） |
| `/implement-tool` | devtools-template | 新しいツールを設計 → 実装 → テスト |

ツールは PC の中だけで動き、ネットワーク接続や生成 AI の API 呼び出しをしません。
業務で使うときの情報の扱いは [docs/AI_USAGE.md](docs/AI_USAGE.md) を参照してください。

### 全部まとめて使う

```bash
git clone https://github.com/shoyo-maya-bot/devtools-workspace.git
cd devtools-workspace
setup.cmd                     # Windows
./setup.sh                    # macOS / Linux
```

全リポジトリを兄弟フォルダに clone し、共有の仮想環境（1 つ上の `.venv`）にまとめてインストールします。
VS Code で `devtools.code-workspace` を開くと全リポジトリを 1 画面で扱えます。

### パイプライン例（08 変換 → 09 検証）

```bash
./examples/expense-pipeline.sh                   # macOS / Linux
.\examples\expense-pipeline.ps1                  # Windows PowerShell
```

### CLI の共通の約束

全ツールで `-f json` の機械可読レポート（[仕様](https://github.com/shoyo-maya-bot/devtools-common/blob/main/docs/REPORT_FORMAT.md)、
schema_version 1.x）と、そろった終了コード（0 問題なし / 1 指摘あり / 2 前提の誤り / 3 実行時エラー）を返します。

## 開発する（全リポをローカルに並べる）

```bash
mkdir devtools && cd devtools
git clone https://github.com/shoyo-maya-bot/devtools-workspace.git
cd devtools-workspace
python scripts/bootstrap.py clone                    # 兄弟フォルダに全リポを clone
python scripts/bootstrap.py install                  # ../.venv に editable で一括インストール
python scripts/bootstrap.py status                   # 各リポのブランチ・未コミット・最新タグ
code devtools.code-workspace                         # VS Code で全リポを 1 ウィンドウに
```

```text
devtools/
├── .venv/                 ← bootstrap install が作る共有の仮想環境
├── devtools-workspace/    ← このリポジトリ
├── .github/
├── devtools-template/
├── devtools-common/
├── doc-to-markdown/
└── field-validation/
```

`install` は各ツールの `devtools-common @ git+…@vX.Y.Z` 依存を **ローカルの devtools-common で置き換えて** 入れます。
共有ライブラリとツールを同時に変更して試せます。

新しいツールの追加手順は [docs/NEW_TOOL.md](docs/NEW_TOOL.md) を参照してください。

## 初期設定チェックリスト（組織に導入するとき）

GitHub アカウント `shoyo-maya-bot` に、次の 6 リポジトリを公開（public）で置く構成です。
別の組織に移すときは、各リポジトリの `shoyo-maya-bot` を置き換えてください（`pyproject.toml`、`ci.yml`、`release.yml`、README、`repos.yaml`）。

- [x] 組織名を `shoyo-maya-bot` に設定
- [x] 6 リポジトリを作成して push（`.github` はリポジトリ名そのものが `.github`）
- [x] `.github` リポに `v1` タグ（各リポの CI が `@v1` で参照）
- [x] `devtools-common` に `v0.2.0` タグ（各ツールが依存）
- [ ] 非公開リポにする場合は Secrets `DEPS_TOKEN`（読み取り専用）を設定し、`.github` のワークフローを呼べるようにする（公開リポなら不要）
- [ ] `devtools-template` を Settings → **Template repository** に設定
- [ ] 各リポの `main` にブランチ保護（CI 必須・レビュー必須）
- [ ] 各リポの LICENSE と依存ライブラリの版固定の方針を決めて反映（検討中）
- [ ] 社内の AI 利用規程・Copilot の契約で、業務文書を扱ってよい範囲を確認（[docs/AI_USAGE.md](docs/AI_USAGE.md)）
