# devtools-template

新しい開発支援ツール（**1 ツール = 1 リポジトリ**）を作るためのテンプレートリポジトリです。
GitHub の Settings で **Template repository** に設定して使います。複製すると組織標準の構成・CI・lint 設定がそろいます。

## 含まれるもの

```text
devtools-template/
├── src/tool_name/
│   ├── cli.py                  # CLI エントリ（共通オプション・終了コード・レポート出力は devtools-common）
│   ├── core.py                 # 本体（CLI から独立。単体テスト対象）
│   └── schemas/config.schema.json   # 設定ファイルの入力スキーマ（実行前に検証 → 誤りは終了コード 2）
├── tests/                      # ユニットテスト（unittest 形式。pytest でも実行可）
├── samples/                    # 使用例の入力
├── config.example.yaml         # 設定ファイルの例
├── .env.example                # 秘密情報のひな形（<your-token>）。.env はコミットしない
├── TOOL_README.md              # 新ツールの README 雛形（初期化で README.md になる）
├── AGENTS.md                   # AI エージェント向けの作業ルール
├── setup.cmd / setup.sh        # 利用者向けの 1 コマンドセットアップ（.venv 作成・インストール）
├── scripts/install_deps.py     # 隣に devtools-common があればそれを使ってインストール
├── CHANGELOG.md
├── pyproject.toml              # 依存・CLI 登録・組織共通の ruff 設定
├── scripts/init_tool.py        # 初期化スクリプト（名前の置換。実行後に自身を削除）
└── .github/
    ├── copilot-instructions.md # Copilot への常設の指示（日本語・初心者向け・規約）
    ├── prompts/implement-tool.prompt.md   # Copilot の /implement-tool: 設計 → 実装 → テストを工程ごとに
    ├── workflows/ci.yml        # 組織の再利用ワークフロー（<your-org>/.github）を呼ぶだけ
    ├── workflows/release.yml   # v* タグで wheel を GitHub Release へ
    └── dependabot.yml          # devtools-common・Actions の更新 PR
```

サンプル実装は「テキストファイルを設定のルール（行長・禁止表現）で検査してレポートを出す」小さなツールです。
設定の検証・1 行ずつの読み込み・Finding の生成・終了コードなど、規約の実例として残してあります。

## 新規ツールの作り方（テンプレ複製〜公開）

1. **Issue を起票**（組織の `.github` にある「新規ツールの提案」テンプレート）で責務を 1 文に決める
2. GitHub で **Use this template** → リポジトリ名 = ツール名（例: `api-spec-diff`）で作成
3. 初期化:

   ```bash
   git clone https://github.com/<your-org>/api-spec-diff.git && cd api-spec-diff
   python scripts/init_tool.py api-spec-diff "OpenAPI 仕様の差分を抽出する"
   ./setup.sh --dev && .venv/bin/pytest        # Windows: .\scripts\setup.ps1 -Dev
   ```

   または VS Code で開き、Copilot Chat で `/implement-tool` と入力して作りたいものを説明すると、
   設計の確認 → 実装 → テストの順で進めます。

   ```bash
   git add -A && git commit -m "chore: initialize from devtools-template"
   ```

4. `core.py` / `cli.py` / `schemas/` / `tests/` を自分の処理に置き換え、README を埋める
5. リポジトリ設定: `main` のブランチ保護（CI 必須・レビュー必須）、CODEOWNERS、Secrets は組織の `DEPS_TOKEN` を利用
6. 公開: version と CHANGELOG を更新 → `git tag v0.1.0 && git push origin v0.1.0`
7. `devtools-workspace` の `repos.yaml` にツールを追記（ワークスペースとツール一覧に載る）

## テンプレート自体を変更するとき

- lint 設定（`[tool.ruff]`）・CI の呼び出し方・ディレクトリ構成は全ツール共通の標準です。変えたら既存ツールにも PR で反映します。
- `tests/test_init_tool.py` が「複製 → 初期化 → 新ツールのテストが通る」ことを検証しています。
