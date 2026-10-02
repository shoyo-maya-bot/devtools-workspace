# AGENTS.md — AI エージェント向けツールカタログ

このワークスペースの CLI ツールは、AI エージェント（Copilot Agent Mode・Claude Code など）から呼び出して使うことを想定しています。
Python の CLI はすべて次が共通です。

- `-f json` で機械可読なレポート（`summary` と `findings[]`：`severity / rule_id / location / field / message / expected / actual / suggestion`）
- 終了コード: `0` 問題なし / `1` 指摘あり / `2` 使い方・設定・入力の誤り / `3` 実行時エラー
- ログは標準エラー。機密の本文は出さない

## いつ・どのツールを使うか

| やりたいこと | コマンド（リポジトリ） |
|---|---|
| Word / Excel / PowerPoint / PDF / draw.io の中身を読みたい | `doc2md <file> -d out/ -f json` → `out/<stem>.md` を読む（doc-to-markdown） |
| 図（業務フローなど）を作りたい | YAML を書いて `figspec build flow.yaml -d out/ --svg`（doc-to-markdown） |
| 表の項目間の整合性を確かめたい | `fieldcheck validate <data> -r rules.yaml -f json`（office-review） |
| 設計資料をレビューしたい | `/review` の手順、`harness precheck`・`harness lint`（office-review） |
| 設計書の新旧の差分を見たい | `design-diff excel --type api --before 旧.xlsx --after 新.xlsx`（design-diff） |
| API 定義書と OpenAPI のずれを見たい | `design-diff spec --excel API定義書.xlsx --oas openapi.yaml`（design-diff） |
| 指摘の傾向を見たい | `qa collect …` → `qa classify --mode rules` → `qa analyze`（quality-analytics） |
| Office の文字列を一括で差し替えたい | **必ず先に** `office-replace <dir> --rules rules.csv --dry-run`、確認後に `-o <出力>`（office-replace） |
| 進捗を確認したい | `backlog-report report`（backlog-report） |
| 設計書から実装・テストを進めたい | ai-coding の `/ai-plan` から。ゲートは `scripts/verify-gates.sh` |
| 要件と実装・テストの対応を確かめたい | `spec-trace check traceability/ --require proven`（ai-coding の tools/spec-trace） |

## 注意

- 1 ツール = 1 責務。既存ツールで足りることを新しいスクリプトにしない。
- `doc2md` の JSON に `loss.*` の warning があれば、変換で内容が欠けた可能性がある。利用者に伝える。
- 終了コード 2 はデータではなく **前提の誤り**（列名・設定ファイル・引数）。データではなく前提を確認する。
- 外部に送る操作（`qa classify --mode api --yes`、`backlog-report batch --slack --wiki`、Slack ボットの起動）は、利用者の明示の指示があるときだけ実行する。
- 元のファイルを書き換える操作をしない（office-replace は出力フォルダに書く）。
- 各リポジトリで作業するときは、そのリポジトリの `.github/copilot-instructions.md` に従う。
