# 新しいツールを追加する

```mermaid
flowchart LR
  A[責務を 1 文で決める<br/>既存ツールと重ならないか] --> B[GitHub で空のリポジトリを作る]
  B --> C[既存ツールの構成を写す<br/>design-diff が最小の見本]
  C --> D[処理・CLI・テスト・README]
  D --> E[CI が緑になったら main へ]
  E --> F[repos.yaml・devtools.code-workspace・<br/>armory/index.html の ITEMS・<br/>.github/ci-repos.yaml に追記]
```

1. **責務を決める**: やること / やらないこと、入力と出力を 1 枚に書く。既存ツールの責務と重なるなら、既存ツールの拡張を先に検討する
2. **リポジトリを作る**: リポジトリ名 = ツール名（ケバブケース）
3. **構成を写す**: 見本は design-diff（小さく、層が分かれている）。次をそろえる
   - `pyproject.toml`: `requires-python = ">=3.12"`、`devtools-common @ git+…@<SHA>`、`[project.scripts]` に CLI、ruff の設定
   - `src/<パッケージ>/`: `cli` は引数と出力だけ、処理は別のモジュール。終了コードは `devtools_common.cli.ExitCode`、レポートは `devtools_common.report`
   - `tests/`: サンプルの入力は `samples/make_samples.py` で生成し、テストもそれを使う（実データを置かない）
   - `setup.sh` / `setup.cmd`（Shift_JIS・CRLF）、`.gitattributes`、`.gitignore`（`.env`・出力・実データ）
   - `.github/workflows/ci.yml`（ruff → pytest → サンプルの実行）、`.github/copilot-instructions.md`、`.github/prompts/<名前>.prompt.md`
   - `README.md`: 何をするか → すぐ使う（3 ステップ）→ 使い方 → 終了コード → 開発
4. **秘密情報**: API キー・トークンは `.env`（`.env.example` に `<your-value>`）。設定ファイルやログに書かない
5. **リポジトリ設定**: `main` のブランチ保護（CI 必須・レビュー必須）
6. **登録**: このリポジトリの次のファイルに追記して 1 本の PR にする（`tests/` のテストが repos.yaml との一致を検査するので、1 つでも抜けると CI が落ちる）
   - `repos.yaml`: 1 件追加（name・role・description。Python なら `python: true`、CLI があれば `cli:`、サブフォルダなら `packages:`）
   - `devtools.code-workspace`: `folders` に `../<リポジトリ名>` を追加（`tests/test_bootstrap.py`）
   - `armory/index.html`: `ITEMS` に 1 件追加（`id` はリポジトリ名。`skill:{p:…}` と `steps:[[…]]` を書き、CLI があればその名前のコマンドを入れる。`tests/test_armory.py`）
   - `.github/ci-repos.yaml`: `python: true` のときだけ。repos.yaml と同じ name・role・python・cli・packages に、`ref:` として新しいリポジトリの main のコミット SHA（40 桁）を書く（統合 CI が全ツールを一括インストールする。`tests/test_bootstrap.py`）。
     CLI があれば `.github/workflows/ci.yml` の `SMOKE_CLIS`、import できるモジュールを `SMOKE_IMPORTS` にも足す
   - README の一覧の表（リポジトリの数もテストで確かめる）
