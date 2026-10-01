# AGENTS.md — AI エージェント向けガイド

このリポジトリは devtools-template から作られた「1 ツール = 1 リポジトリ」の開発支援ツールです。

## 規約（守ること）

- **責務は 1 つ**。README 冒頭の 1 文を超える機能は足さず、別ツールとして提案する。
- 本体は `src/<package>/core.py`、CLI は `cli.py`。CLI はオプション解釈と出力だけを担い、処理は core に置く。
- CLI の共通規約は `devtools-common` を使う（コピーしない）:
  - `devtools_common.cli`: 終了コード（0/1/2/3）、`--format/--output/--log-level`、`UsageError`、`run_main`
  - `devtools_common.report`: `Finding` と Markdown/HTML/CSV/JSON 出力
  - `devtools_common.log`: ログは標準エラー、本文・データ値は出さない
  - `devtools_common.tempfiles.secure_tempdir`: 一時ファイル
  - `devtools_common.httpclient.HttpClient`: 外部 API（レート制限・リトライ）
  - `devtools_common.config`: `.env` / YAML / JSON
- 設定・入力は JSON Schema（`schemas/`）で実行前に検証し、誤りは `UsageError`（終了コード 2）。
- 秘密情報は `.env`（コミットしない）。`.env.example` に `<your-token>` 形式で項目だけ書く。
- 大きな入力は 1 件ずつ処理し、全体をメモリに載せない。
- 出力は決定的に（時刻・乱数を含めない）。テストで期待値と比較できるようにする。

## 作業手順

1. 変更前に `pytest` が通ることを確認
2. 実装 + テスト追加（新しい振る舞いには必ずテスト）
3. `ruff check . && ruff format --check . && pytest`
4. README の使用例と CHANGELOG の `[Unreleased]` を更新
