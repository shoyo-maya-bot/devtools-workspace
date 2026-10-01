# AGENTS.md — AI エージェント向けツールカタログ

このワークスペースの CLI ツールは、AI エージェント（Copilot Agent Mode・Claude Code など）から呼び出して使うことを想定しています。
すべてのツールで次が共通です。

- `-f json` で機械可読なレポート（`summary` と `findings[]`：`severity / rule_id / location / field / message / expected / actual / suggestion`）
- 終了コード: `0` 問題なし / `1` 指摘あり / `2` 使い方・設定・入力スキーマの誤り / `3` 実行時エラー
- ログは標準エラー。機密本文は出さない

## いつ・どのツールを使うか

| やりたいこと | コマンド |
|---|---|
| Word / Excel / PowerPoint / PDF / draw.io の中身を読みたい | `doc2md <file> -d out/ -f json` → `out/<stem>.md` を読む |
| フォルダ内の文書をまとめてテキスト化 | `doc2md <dir> -d out/ -r --continue-on-error -f json` |
| 表データ（CSV / JSON / YAML / Markdown の表）の整合性を確かめたい | `fieldcheck validate <data> -r rules.yaml -f json` |
| Excel の表の整合性を確かめたい | `doc2md <xlsx> -d out/` → `fieldcheck validate out/<stem>.md -r rules.yaml --table <シート名>` |
| 検証ルールを書きたい | `fieldcheck list-rules` と `fieldcheck schema` を読み、書いたら `fieldcheck check-rules rules.yaml` |
| 新しいツールを作りたい | [docs/NEW_TOOL.md](docs/NEW_TOOL.md)（devtools-template から作る。既存ツールに機能を足さない） |

## 注意

- 1 ツール = 1 責務。変換（doc2md）と検証（fieldcheck）を 1 つのスクリプトにまとめない。
- `doc2md` の JSON に `loss.*` の warning があれば、変換で内容が欠けた可能性がある。利用者に伝える。
- 終了コード 2 はデータではなく **前提の誤り**（列名・ルールファイル・引数）。データの修正ではなく前提を確認する。
- 各リポジトリで作業するときは、そのリポジトリの AGENTS.md に従う。
