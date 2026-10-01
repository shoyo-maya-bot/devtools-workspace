# Copilot への指示（tool-name）

このリポジトリは devtools-template から作った「1 ツール = 1 リポジトリ」の開発支援ツール `tool-name` です。
説明は日本語で行い、利用者が初心者でも分かるように、手順は番号付きで示してください。

- 規約は [AGENTS.md](../AGENTS.md) に従う（責務は 1 つ・処理は core.py・CLI 規約は devtools-common を使う）
- 変更後は必ず `ruff check . && ruff format --check . && pytest` を実行し、結果を報告する
- 秘密情報（トークン・パスワード）はコードに書かない。`.env`（コミットしない）から読み、項目は `.env.example` に書く
- 外部 API を呼ぶときは `devtools_common.httpclient.HttpClient`（レート制限・リトライ付き）を使う
- レポートは `devtools_common.report` の `Finding` で返し、形式（`--format json` の schema_version 1.x）を変えない
